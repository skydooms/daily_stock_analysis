# -*- coding: utf-8 -*-
"""
===================================
Trading Module - Risk Control
===================================

This module provides risk management functionality for trading.

Features:
- Position size limits
- Daily loss limits
- Risk per trade limits
- Portfolio risk assessment
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from .base import Order, OrderSide, Position, AccountInfo


logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_position_size: float = 0.1  # Max 10% of portfolio per position
    max_daily_loss: float = 0.05    # Max 5% daily loss
    max_risk_per_trade: float = 0.02  # Max 2% risk per trade
    max_positions: int = 10         # Max number of positions
    max_sector_exposure: float = 0.3  # Max 30% exposure per sector
    enable_auto_stop_loss: bool = True
    default_stop_loss_pct: float = 0.08  # Default 8% stop loss


class RiskManager:
    """
    Risk manager for trading operations
    
    Usage:
        risk_manager = RiskManager(config)
        
        # Check if order is allowed
        if risk_manager.can_open_position(order, account, positions):
            # Execute order
            pass
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """
        Initialize risk manager
        
        Args:
            config: Risk configuration
        """
        self.config = config or RiskConfig()
        self._daily_pnl: float = 0.0
        self._trades_today: int = 0
    
    def can_open_position(
        self,
        order: Order,
        account: AccountInfo,
        positions: List[Position]
    ) -> bool:
        """
        Check if opening a new position is allowed
        
        Args:
            order: Order to check
            account: Account information
            positions: Current positions
            
        Returns:
            True if position can be opened
        """
        if order.side != OrderSide.BUY:
            return True  # Selling is always allowed
        
        reasons = self._check_risk_rules(order, account, positions)
        
        if reasons:
            logger.warning(f"Order {order.order_id} rejected: {'; '.join(reasons)}")
            return False
        
        return True
    
    def get_rejection_reasons(
        self,
        order: Order,
        account: AccountInfo,
        positions: List[Position]
    ) -> List[str]:
        """
        Get reasons why an order would be rejected
        
        Args:
            order: Order to check
            account: Account information
            positions: Current positions
            
        Returns:
            List of rejection reasons
        """
        return self._check_risk_rules(order, account, positions)
    
    def calculate_position_size(
        self,
        stock_code: str,
        entry_price: float,
        stop_loss_price: float,
        account: AccountInfo
    ) -> int:
        """
        Calculate appropriate position size based on risk rules
        
        Args:
            stock_code: Stock code
            entry_price: Entry price
            stop_loss_price: Stop loss price
            account: Account information
            
        Returns:
            Number of shares to trade
        """
        if entry_price <= 0:
            return 0
        
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            risk_per_share = entry_price * self.config.default_stop_loss_pct
        
        max_risk_amount = account.total_assets * self.config.max_risk_per_trade
        max_shares_by_risk = int(max_risk_amount / risk_per_share)
        
        max_position_amount = account.total_assets * self.config.max_position_size
        max_shares_by_size = int(max_position_amount / entry_price)
        
        return min(max_shares_by_risk, max_shares_by_size)
    
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
    
    def update_daily_pnl(self, pnl: float) -> None:
        """
        Update daily P&L tracking
        
        Args:
            pnl: Profit/Loss amount
        """
        self._daily_pnl += pnl
        self._trades_today += 1
    
    def reset_daily_tracking(self) -> None:
        """Reset daily tracking (call at market open)"""
        self._daily_pnl = 0.0
        self._trades_today = 0
    
    def get_portfolio_risk(
        self,
        positions: List[Position],
        account: AccountInfo
    ) -> Dict[str, Any]:
        """
        Calculate portfolio risk metrics
        
        Args:
            positions: Current positions
            account: Account information
            
        Returns:
            Dictionary with risk metrics
        """
        total_market_value = sum(p.market_value for p in positions)
        total_risk = sum(
            abs(p.profit_loss) for p in positions if p.profit_loss < 0
        )
        
        return {
            "total_positions": len(positions),
            "total_market_value": total_market_value,
            "portfolio_exposure": total_market_value / account.total_assets if account.total_assets > 0 else 0,
            "total_risk": total_risk,
            "risk_ratio": total_risk / account.total_assets if account.total_assets > 0 else 0,
            "daily_pnl": self._daily_pnl,
            "trades_today": self._trades_today,
        }
    
    def _check_risk_rules(
        self,
        order: Order,
        account: AccountInfo,
        positions: List[Position]
    ) -> List[str]:
        """
        Check all risk rules
        
        Returns:
            List of violation reasons
        """
        reasons = []
        
        if order.side != OrderSide.BUY:
            return reasons
        
        order_value = order.quantity * (order.price or 0)
        
        if len(positions) >= self.config.max_positions:
            reasons.append(f"Max positions ({self.config.max_positions}) reached")
        
        if account.total_assets > 0:
            position_ratio = order_value / account.total_assets
            if position_ratio > self.config.max_position_size:
                reasons.append(
                    f"Position size ({position_ratio:.1%}) exceeds max ({self.config.max_position_size:.1%})"
                )
        
        if self._daily_pnl < 0:
            daily_loss_ratio = abs(self._daily_pnl) / account.total_assets
            if daily_loss_ratio >= self.config.max_daily_loss:
                reasons.append(
                    f"Daily loss ({daily_loss_ratio:.1%}) exceeds max ({self.config.max_daily_loss:.1%})"
                )
        
        if account.available_cash < order_value:
            reasons.append(
                f"Insufficient cash ({account.available_cash:.2f}) for order ({order_value:.2f})"
            )
        
        return reasons
