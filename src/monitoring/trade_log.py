# -*- coding: utf-8 -*-
"""
Trade Log Module

This module provides trade logging and tracking functionality.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import json
import os


logger = logging.getLogger(__name__)


class TradeType(Enum):
    """Trade type enumeration"""
    BUY = "buy"
    SELL = "sell"


class TradeStatus(Enum):
    """Trade status enumeration"""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class TradeRecord:
    """
    Trade record data class
    
    Represents a single trade execution record.
    """
    trade_id: str
    stock_code: str
    stock_name: str = ""
    trade_type: TradeType = TradeType.BUY
    quantity: int = 0
    price: float = 0.0
    amount: float = 0.0
    fee: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    status: TradeStatus = TradeStatus.EXECUTED
    pnl: float = 0.0
    pnl_pct: float = 0.0
    signal_reason: str = ""
    strategy_name: str = ""
    notes: str = ""
    
    def __post_init__(self):
        """Calculate amount if not provided"""
        if self.amount == 0 and self.quantity > 0 and self.price > 0:
            self.amount = self.quantity * self.price
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trade_id": self.trade_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "trade_type": self.trade_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "signal_reason": self.signal_reason,
            "strategy_name": self.strategy_name,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradeRecord":
        """Create TradeRecord from dictionary"""
        return cls(
            trade_id=data["trade_id"],
            stock_code=data["stock_code"],
            stock_name=data.get("stock_name", ""),
            trade_type=TradeType(data["trade_type"]),
            quantity=data["quantity"],
            price=data["price"],
            amount=data["amount"],
            fee=data.get("fee", 0),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            status=TradeStatus(data.get("status", "executed")),
            pnl=data.get("pnl", 0),
            pnl_pct=data.get("pnl_pct", 0),
            signal_reason=data.get("signal_reason", ""),
            strategy_name=data.get("strategy_name", ""),
            notes=data.get("notes", ""),
        )


class TradeLog:
    """
    Trade log manager
    
    Manages trade records with persistence and query capabilities.
    """
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize trade log
        
        Args:
            log_file: Path to trade log file
        """
        self._trades: List[TradeRecord] = []
        self._log_file = log_file
        self._trade_counter = 0
        
        if log_file and os.path.exists(log_file):
            self._load_from_file()
    
    def add_trade(self, trade: TradeRecord) -> None:
        """
        Add a trade record
        
        Args:
            trade: TradeRecord to add
        """
        self._trades.append(trade)
        self._trade_counter += 1
        
        if self._log_file:
            self._save_to_file()
        
        logger.info(f"Trade recorded: {trade.trade_id} - {trade.trade_type.value} {trade.quantity} {trade.stock_code}")
    
    def create_trade(
        self,
        stock_code: str,
        trade_type: TradeType,
        quantity: int,
        price: float,
        stock_name: str = "",
        fee: float = 0.0,
        signal_reason: str = "",
        strategy_name: str = "",
        notes: str = ""
    ) -> TradeRecord:
        """
        Create and add a new trade record
        
        Args:
            stock_code: Stock code
            trade_type: Buy or sell
            quantity: Number of shares
            price: Trade price
            stock_name: Stock name
            fee: Trading fee
            signal_reason: Reason for trade signal
            strategy_name: Strategy that generated signal
            notes: Additional notes
            
        Returns:
            Created TradeRecord
        """
        self._trade_counter += 1
        trade_id = f"T{datetime.now().strftime('%Y%m%d%H%M%S')}{self._trade_counter:04d}"
        
        trade = TradeRecord(
            trade_id=trade_id,
            stock_code=stock_code,
            stock_name=stock_name,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            fee=fee,
            signal_reason=signal_reason,
            strategy_name=strategy_name,
            notes=notes,
        )
        
        self.add_trade(trade)
        return trade
    
    def get_trades(
        self,
        stock_code: Optional[str] = None,
        trade_type: Optional[TradeType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[TradeStatus] = None
    ) -> List[TradeRecord]:
        """
        Get trades with optional filters
        
        Args:
            stock_code: Filter by stock code
            trade_type: Filter by trade type
            start_date: Filter by start date
            end_date: Filter by end date
            status: Filter by status
            
        Returns:
            List of matching TradeRecords
        """
        result = self._trades
        
        if stock_code:
            result = [t for t in result if t.stock_code == stock_code]
        
        if trade_type:
            result = [t for t in result if t.trade_type == trade_type]
        
        if start_date:
            result = [t for t in result if t.timestamp >= start_date]
        
        if end_date:
            result = [t for t in result if t.timestamp <= end_date]
        
        if status:
            result = [t for t in result if t.status == status]
        
        return result
    
    def get_trade_by_id(self, trade_id: str) -> Optional[TradeRecord]:
        """Get trade by ID"""
        for trade in self._trades:
            if trade.trade_id == trade_id:
                return trade
        return None
    
    def update_trade(self, trade_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a trade record
        
        Args:
            trade_id: Trade ID to update
            updates: Dictionary of fields to update
            
        Returns:
            True if trade was found and updated
        """
        trade = self.get_trade_by_id(trade_id)
        if not trade:
            return False
        
        for key, value in updates.items():
            if hasattr(trade, key):
                setattr(trade, key, value)
        
        if self._log_file:
            self._save_to_file()
        
        return True
    
    def delete_trade(self, trade_id: str) -> bool:
        """
        Delete a trade record
        
        Args:
            trade_id: Trade ID to delete
            
        Returns:
            True if trade was found and deleted
        """
        for i, trade in enumerate(self._trades):
            if trade.trade_id == trade_id:
                self._trades.pop(i)
                if self._log_file:
                    self._save_to_file()
                return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get trade statistics
        
        Returns:
            Dictionary with trade statistics
        """
        if not self._trades:
            return {
                "total_trades": 0,
                "buy_trades": 0,
                "sell_trades": 0,
                "total_volume": 0,
                "total_amount": 0.0,
                "total_fees": 0.0,
                "total_pnl": 0.0,
            }
        
        buy_trades = [t for t in self._trades if t.trade_type == TradeType.BUY]
        sell_trades = [t for t in self._trades if t.trade_type == TradeType.SELL]
        
        return {
            "total_trades": len(self._trades),
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "total_volume": sum(t.quantity for t in self._trades),
            "total_amount": sum(t.amount for t in self._trades),
            "total_fees": sum(t.fee for t in self._trades),
            "total_pnl": sum(t.pnl for t in sell_trades),
            "avg_pnl": sum(t.pnl for t in sell_trades) / len(sell_trades) if sell_trades else 0,
        }
    
    def export_to_csv(self, filepath: str) -> bool:
        """
        Export trades to CSV file
        
        Args:
            filepath: Output file path
            
        Returns:
            True if export successful
        """
        try:
            import csv
            
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                writer.writerow([
                    "trade_id", "stock_code", "stock_name", "trade_type",
                    "quantity", "price", "amount", "fee", "timestamp",
                    "status", "pnl", "pnl_pct", "signal_reason", "strategy_name", "notes"
                ])
                
                for trade in self._trades:
                    writer.writerow([
                        trade.trade_id,
                        trade.stock_code,
                        trade.stock_name,
                        trade.trade_type.value,
                        trade.quantity,
                        trade.price,
                        trade.amount,
                        trade.fee,
                        trade.timestamp.isoformat(),
                        trade.status.value,
                        trade.pnl,
                        trade.pnl_pct,
                        trade.signal_reason,
                        trade.strategy_name,
                        trade.notes,
                    ])
            
            logger.info(f"Trades exported to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def _save_to_file(self) -> None:
        """Save trades to file"""
        try:
            data = [t.to_dict() for t in self._trades]
            with open(self._log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Save to file failed: {e}")
    
    def _load_from_file(self) -> None:
        """Load trades from file"""
        try:
            with open(self._log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._trades = [TradeRecord.from_dict(d) for d in data]
            self._trade_counter = len(self._trades)
            
        except Exception as e:
            logger.error(f"Load from file failed: {e}")
    
    def __len__(self) -> int:
        return len(self._trades)
    
    def __iter__(self):
        return iter(self._trades)
