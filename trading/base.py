# -*- coding: utf-8 -*-
"""
===================================
Trading Module - Base Classes
===================================

This module provides base classes for stock trading functionality.

Features:
- Broker abstraction for multiple trading platforms
- Order management
- Position tracking
- Risk control

Supported brokers:
- XQ (XueQiu)
- THS (TongHuaShun)
- Eastmoney
- Custom brokers via plugin

Note: Trading functionality requires proper account configuration.
Always test with paper trading first!
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Order side (buy/sell)"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type"""
    MARKET = "market"  # Market order
    LIMIT = "limit"    # Limit order
    STOP = "stop"      # Stop order
    STOP_LIMIT = "stop_limit"  # Stop-limit order


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Order:
    """
    Order data class
    
    Represents a trading order with all necessary information.
    """
    order_id: str
    stock_code: str
    stock_name: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.LIMIT
    quantity: int = 0
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: float = 0.0
    commission: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "order_id": self.order_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "commission": self.commission,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message": self.message,
        }


@dataclass
class Position:
    """
    Position data class
    
    Represents a stock position in the portfolio.
    """
    stock_code: str
    stock_name: str = ""
    quantity: int = 0
    available_quantity: int = 0
    cost_price: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    profit_loss: float = 0.0
    profit_loss_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "quantity": self.quantity,
            "available_quantity": self.available_quantity,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "profit_loss": self.profit_loss,
            "profit_loss_pct": self.profit_loss_pct,
        }


@dataclass
class AccountInfo:
    """
    Account information data class
    """
    account_id: str
    account_name: str = ""
    total_assets: float = 0.0
    available_cash: float = 0.0
    market_value: float = 0.0
    profit_loss: float = 0.0
    profit_loss_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "total_assets": self.total_assets,
            "available_cash": self.available_cash,
            "market_value": self.market_value,
            "profit_loss": self.profit_loss,
            "profit_loss_pct": self.profit_loss_pct,
        }


class BaseBroker(ABC):
    """
    Abstract base class for trading brokers
    
    All broker implementations must inherit from this class
    and implement the required methods.
    """
    
    name: str = "BaseBroker"
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the broker
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the broker
        
        Returns:
            True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if connected to the broker
        
        Returns:
            True if connected, False otherwise
        """
        pass
    
    @abstractmethod
    def get_account_info(self) -> Optional[AccountInfo]:
        """
        Get account information
        
        Returns:
            AccountInfo object or None if failed
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """
        Get all positions
        
        Returns:
            List of Position objects
        """
        pass
    
    @abstractmethod
    def get_position(self, stock_code: str) -> Optional[Position]:
        """
        Get position for a specific stock
        
        Args:
            stock_code: Stock code
            
        Returns:
            Position object or None if not found
        """
        pass
    
    @abstractmethod
    def submit_order(self, order: Order) -> Order:
        """
        Submit an order
        
        Args:
            order: Order to submit
            
        Returns:
            Updated order with status
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order by ID
        
        Args:
            order_id: Order ID
            
        Returns:
            Order object or None if not found
        """
        pass
    
    @abstractmethod
    def get_orders(
        self,
        stock_code: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        days: int = 7
    ) -> List[Order]:
        """
        Get orders with optional filters
        
        Args:
            stock_code: Filter by stock code
            status: Filter by status
            days: Number of days to look back
            
        Returns:
            List of Order objects
        """
        pass


class TradingError(Exception):
    """Base exception for trading errors"""
    pass


class ConnectionError(TradingError):
    """Connection error"""
    pass


class OrderError(TradingError):
    """Order submission error"""
    pass


class InsufficientFundsError(TradingError):
    """Insufficient funds error"""
    pass


class InsufficientSharesError(TradingError):
    """Insufficient shares error"""
    pass
