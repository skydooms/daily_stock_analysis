# -*- coding: utf-8 -*-
"""
Stock Monitor Service.

High-level service for stock monitoring that integrates:
- Monitor engine for real-time checking
- Feishu client for notifications
- Data fetcher for stock quotes
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from data_provider.base import DataFetcherManager
from src.config import get_config
from src.monitor.engine import MonitorEngine, get_monitor_engine
from src.monitor.models import StockMonitorConfig
from src.repositories.stock_monitor_repo import StockMonitorRepository

if TYPE_CHECKING:
    from bot.platforms.feishu_stream import FeishuReplyClient

logger = logging.getLogger(__name__)


@dataclass
class MonitorInfo:
    """Monitor information with current state."""

    config: StockMonitorConfig
    stock_name: str
    current_price: Optional[float] = None
    change_pct: Optional[float] = None
    baseline_price: Optional[float] = None
    last_check_time: Optional[datetime] = None
    alert_1pct_triggered: bool = False
    alert_2pct_triggered: bool = False


class StockMonitorService:
    """
    Stock Monitor Service.

    Provides high-level API for stock monitoring operations.
    """

    def __init__(
        self,
        repo: Optional[StockMonitorRepository] = None,
        engine: Optional[MonitorEngine] = None,
        data_fetcher: Optional[DataFetcherManager] = None,
    ):
        self.repo = repo or StockMonitorRepository()
        self.engine = engine or get_monitor_engine()
        self.data_fetcher = data_fetcher or DataFetcherManager()
        self._feishu_client: Optional["FeishuReplyClient"] = None

    def set_feishu_client(self, client: "FeishuReplyClient") -> None:
        """Set the Feishu client for notifications."""
        self._feishu_client = client
        self.engine.set_feishu_client(client)

    def add_monitor(
        self,
        stock_code: str,
        user_id: str,
        chat_id: str,
        stock_name: Optional[str] = None,
        monitor_type: str = "realtime",
        window_minutes: int = 10,
    ) -> Tuple[bool, str]:
        """
        Add a stock to monitoring.

        Args:
            stock_code: Stock code (e.g., "600519", "00700.HK")
            user_id: User's open_id from Feishu
            chat_id: Chat ID for sending notifications
            stock_name: Optional stock name (will be fetched if not provided)
            monitor_type: "realtime" or "simulation"
            window_minutes: Time window in minutes for threshold calculation

        Returns:
            Tuple of (success, message)
        """
        if not stock_name:
            stock_name = self.data_fetcher.get_stock_name(stock_code)
            if not stock_name:
                stock_name = stock_code

        success, message = self.engine.add_stock(
            stock_code=stock_code,
            stock_name=stock_name,
            user_id=user_id,
            chat_id=chat_id,
            monitor_type=monitor_type,
            window_minutes=window_minutes,
        )

        if success:
            logger.info(f"[MonitorService] Added monitor: {stock_code} for user={user_id}")

        return success, message

    def remove_monitor(self, stock_code: str, user_id: str) -> Tuple[bool, str]:
        """
        Remove a stock from monitoring.

        Args:
            stock_code: Stock code to remove
            user_id: User's open_id

        Returns:
            Tuple of (success, message)
        """
        return self.engine.remove_stock(stock_code, user_id)

    def list_monitors(self, user_id: str) -> List[MonitorInfo]:
        """
        List all monitors for a user with current state.

        Args:
            user_id: User's open_id

        Returns:
            List of MonitorInfo objects
        """
        configs = self.repo.list_configs(user_id=user_id, is_active=True)
        result = []

        for config in configs:
            state = self.repo.get_state(config.id)

            quote = None
            try:
                quote = self.data_fetcher.get_realtime_quote(config.stock_code)
            except Exception as e:
                logger.warning(f"[MonitorService] Failed to get quote for {config.stock_code}: {e}")

            info = MonitorInfo(
                config=config,
                stock_name=config.stock_name or config.stock_code,
                current_price=state.last_price if state else None,
                change_pct=state.last_change_pct if state else None,
                baseline_price=state.baseline_price if state else None,
                last_check_time=state.last_check_time if state else None,
                alert_1pct_triggered=state.alert_1pct_triggered if state else False,
                alert_2pct_triggered=state.alert_2pct_triggered if state else False,
            )

            if quote and quote.has_basic_data():
                info.current_price = quote.price
                info.stock_name = quote.name or config.stock_name or config.stock_code

            result.append(info)

        return result

    def get_monitor_status(self, user_id: str, stock_code: str) -> Optional[MonitorInfo]:
        """
        Get the status of a specific monitor.

        Args:
            user_id: User's open_id
            stock_code: Stock code

        Returns:
            MonitorInfo or None if not found
        """
        config = self.repo.get_config_by_stock(stock_code, user_id)
        if not config:
            return None

        state = self.repo.get_state(config.id)

        quote = None
        try:
            quote = self.data_fetcher.get_realtime_quote(config.stock_code)
        except Exception as e:
            logger.warning(f"[MonitorService] Failed to get quote for {config.stock_code}: {e}")

        info = MonitorInfo(
            config=config,
            stock_name=config.stock_name or config.stock_code,
            current_price=state.last_price if state else None,
            change_pct=state.last_change_pct if state else None,
            baseline_price=state.baseline_price if state else None,
            last_check_time=state.last_check_time if state else None,
            alert_1pct_triggered=state.alert_1pct_triggered if state else False,
            alert_2pct_triggered=state.alert_2pct_triggered if state else False,
        )

        if quote and quote.has_basic_data():
            info.current_price = quote.price
            info.stock_name = quote.name or config.stock_name or config.stock_code

        return info

    def start_monitoring(self, interval_seconds: Optional[int] = None) -> Tuple[bool, str]:
        """
        Start the monitoring engine.

        Args:
            interval_seconds: Check interval in seconds (default from config)

        Returns:
            Tuple of (success, message)
        """
        config = get_config()
        interval = interval_seconds or getattr(config, "stock_monitor_interval_seconds", 60)

        try:
            self.engine.start(interval)
            return True, f"监控引擎已启动，检查间隔 {interval} 秒"
        except Exception as e:
            logger.error(f"[MonitorService] Failed to start monitoring: {e}")
            return False, f"启动监控失败: {e}"

    def stop_monitoring(self) -> Tuple[bool, str]:
        """
        Stop the monitoring engine.

        Returns:
            Tuple of (success, message)
        """
        try:
            self.engine.stop()
            return True, "监控引擎已停止"
        except Exception as e:
            logger.error(f"[MonitorService] Failed to stop monitoring: {e}")
            return False, f"停止监控失败: {e}"

    def get_engine_status(self) -> Dict[str, Any]:
        """
        Get the monitoring engine status.

        Returns:
            Dictionary with engine status information
        """
        return self.engine.get_status()

    def get_alert_history(
        self,
        user_id: str,
        stock_code: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Get alert history for a user.

        Args:
            user_id: User's open_id
            stock_code: Optional stock code filter
            hours: Hours to look back

        Returns:
            List of alert records
        """
        alerts = self.repo.list_alerts(
            user_id=user_id,
            stock_code=stock_code,
            hours=hours,
        )
        return [a.to_dict() for a in alerts]

    def format_monitor_list(self, monitors: List[MonitorInfo]) -> str:
        """
        Format monitor list for display.

        Args:
            monitors: List of MonitorInfo objects

        Returns:
            Formatted string for display
        """
        if not monitors:
            return "暂无监控股票"

        lines = ["📊 **监控股票列表**\n"]

        for i, m in enumerate(monitors, 1):
            type_icon = "🔴" if m.config.monitor_type == "realtime" else "🟡"
            status = "运行中" if m.config.is_active else "已暂停"

            price_str = f"¥{m.current_price:.2f}" if m.current_price else "--"
            change_str = f"{m.change_pct:+.2f}%" if m.change_pct is not None else "--"

            alert_1 = "✅" if m.alert_1pct_triggered else "⬜"
            alert_2 = "✅" if m.alert_2pct_triggered else "⬜"

            lines.append(
                f"{i}. {type_icon} **{m.stock_name}** ({m.config.stock_code})\n"
                f"   价格: {price_str} | 涨跌: {change_str}\n"
                f"   窗口: {m.config.window_minutes}分钟 | 状态: {status}\n"
                f"   1%阈值: {alert_1} | 2%阈值: {alert_2}\n"
            )

        return "\n".join(lines)


_service_instance: Optional[StockMonitorService] = None


def get_monitor_service() -> StockMonitorService:
    """Get the global monitor service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = StockMonitorService()
    return _service_instance
