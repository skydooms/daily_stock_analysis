# -*- coding: utf-8 -*-
"""
Risk Manager Module

This module provides risk management functionality for trading.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import numpy as np


logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskConfig:
    """
    Risk management configuration
    
    Defines limits and thresholds for risk control.
    """
    max_position_size_pct: float = 0.1  # Max 10% per position
    max_sector_exposure_pct: float = 0.3  # Max 30% per sector
    max_total_exposure_pct: float = 0.8  # Max 80% total capital usage
    max_daily_loss_pct: float = 0.03  # Max 3% daily loss
    max_drawdown_pct: float = 0.1  # Max 10% drawdown
    default_stop_loss_pct: float = 0.08  # Default 8% stop loss
    default_take_profit_pct: float = 0.15  # Default 15% take profit
    max_trades_per_day: int = 10
    min_trade_interval_minutes: int = 5
    enable_auto_stop_loss: bool = True
    enable_auto_take_profit: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_position_size_pct": self.max_position_size_pct,
            "max_sector_exposure_pct": self.max_sector_exposure_pct,
            "max_total_exposure_pct": self.max_total_exposure_pct,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "default_stop_loss_pct": self.default_stop_loss_pct,
            "default_take_profit_pct": self.default_take_profit_pct,
            "max_trades_per_day": self.max_trades_per_day,
            "min_trade_interval_minutes": self.min_trade_interval_minutes,
            "enable_auto_stop_loss": self.enable_auto_stop_loss,
            "enable_auto_take_profit": self.enable_auto_take_profit,
        }


@dataclass
class RiskAlert:
    """Risk alert data class"""
    alert_type: str
    risk_level: RiskLevel
    message: str
    stock_code: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "alert_type": self.alert_type,
            "risk_level": self.risk_level.value,
            "message": self.message,
            "stock_code": self.stock_code,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "timestamp": self.timestamp.isoformat(),
        }


class RiskManager:
    """
    Risk manager for trading operations
    
    Provides risk assessment, position sizing, and risk alerts.
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """
        Initialize risk manager
        
        Args:
            config: Risk configuration
        """
        self.config = config or RiskConfig()
        self._daily_pnl: float = 0.0
        self._daily_trades: int = 0
        self._last_trade_time: Optional[datetime] = None
        self._peak_equity: float = 0.0
        self._alerts: List[RiskAlert] = []
    
    def can_open_position(
        self,
        stock_code: str,
        amount: float,
        total_capital: float,
        current_exposure: float,
        sector_exposure: Optional[Dict[str, float]] = None,
        stock_sector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if position can be opened
        
        Args:
            stock_code: Stock code
            amount: Position amount
            total_capital: Total capital
            current_exposure: Current total exposure
            sector_exposure: Current sector exposures
            stock_sector: Stock sector
            
        Returns:
            Dictionary with check result
        """
        reasons = []
        
        position_pct = amount / total_capital
        if position_pct > self.config.max_position_size_pct:
            reasons.append(
                f"Position size ({position_pct:.1%}) exceeds max ({self.config.max_position_size_pct:.1%})"
            )
        
        new_exposure = current_exposure + amount
        exposure_pct = new_exposure / total_capital
        if exposure_pct > self.config.max_total_exposure_pct:
            reasons.append(
                f"Total exposure ({exposure_pct:.1%}) would exceed max ({self.config.max_total_exposure_pct:.1%})"
            )
        
        if sector_exposure and stock_sector:
            sector_amount = sector_exposure.get(stock_sector, 0) + amount
            sector_pct = sector_amount / total_capital
            if sector_pct > self.config.max_sector_exposure_pct:
                reasons.append(
                    f"Sector exposure ({sector_pct:.1%}) would exceed max ({self.config.max_sector_exposure_pct:.1%})"
                )
        
        if self._daily_trades >= self.config.max_trades_per_day:
            reasons.append(
                f"Daily trade limit ({self.config.max_trades_per_day}) reached"
            )
        
        if self._last_trade_time:
            minutes_since_last = (datetime.now() - self._last_trade_time).total_seconds() / 60
            if minutes_since_last < self.config.min_trade_interval_minutes:
                reasons.append(
                    f"Trade interval too short ({minutes_since_last:.1f} min < {self.config.min_trade_interval_minutes} min)"
                )
        
        if self._daily_pnl / total_capital < -self.config.max_daily_loss_pct:
            reasons.append(
                f"Daily loss limit ({self.config.max_daily_loss_pct:.1%}) reached"
            )
        
        return {
            "allowed": len(reasons) == 0,
            "reasons": reasons,
            "position_pct": position_pct,
            "exposure_pct": exposure_pct,
        }
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        total_capital: float,
        risk_per_trade_pct: float = 0.02
    ) -> int:
        """
        Calculate position size based on risk
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            total_capital: Total capital
            risk_per_trade_pct: Risk per trade as % of capital
            
        Returns:
            Number of shares
        """
        if entry_price <= 0:
            return 0
        
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            risk_per_share = entry_price * self.config.default_stop_loss_pct
        
        max_risk_amount = total_capital * risk_per_trade_pct
        shares_by_risk = int(max_risk_amount / risk_per_share)
        
        max_position_amount = total_capital * self.config.max_position_size_pct
        shares_by_size = int(max_position_amount / entry_price)
        
        return min(shares_by_risk, shares_by_size)
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        position_type: str = "long"
    ) -> float:
        """
        Calculate stop loss price
        
        Args:
            entry_price: Entry price
            position_type: "long" or "short"
            
        Returns:
            Stop loss price
        """
        if position_type == "long":
            return entry_price * (1 - self.config.default_stop_loss_pct)
        else:
            return entry_price * (1 + self.config.default_stop_loss_pct)
    
    def calculate_take_profit(
        self,
        entry_price: float,
        position_type: str = "long"
    ) -> float:
        """
        Calculate take profit price
        
        Args:
            entry_price: Entry price
            position_type: "long" or "short"
            
        Returns:
            Take profit price
        """
        if position_type == "long":
            return entry_price * (1 + self.config.default_take_profit_pct)
        else:
            return entry_price * (1 - self.config.default_take_profit_pct)
    
    def update_daily_pnl(self, pnl: float) -> None:
        """
        Update daily P&L
        
        Args:
            pnl: Profit/loss amount
        """
        self._daily_pnl += pnl
        self._daily_trades += 1
        self._last_trade_time = datetime.now()
    
    def reset_daily(self) -> None:
        """Reset daily counters"""
        self._daily_pnl = 0.0
        self._daily_trades = 0
    
    def update_peak_equity(self, current_equity: float) -> None:
        """
        Update peak equity for drawdown calculation
        
        Args:
            current_equity: Current equity
        """
        if current_equity > self._peak_equity:
            self._peak_equity = current_equity
    
    def check_drawdown(self, current_equity: float) -> Optional[RiskAlert]:
        """
        Check if drawdown exceeds limit
        
        Args:
            current_equity: Current equity
            
        Returns:
            RiskAlert if limit exceeded
        """
        if self._peak_equity <= 0:
            return None
        
        drawdown_pct = (self._peak_equity - current_equity) / self._peak_equity
        
        if drawdown_pct >= self.config.max_drawdown_pct:
            alert = RiskAlert(
                alert_type="max_drawdown",
                risk_level=RiskLevel.CRITICAL,
                message=f"Drawdown ({drawdown_pct:.1%}) exceeds limit ({self.config.max_drawdown_pct:.1%})",
                current_value=drawdown_pct,
                threshold_value=self.config.max_drawdown_pct,
            )
            self._alerts.append(alert)
            return alert
        
        return None
    
    def check_daily_loss(self, total_capital: float) -> Optional[RiskAlert]:
        """
        Check if daily loss exceeds limit
        
        Args:
            total_capital: Total capital
            
        Returns:
            RiskAlert if limit exceeded
        """
        if total_capital <= 0:
            return None
        
        loss_pct = abs(self._daily_pnl) / total_capital if self._daily_pnl < 0 else 0
        
        if loss_pct >= self.config.max_daily_loss_pct:
            alert = RiskAlert(
                alert_type="daily_loss",
                risk_level=RiskLevel.HIGH,
                message=f"Daily loss ({loss_pct:.1%}) exceeds limit ({self.config.max_daily_loss_pct:.1%})",
                current_value=loss_pct,
                threshold_value=self.config.max_daily_loss_pct,
            )
            self._alerts.append(alert)
            return alert
        
        return None
    
    def get_risk_metrics(
        self,
        equity_curve: List[float],
        returns: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate risk metrics
        
        Args:
            equity_curve: Equity values over time
            returns: Daily returns (optional)
            
        Returns:
            Dictionary with risk metrics
        """
        if not equity_curve:
            return {}
        
        metrics = {}
        
        peak = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        metrics["max_drawdown"] = max_dd
        metrics["max_drawdown_pct"] = max_dd * 100
        
        if returns:
            metrics["volatility"] = np.std(returns) * np.sqrt(252)
            metrics["var_95"] = np.percentile(returns, 5)
            metrics["var_99"] = np.percentile(returns, 1)
            
            var_95 = metrics["var_95"]
            cvar_95 = np.mean([r for r in returns if r <= var_95])
            metrics["cvar_95"] = cvar_95
        
        return metrics
    
    def get_alerts(self, clear: bool = False) -> List[RiskAlert]:
        """
        Get all alerts
        
        Args:
            clear: Whether to clear alerts after retrieval
            
        Returns:
            List of RiskAlert objects
        """
        alerts = self._alerts.copy()
        if clear:
            self._alerts.clear()
        return alerts
    
    def clear_alerts(self) -> None:
        """Clear all alerts"""
        self._alerts.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get risk manager status
        
        Returns:
            Dictionary with status information
        """
        return {
            "daily_pnl": self._daily_pnl,
            "daily_trades": self._daily_trades,
            "peak_equity": self._peak_equity,
            "alert_count": len(self._alerts),
            "config": self.config.to_dict(),
        }
