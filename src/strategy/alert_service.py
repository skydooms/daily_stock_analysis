# -*- coding: utf-8 -*-
"""
Alert Service Module

This module provides alert service functionality for trading signals.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import json
import os

from .base import Signal, SignalType


logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    """Alert configuration"""
    enabled: bool = True
    channels: List[str] = field(default_factory=lambda: ["log"])
    min_confidence: float = 0.5
    alert_on_buy: bool = True
    alert_on_sell: bool = True
    cooldown_minutes: int = 60


class AlertService:
    """
    Alert service for sending trading alerts
    
    Supports multiple alert channels: log, file, webhook, email, etc.
    """
    
    def __init__(self, config: Optional[AlertConfig] = None):
        """
        Initialize alert service
        
        Args:
            config: Alert configuration
        """
        self.config = config or AlertConfig()
        self._alert_handlers: Dict[str, Callable] = {}
        self._last_alerts: Dict[str, datetime] = {}
        
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default alert handlers"""
        self._alert_handlers["log"] = self._log_alert
        self._alert_handlers["file"] = self._file_alert
    
    def send_alert(
        self,
        signal: Signal,
        stock_code: str,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send alert for a signal
        
        Args:
            signal: Trading signal
            stock_code: Stock code
            additional_info: Additional information
            
        Returns:
            True if alert sent successfully
        """
        if not self.config.enabled:
            return False
        
        if signal.confidence < self.config.min_confidence:
            return False
        
        if signal.is_buy and not self.config.alert_on_buy:
            return False
        
        if signal.is_sell and not self.config.alert_on_sell:
            return False
        
        alert_key = f"{stock_code}_{signal.signal_type.value}"
        if alert_key in self._last_alerts:
            minutes_since = (datetime.now() - self._last_alerts[alert_key]).total_seconds() / 60
            if minutes_since < self.config.cooldown_minutes:
                return False
        
        alert_data = {
            "stock_code": stock_code,
            "signal_type": signal.signal_type.value,
            "price": signal.price,
            "confidence": signal.confidence,
            "reason": signal.reason,
            "strategy": signal.strategy_name,
            "timestamp": datetime.now().isoformat(),
            "additional_info": additional_info or {},
        }
        
        for channel in self.config.channels:
            if channel in self._alert_handlers:
                try:
                    self._alert_handlers[channel](alert_data)
                except Exception as e:
                    logger.error(f"Alert handler {channel} failed: {e}")
        
        self._last_alerts[alert_key] = datetime.now()
        
        return True
    
    def _log_alert(self, alert_data: Dict[str, Any]) -> None:
        """Log alert to logger"""
        stock_code = alert_data.get("stock_code", "")
        signal_type = alert_data.get("signal_type", "")
        price = alert_data.get("price", 0)
        reason = alert_data.get("reason", "")
        
        logger.info(f"[ALERT] {stock_code} - {signal_type.upper()} @ {price:.2f} - {reason}")
    
    def _file_alert(self, alert_data: Dict[str, Any]) -> None:
        """Save alert to file"""
        alert_dir = "alerts"
        os.makedirs(alert_dir, exist_ok=True)
        
        filename = f"{alert_dir}/alerts_{datetime.now().strftime('%Y%m%d')}.json"
        
        alerts = []
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    alerts = json.load(f)
            except:
                alerts = []
        
        alerts.append(alert_data)
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    
    def register_handler(
        self,
        channel: str,
        handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register a custom alert handler
        
        Args:
            channel: Channel name
            handler: Handler function
        """
        self._alert_handlers[channel] = handler
        logger.info(f"Registered alert handler for channel: {channel}")
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent alerts from file
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent alerts
        """
        alerts = []
        alert_dir = "alerts"
        
        if not os.path.exists(alert_dir):
            return alerts
        
        cutoff = datetime.now() - __import__('datetime').timedelta(hours=hours)
        
        for filename in os.listdir(alert_dir):
            if filename.startswith("alerts_") and filename.endswith(".json"):
                filepath = os.path.join(alert_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        file_alerts = json.load(f)
                        for alert in file_alerts:
                            alert_time = datetime.fromisoformat(alert.get("timestamp", ""))
                            if alert_time >= cutoff:
                                alerts.append(alert)
                except Exception as e:
                    logger.error(f"Failed to read alerts from {filepath}: {e}")
        
        return sorted(alerts, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def clear_alerts(self) -> None:
        """Clear alert history"""
        self._last_alerts.clear()
