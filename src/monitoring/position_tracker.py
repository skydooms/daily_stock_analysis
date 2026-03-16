# -*- coding: utf-8 -*-
"""
Position Tracker Module

This module provides position tracking and management functionality.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import os


logger = logging.getLogger(__name__)


@dataclass
class Position:
    """
    Position data class
    
    Represents a stock position with cost basis and current value.
    """
    stock_code: str
    stock_name: str = ""
    quantity: int = 0
    available_quantity: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    profit_loss: float = 0.0
    profit_loss_pct: float = 0.0
    open_date: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    notes: str = ""
    
    def __post_init__(self):
        """Initialize available quantity"""
        if self.available_quantity == 0 and self.quantity > 0:
            self.available_quantity = self.quantity
    
    def update_price(self, price: float) -> None:
        """
        Update current price and recalculate values
        
        Args:
            price: Current market price
        """
        self.current_price = price
        self.market_value = self.quantity * price
        self.last_update = datetime.now()
        
        if self.quantity > 0 and self.avg_cost > 0:
            self.profit_loss = (price - self.avg_cost) * self.quantity
            self.profit_loss_pct = (price / self.avg_cost - 1) * 100
    
    def add_shares(self, quantity: int, price: float) -> None:
        """
        Add shares to position
        
        Args:
            quantity: Number of shares to add
            price: Purchase price
        """
        if quantity <= 0 or price <= 0:
            return
        
        total_cost = self.avg_cost * self.quantity + price * quantity
        self.quantity += quantity
        self.available_quantity += quantity
        self.avg_cost = total_cost / self.quantity if self.quantity > 0 else 0
        self.last_update = datetime.now()
    
    def remove_shares(self, quantity: int) -> bool:
        """
        Remove shares from position
        
        Args:
            quantity: Number of shares to remove
            
        Returns:
            True if successful
        """
        if quantity <= 0 or quantity > self.available_quantity:
            return False
        
        self.quantity -= quantity
        self.available_quantity -= quantity
        self.last_update = datetime.now()
        
        return True
    
    def set_stop_loss(self, price: float) -> None:
        """Set stop loss price"""
        self.stop_loss_price = price
        self.last_update = datetime.now()
    
    def set_take_profit(self, price: float) -> None:
        """Set take profit price"""
        self.take_profit_price = price
        self.last_update = datetime.now()
    
    def check_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss is triggered"""
        if self.stop_loss_price and current_price <= self.stop_loss_price:
            return True
        return False
    
    def check_take_profit(self, current_price: float) -> bool:
        """Check if take profit is triggered"""
        if self.take_profit_price and current_price >= self.take_profit_price:
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "quantity": self.quantity,
            "available_quantity": self.available_quantity,
            "avg_cost": self.avg_cost,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "profit_loss": self.profit_loss,
            "profit_loss_pct": self.profit_loss_pct,
            "open_date": self.open_date.isoformat(),
            "last_update": self.last_update.isoformat(),
            "stop_loss_price": self.stop_loss_price,
            "take_profit_price": self.take_profit_price,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Position":
        """Create Position from dictionary"""
        return cls(
            stock_code=data["stock_code"],
            stock_name=data.get("stock_name", ""),
            quantity=data["quantity"],
            available_quantity=data.get("available_quantity", data["quantity"]),
            avg_cost=data["avg_cost"],
            current_price=data.get("current_price", 0),
            market_value=data.get("market_value", 0),
            profit_loss=data.get("profit_loss", 0),
            profit_loss_pct=data.get("profit_loss_pct", 0),
            open_date=datetime.fromisoformat(data["open_date"]) if "open_date" in data else datetime.now(),
            last_update=datetime.fromisoformat(data["last_update"]) if "last_update" in data else datetime.now(),
            stop_loss_price=data.get("stop_loss_price"),
            take_profit_price=data.get("take_profit_price"),
            notes=data.get("notes", ""),
        )


class PositionTracker:
    """
    Position tracker for managing multiple positions
    
    Tracks all open positions with real-time updates and risk management.
    """
    
    def __init__(self, data_file: Optional[str] = None):
        """
        Initialize position tracker
        
        Args:
            data_file: Path to position data file
        """
        self._positions: Dict[str, Position] = {}
        self._data_file = data_file
        
        if data_file and os.path.exists(data_file):
            self._load_from_file()
    
    def open_position(
        self,
        stock_code: str,
        quantity: int,
        price: float,
        stock_name: str = "",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Position:
        """
        Open a new position or add to existing
        
        Args:
            stock_code: Stock code
            quantity: Number of shares
            price: Purchase price
            stock_name: Stock name
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Position object
        """
        if stock_code in self._positions:
            position = self._positions[stock_code]
            position.add_shares(quantity, price)
        else:
            position = Position(
                stock_code=stock_code,
                stock_name=stock_name,
                quantity=quantity,
                available_quantity=quantity,
                avg_cost=price,
                current_price=price,
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
            )
            self._positions[stock_code] = position
        
        if self._data_file:
            self._save_to_file()
        
        logger.info(f"Position opened: {stock_code} - {quantity} shares @ {price}")
        
        return position
    
    def close_position(
        self,
        stock_code: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Close a position (partial or full)
        
        Args:
            stock_code: Stock code
            quantity: Number of shares to close (None = all)
            price: Closing price
            
        Returns:
            Dictionary with closing information
        """
        if stock_code not in self._positions:
            return None
        
        position = self._positions[stock_code]
        
        if quantity is None:
            quantity = position.quantity
        
        if quantity > position.available_quantity:
            quantity = position.available_quantity
        
        if price is None:
            price = position.current_price
        
        pnl = (price - position.avg_cost) * quantity
        pnl_pct = (price / position.avg_cost - 1) * 100 if position.avg_cost > 0 else 0
        
        result = {
            "stock_code": stock_code,
            "quantity": quantity,
            "avg_cost": position.avg_cost,
            "close_price": price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        }
        
        if quantity >= position.quantity:
            del self._positions[stock_code]
        else:
            position.remove_shares(quantity)
        
        if self._data_file:
            self._save_to_file()
        
        logger.info(f"Position closed: {stock_code} - {quantity} shares @ {price}, P&L: {pnl:.2f}")
        
        return result
    
    def update_prices(self, prices: Dict[str, float]) -> None:
        """
        Update prices for all positions
        
        Args:
            prices: Dictionary mapping stock codes to prices
        """
        for stock_code, price in prices.items():
            if stock_code in self._positions:
                self._positions[stock_code].update_price(price)
    
    def get_position(self, stock_code: str) -> Optional[Position]:
        """Get position by stock code"""
        return self._positions.get(stock_code)
    
    def get_all_positions(self) -> List[Position]:
        """Get all positions"""
        return list(self._positions.values())
    
    def get_total_value(self) -> float:
        """Get total market value of all positions"""
        return sum(p.market_value for p in self._positions.values())
    
    def get_total_cost(self) -> float:
        """Get total cost basis of all positions"""
        return sum(p.avg_cost * p.quantity for p in self._positions.values())
    
    def get_total_pnl(self) -> float:
        """Get total profit/loss"""
        return sum(p.profit_loss for p in self._positions.values())
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get position summary
        
        Returns:
            Dictionary with position summary
        """
        positions = self.get_all_positions()
        
        return {
            "total_positions": len(positions),
            "total_shares": sum(p.quantity for p in positions),
            "total_value": self.get_total_value(),
            "total_cost": self.get_total_cost(),
            "total_pnl": self.get_total_pnl(),
            "total_pnl_pct": (self.get_total_value() / self.get_total_cost() - 1) * 100 if self.get_total_cost() > 0 else 0,
            "positions": [p.to_dict() for p in positions],
        }
    
    def check_risk_alerts(self, prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Check for risk alerts (stop loss / take profit)
        
        Args:
            prices: Current prices dictionary
            
        Returns:
            List of risk alerts
        """
        alerts = []
        
        for stock_code, position in self._positions.items():
            price = prices.get(stock_code, position.current_price)
            
            if position.check_stop_loss(price):
                alerts.append({
                    "type": "stop_loss",
                    "stock_code": stock_code,
                    "current_price": price,
                    "stop_loss_price": position.stop_loss_price,
                    "message": f"Stop loss triggered for {stock_code}",
                })
            
            if position.check_take_profit(price):
                alerts.append({
                    "type": "take_profit",
                    "stock_code": stock_code,
                    "current_price": price,
                    "take_profit_price": position.take_profit_price,
                    "message": f"Take profit triggered for {stock_code}",
                })
        
        return alerts
    
    def _save_to_file(self) -> None:
        """Save positions to file"""
        try:
            data = {code: pos.to_dict() for code, pos in self._positions.items()}
            with open(self._data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Save positions failed: {e}")
    
    def _load_from_file(self) -> None:
        """Load positions from file"""
        try:
            with open(self._data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._positions = {
                code: Position.from_dict(pos_data)
                for code, pos_data in data.items()
            }
        except Exception as e:
            logger.error(f"Load positions failed: {e}")
    
    def __len__(self) -> int:
        return len(self._positions)
    
    def __contains__(self, stock_code: str) -> bool:
        return stock_code in self._positions
