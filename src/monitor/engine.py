# -*- coding: utf-8 -*-
"""
Stock Monitor Engine.

Core monitoring logic that:
1. Fetches real-time stock quotes
2. Calculates price changes within time windows
3. Triggers alerts when thresholds are exceeded
4. Sends notifications via Feishu
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
from src.monitor.models import StockMonitorConfig, StockMonitorState
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
    baseline_price: float
    change_pct: float
    window_minutes: int
    triggered_1pct: bool
    triggered_2pct: bool
    alert_sent: bool
    error: Optional[str] = None


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
        configs = self.repo.list_active_configs()
        if not configs:
            logger.debug("[MonitorEngine] No active monitors to check")
            return []

        results = []
        for config in configs:
            try:
                result = self.check_single_monitor(config)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"[MonitorEngine] Error checking {config.stock_code}: {e}")

        return results

    def check_single_monitor(self, config: StockMonitorConfig) -> Optional[MonitorResult]:
        """Check a single monitor configuration."""
        stock_code = config.stock_code
        stock_name = config.stock_name or stock_code
        now = datetime.now()

        quote = self.data_fetcher.get_realtime_quote(stock_code)
        if not quote or not quote.has_basic_data():
            logger.warning(f"[MonitorEngine] No quote data for {stock_code}")
            return None

        current_price = quote.price

        state = self.repo.get_state(config.id)
        if not state:
            logger.warning(f"[MonitorEngine] No state for config {config.id}")
            return None

        if state.baseline_price is None or state.baseline_time is None:
            self.repo.reset_baseline(config.id, current_price, now)
            logger.info(f"[MonitorEngine] Initialized baseline for {stock_code}: {current_price}")
            return MonitorResult(
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                baseline_price=current_price,
                change_pct=0.0,
                window_minutes=config.window_minutes,
                triggered_1pct=False,
                triggered_2pct=False,
                alert_sent=False,
            )

        window_expired = (now - state.baseline_time) >= timedelta(minutes=config.window_minutes)
        if window_expired:
            self.repo.reset_baseline(config.id, current_price, now)
            logger.info(
                f"[MonitorEngine] Window expired, reset baseline for {stock_code}: {current_price}"
            )
            return MonitorResult(
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                baseline_price=current_price,
                change_pct=0.0,
                window_minutes=config.window_minutes,
                triggered_1pct=False,
                triggered_2pct=False,
                alert_sent=False,
            )

        baseline_price = state.baseline_price
        if baseline_price <= 0:
            self.repo.reset_baseline(config.id, current_price, now)
            return None

        change_pct = (current_price - baseline_price) / baseline_price * 100

        triggered_1pct = abs(change_pct) >= 1.0
        triggered_2pct = abs(change_pct) >= 2.0

        alert_sent = False

        if config.monitor_type == "realtime":
            if config.threshold_2pct_enabled and triggered_2pct and not state.alert_2pct_triggered:
                alert_sent = self._send_alert(
                    config=config,
                    stock_name=stock_name,
                    change_pct=change_pct,
                    current_price=current_price,
                    alert_type="threshold_2pct",
                )
                if alert_sent:
                    self.repo.update_state(config.id, alert_2pct_triggered=True)
                    self.repo.add_alert(
                        config_id=config.id,
                        stock_code=stock_code,
                        alert_type="threshold_2pct",
                        change_pct=change_pct,
                        price=current_price,
                        notified=True,
                    )

            if config.threshold_1pct_enabled and triggered_1pct and not state.alert_1pct_triggered:
                self.repo.update_state(config.id, alert_1pct_triggered=True)
                self.repo.add_alert(
                    config_id=config.id,
                    stock_code=stock_code,
                    alert_type="threshold_1pct",
                    change_pct=change_pct,
                    price=current_price,
                    notified=False,
                )
                logger.info(
                    f"[MonitorEngine] 1% threshold triggered for {stock_code}: {change_pct:.2f}%"
                )

        self.repo.update_state(
            config.id,
            last_price=current_price,
            last_change_pct=change_pct,
            last_check_time=now,
        )

        return MonitorResult(
            stock_code=stock_code,
            stock_name=stock_name,
            current_price=current_price,
            baseline_price=baseline_price,
            change_pct=change_pct,
            window_minutes=config.window_minutes,
            triggered_1pct=triggered_1pct,
            triggered_2pct=triggered_2pct,
            alert_sent=alert_sent,
        )

    def _send_alert(
        self,
        config: StockMonitorConfig,
        stock_name: str,
        change_pct: float,
        current_price: float,
        alert_type: str,
    ) -> bool:
        """Send an alert notification."""
        direction = "上涨" if change_pct > 0 else "下跌"
        abs_change = abs(change_pct)

        title = f"⚠️ {stock_name}({config.stock_code}) {direction}预警"
        message = (
            f"**{stock_name}** ({config.stock_code})\n"
            f"**{direction} {abs_change:.2f}%**\n\n"
            f"当前价格: ¥{current_price:.2f}\n"
            f"触发时间: {datetime.now().strftime('%H:%M:%S')}\n"
            f"监控窗口: {config.window_minutes}分钟\n"
        )

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
