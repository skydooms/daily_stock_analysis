# -*- coding: utf-8 -*-
"""
Stock Monitor Engine.

Core monitoring logic that:
1. Fetches real-time stock quotes
2. Calculates price changes within time windows and from day start
3. Triggers alerts when thresholds are exceeded (3 levels)
4. Sends notifications via Feishu

Alert Levels:
- Level 1 (🔴): Today's change > level1_threshold (default 3.5%)
- Level 2 (🟠): Today's change > level2_threshold (default 2.0%)
- Level 3 (🟡): Window change > level3_threshold (default 0.5%)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

from data_provider.base import DataFetcherManager
from src.config import get_config
from src.monitor.models import (
    StockMonitorConfig, StockMonitorState,
    get_now_cn, TZ_CN
)
from src.repositories.stock_monitor_repo import is_same_day_cn
from src.repositories.stock_monitor_repo import StockMonitorRepository

if TYPE_CHECKING:
    from bot.platforms.feishu_stream import FeishuReplyClient

logger = logging.getLogger(__name__)


@dataclass
class MonitorResult:
    """Result of a single monitoring check."""

    stock_code: str
    stock_name: str
    current_price: float

    # Today change (for level 1 and 2)
    today_start_price: Optional[float] = None
    today_change_pct: Optional[float] = None

    # Window change (for level 3)
    window_baseline_price: Optional[float] = None
    window_change_pct: Optional[float] = None
    window_minutes: int = 10

    # Trigger status
    triggered_level1: bool = False
    triggered_level2: bool = False
    triggered_level3: bool = False

    alert_sent: bool = False
    error: Optional[str] = None

    # Quote timing info
    quote_time: Optional[datetime] = None
    latency_seconds: Optional[float] = None


class MonitorEngine:
    """
    Stock Monitor Engine.

    Continuously monitors configured stocks and triggers alerts
    when price changes exceed thresholds within time windows.
    """

    def __init__(
        self,
        repo: Optional[StockMonitorRepository] = None,
        data_fetcher: Optional[DataFetcherManager] = None,
        notifier: Optional[Callable[[str, str, str], bool]] = None,
    ):
        self.repo = repo or StockMonitorRepository()
        self.data_fetcher = data_fetcher or DataFetcherManager()
        self._notifier = notifier
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._feishu_client: Optional[FeishuReplyClient] = None

    def set_notifier(self, notifier: Callable[[str, str, str], bool]) -> None:
        """Set the notification callback function.

        Args:
            notifier: A function that takes (chat_id, title, message) and returns success status.
        """
        self._notifier = notifier

    def set_feishu_client(self, client: "FeishuReplyClient") -> None:
        """Set the Feishu client for sending notifications."""
        self._feishu_client = client

    def start(self, interval_seconds: Optional[int] = None) -> None:
        """Start the monitoring loop in a background thread."""
        if self._running:
            logger.warning("[MonitorEngine] Already running")
            return

        config = get_config()
        interval = interval_seconds or getattr(config, "stock_monitor_interval_seconds", 60)

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, args=(interval,), daemon=True)
        self._thread.start()
        logger.info(f"[MonitorEngine] Started monitoring with interval={interval}s")

    def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("[MonitorEngine] Stopped monitoring")

    def _run_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop."""
        while self._running and not self._stop_event.is_set():
            try:
                self.check_all_monitors()
            except Exception as e:
                logger.error(f"[MonitorEngine] Error in monitoring loop: {e}")

            self._stop_event.wait(interval_seconds)

    def check_all_monitors(self) -> List[MonitorResult]:
        """Check all active monitor configurations."""
        logger.info(f"[MonitorEngine] Checking all monitors...")
        configs = self.repo.list_active_configs()
        if not configs:
            logger.debug("[MonitorEngine] No active monitors to check")
            return []

        logger.info(f"[MonitorEngine] Found {len(configs)} active monitors")
        results = []
        for config in configs:
            try:
                logger.debug(f"[MonitorEngine] Checking {config.stock_code}...")
                result = self.check_single_monitor(config)
                if result:
                    results.append(result)
                    logger.info(
                        f"[MonitorEngine] Checked {result.stock_code}: "
                        f"price={result.current_price}, "
                        f"today_change={result.today_change_pct:.2f}%, "
                        f"window_change={result.window_change_pct:.2f}%"
                    )
            except Exception as e:
                logger.error(f"[MonitorEngine] Error checking {config.stock_code}: {e}")

        logger.info(f"[MonitorEngine] Check completed, {len(results)} results")
        return results

    def check_single_monitor(self, config: StockMonitorConfig) -> Optional[MonitorResult]:
        """Check a single monitor configuration."""
        stock_code = config.stock_code
        stock_name = config.stock_name or stock_code
        now = get_now_cn()

        quote = self.data_fetcher.get_realtime_quote(stock_code)
        if not quote or not quote.has_basic_data():
            logger.warning(f"[MonitorEngine] No quote data for {stock_code}")
            return None

        current_price = quote.price

        # Get quote time and calculate latency
        quote_time = None
        latency_seconds = None
        if hasattr(quote, 'quote_time') and quote.quote_time:
            quote_time = quote.quote_time
            if quote_time.tzinfo is None:
                quote_time = quote_time.replace(tzinfo=TZ_CN)
            latency_seconds = (now - quote_time).total_seconds()
            latency_str = f"{latency_seconds:.1f}s" if latency_seconds >= 0 else "N/A"
            logger.info(
                f"[检查] {stock_code} {stock_name}: "
                f"行情时间={quote_time.strftime('%H:%M:%S')} CST (延迟: {latency_str})"
            )

        state = self.repo.get_state(config.id)
        if not state:
            logger.warning(f"[MonitorEngine] No state for config {config.id}")
            return None

        result = MonitorResult(
            stock_code=stock_code,
            stock_name=stock_name,
            current_price=current_price,
            window_minutes=config.window_minutes,
            quote_time=quote_time,
            latency_seconds=latency_seconds,
        )

        # Initialize or check today's start price (for level 1 and 2)
        if (state.today_start_price is None or
                state.today_start_time is None or
                not is_same_day_cn(state.today_start_time, now)):
            # New day, reset today's start price
            self.repo.reset_today_start(config.id, current_price, now)
            logger.info(f"[MonitorEngine] Initialized today start for {stock_code}: {current_price}")
            state.today_start_price = current_price
            state.today_start_time = now

        result.today_start_price = state.today_start_price
        if state.today_start_price > 0:
            result.today_change_pct = (current_price - state.today_start_price) / state.today_start_price * 100

        # Initialize or check window baseline (for level 3)
        if state.baseline_price is None or state.baseline_time is None:
            self.repo.reset_baseline(config.id, current_price, now)
            logger.info(f"[MonitorEngine] Initialized window baseline for {stock_code}: {current_price}")
            state.baseline_price = current_price
            state.baseline_time = now

        result.window_baseline_price = state.baseline_price
        if state.baseline_price > 0:
            result.window_change_pct = (current_price - state.baseline_price) / state.baseline_price * 100

        # Check if window expired
        window_expired = (now - state.baseline_time) >= timedelta(minutes=config.window_minutes)
        if window_expired:
            self.repo.reset_baseline(config.id, current_price, now)
            logger.info(
                f"[MonitorEngine] Window expired, reset baseline for {stock_code}: {current_price}"
            )
            state.baseline_price = current_price
            result.window_baseline_price = current_price
            result.window_change_pct = 0.0

        # Check thresholds
        result.triggered_level1 = False
        result.triggered_level2 = False
        result.triggered_level3 = False

        if config.monitor_type == "realtime":
            # Level 1: Today's change > level1_threshold
            if (config.level1_enabled and result.today_change_pct is not None and
                    abs(result.today_change_pct) >= config.level1_threshold and
                    not state.alert_level1_triggered):
                result.triggered_level1 = True

            # Level 2: Today's change > level2_threshold
            if (config.level2_enabled and result.today_change_pct is not None and
                    abs(result.today_change_pct) >= config.level2_threshold and
                    not state.alert_level2_triggered):
                result.triggered_level2 = True

            # Level 3: Window change > level3_threshold
            if (config.level3_enabled and result.window_change_pct is not None and
                    abs(result.window_change_pct) >= config.level3_threshold and
                    not state.alert_level3_triggered):
                result.triggered_level3 = True

        # Send alerts (from highest to lowest level)
        alert_sent = False

        if result.triggered_level1:
            alert_sent = self._send_alert(
                config=config,
                stock_name=stock_name,
                change_pct=result.today_change_pct,
                current_price=current_price,
                alert_level=1,
                alert_type="today_change",
            )
            if alert_sent:
                self.repo.update_state(config.id, alert_level1_triggered=True)
                self.repo.add_alert(
                    config_id=config.id,
                    stock_code=stock_code,
                    alert_level=1,
                    alert_type="today_change",
                    change_pct=result.today_change_pct,
                    price=current_price,
                    notified=True,
                )

        elif result.triggered_level2:
            alert_sent = self._send_alert(
                config=config,
                stock_name=stock_name,
                change_pct=result.today_change_pct,
                current_price=current_price,
                alert_level=2,
                alert_type="today_change",
            )
            if alert_sent:
                self.repo.update_state(config.id, alert_level2_triggered=True)
                self.repo.add_alert(
                    config_id=config.id,
                    stock_code=stock_code,
                    alert_level=2,
                    alert_type="today_change",
                    change_pct=result.today_change_pct,
                    price=current_price,
                    notified=True,
                )

        elif result.triggered_level3:
            alert_sent = self._send_alert(
                config=config,
                stock_name=stock_name,
                change_pct=result.window_change_pct,
                current_price=current_price,
                alert_level=3,
                alert_type="window_change",
            )
            if alert_sent:
                self.repo.update_state(config.id, alert_level3_triggered=True)
                self.repo.add_alert(
                    config_id=config.id,
                    stock_code=stock_code,
                    alert_level=3,
                    alert_type="window_change",
                    change_pct=result.window_change_pct,
                    price=current_price,
                    notified=True,
                )
            else:
                # Record alert even if notification failed
                self.repo.add_alert(
                    config_id=config.id,
                    stock_code=stock_code,
                    alert_level=3,
                    alert_type="window_change",
                    change_pct=result.window_change_pct,
                    price=current_price,
                    notified=False,
                )
                logger.info(
                    f"[MonitorEngine] Level 3 threshold triggered for {stock_code}: {result.window_change_pct:.2f}%"
                )

        result.alert_sent = alert_sent

        # Update state
        self.repo.update_state(
            config.id,
            last_price=current_price,
            last_change_pct=result.today_change_pct or result.window_change_pct,
            last_check_time=now,
        )

        return result

    def _send_alert(
        self,
        config: StockMonitorConfig,
        stock_name: str,
        change_pct: float,
        current_price: float,
        alert_level: int,
        alert_type: str,
    ) -> bool:
        """Send an alert notification."""
        direction = "上涨" if change_pct > 0 else "下跌"
        abs_change = abs(change_pct)

        level_icons = {1: "🔴", 2: "🟠", 3: "🟡"}
        level_names = {1: "一级", 2: "二级", 3: "三级"}
        threshold_descs = {
            1: f"今日涨跌幅超{config.level1_threshold}%",
            2: f"今日涨跌幅超{config.level2_threshold}%",
            3: f"{config.window_minutes}分钟内涨跌幅超{config.level3_threshold}%",
        }

        icon = level_icons.get(alert_level, "⚠️")
        level_name = level_names.get(alert_level, "")
        threshold_desc = threshold_descs.get(alert_level, "")

        title = f"{icon} {level_name}预警 {stock_name}({config.stock_code}) {direction}"
        message = (
            f"**{stock_name}** ({config.stock_code})\n"
            f"**{direction} {abs_change:.2f}%**\n\n"
            f"预警级别: {icon} {level_name}\n"
            f"触发条件: {threshold_desc}\n"
            f"当前价格: ¥{current_price:.2f}\n"
            f"触发时间: {get_now_cn().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

        if alert_type == "window_change":
            message += f"监控窗口: {config.window_minutes}分钟\n"

        if self._notifier:
            try:
                return self._notifier(config.chat_id or "", title, message)
            except Exception as e:
                logger.error(f"[MonitorEngine] Notification failed: {e}")
                return False

        if self._feishu_client and config.chat_id:
            try:
                success = self._feishu_client.send_to_chat(config.chat_id, f"{title}\n\n{message}")
                return success
            except Exception as e:
                logger.error(f"[MonitorEngine] Feishu notification failed: {e}")
                return False

        logger.info(f"[MonitorEngine] Alert (no notifier): {title}")
        return False

    def add_stock(
        self,
        stock_code: str,
        stock_name: Optional[str] = None,
        user_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        monitor_type: str = "realtime",
        level1_threshold: float = 3.5,
        level1_enabled: bool = True,
        level2_threshold: float = 2.0,
        level2_enabled: bool = True,
        level3_threshold: float = 0.5,
        level3_enabled: bool = True,
        window_minutes: int = 10,
    ) -> Tuple[bool, str]:
        """Add a stock to monitoring.

        Returns:
            Tuple of (success, message)
        """
        existing = self.repo.get_config_by_stock(stock_code, user_id)
        if existing:
            return False, f"股票 {stock_code} 已在监控列表中"

        config = self.repo.add_config(
            stock_code=stock_code,
            stock_name=stock_name,
            user_id=user_id,
            chat_id=chat_id,
            monitor_type=monitor_type,
            level1_threshold=level1_threshold,
            level1_enabled=level1_enabled,
            level2_threshold=level2_threshold,
            level2_enabled=level2_enabled,
            level3_threshold=level3_threshold,
            level3_enabled=level3_enabled,
            window_minutes=window_minutes,
        )

        if config:
            return True, f"已添加 {stock_name or stock_code} 到监控列表"
        else:
            return False, f"添加 {stock_code} 失败"

    def remove_stock(self, stock_code: str, user_id: Optional[str] = None) -> Tuple[bool, str]:
        """Remove a stock from monitoring.

        Returns:
            Tuple of (success, message)
        """
        count = self.repo.remove_config_by_stock(stock_code, user_id)
        if count > 0:
            return True, f"已移除 {stock_code} 的监控"
        else:
            return False, f"未找到 {stock_code} 的监控配置"

    def list_stocks(self, user_id: Optional[str] = None) -> List[Dict]:
        """List monitored stocks with their current state."""
        configs = self.repo.list_configs(user_id=user_id, is_active=True)
        result = []

        for config in configs:
            state = self.repo.get_state(config.id)
            result.append({
                "config": config.to_dict(),
                "state": state.to_dict() if state else None,
            })

        return result

    def get_status(self) -> Dict:
        """Get overall monitoring status."""
        configs = self.repo.list_active_configs()
        stats = self.repo.get_alert_stats(hours=24)

        return {
            "running": self._running,
            "active_monitors": len(configs),
            "monitor_type_breakdown": {
                "realtime": sum(1 for c in configs if c.monitor_type == "realtime"),
                "simulation": sum(1 for c in configs if c.monitor_type == "simulation"),
            },
            "alerts_24h": stats,
        }


_engine_instance: Optional[MonitorEngine] = None


def get_monitor_engine() -> MonitorEngine:
    """Get the global monitor engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = MonitorEngine()
    return _engine_instance


def start_monitoring(interval_seconds: Optional[int] = None) -> None:
    """Start the global monitor engine."""
    engine = get_monitor_engine()
    engine.start(interval_seconds)


def stop_monitoring() -> None:
    """Stop the global monitor engine."""
    engine = get_monitor_engine()
    engine.stop()
