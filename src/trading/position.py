# -*- coding: utf-8 -*-
"""
Position Management - Single stock position
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class PositionStatus(str, Enum):
    """Position status"""
    OPEN = "open"
    CLOSED = "closed"
    PARTIAL = "partial"


@dataclass
class Position:
    """
    Single stock position
    
    Attributes:
        stock_code: Stock code (e.g., "600519", "03759.HK")
        stock_name: Stock name
        shares: Number of shares held
        cost_price: Average cost price
        current_price: Current market price
        opened_at: Position open time
        updated_at: Last update time
        status: Position status
    """
    stock_code: str
    stock_name: str = ""
    shares: int = 0
    cost_price: float = 0.0
    current_price: float = 0.0
    opened_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: PositionStatus = PositionStatus.OPEN
    
    # Price tracking for 3 months
    price_min_3m: float = 0.0  # Lowest price in 3 months
    price_max_3m: float = 0.0  # Highest price in 3 months
    close_min_3m: float = 0.0  # Lowest close price in 3 months
    close_max_3m: float = 0.0  # Highest close price in 3 months
    
    @property
    def market_value(self) -> float:
        """Current market value"""
        return self.shares * self.current_price
    
    @property
    def cost_value(self) -> float:
        """Total cost value"""
        return self.shares * self.cost_price
    
    @property
    def profit_loss(self) -> float:
        """Profit/Loss amount"""
        return self.market_value - self.cost_value
    
    @property
    def profit_loss_pct(self) -> float:
        """Profit/Loss percentage"""
        if self.cost_value == 0:
            return 0.0
        return (self.profit_loss / self.cost_value) * 100
    
    def add_shares(self, shares: int, price: float) -> None:
        """Add shares to position (buy more)"""
        total_cost = self.cost_value + (shares * price)
        total_shares = self.shares + shares
        self.cost_price = total_cost / total_shares if total_shares > 0 else 0
        self.shares = total_shares
        self.updated_at = datetime.now()
    
    def reduce_shares(self, shares: int) -> float:
        """
        Reduce shares from position (sell)
        Returns the realized profit/loss
        """
        if shares > self.shares:
            shares = self.shares
        
        realized_pl = shares * (self.current_price - self.cost_price)
        self.shares -= shares
        self.updated_at = datetime.now()
        
        if self.shares == 0:
            self.status = PositionStatus.CLOSED
        elif self.shares > 0:
            self.status = PositionStatus.PARTIAL
        
        return realized_pl
    
    def update_price(self, price: float, price_min: float = None, price_max: float = None,
                     close_min: float = None, close_max: float = None) -> None:
        """Update current price and 3-month stats"""
        self.current_price = price
        self.updated_at = datetime.now()
        
        if price_min is not None:
            self.price_min_3m = price_min
        if price_max is not None:
            self.price_max_3m = price_max
        if close_min is not None:
            self.close_min_3m = close_min
        if close_max is not None:
            self.close_max_3m = close_max
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "shares": self.shares,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "cost_value": self.cost_value,
            "profit_loss": self.profit_loss,
            "profit_loss_pct": self.profit_loss_pct,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status.value,
            "price_min_3m": self.price_min_3m,
            "price_max_3m": self.price_max_3m,
            "close_min_3m": self.close_min_3m,
            "close_max_3m": self.close_max_3m,
        }
