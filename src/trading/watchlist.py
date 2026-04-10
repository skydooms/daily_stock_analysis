# -*- coding: utf-8 -*-
"""
Watchlist Management Module
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class WatchStatus(Enum):
    """Watch item status"""
    WATCHING = "watching"
    POSITION = "position"
    CLOSED = "closed"


@dataclass
class WatchItem:
    """Watch item for a single stock"""
    stock_code: str
    stock_name: str = ""
    status: WatchStatus = WatchStatus.WATCHING
    added_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    watch_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "status": self.status.value,
            "added_at": self.added_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "watch_price": self.watch_price,
            "target_price": self.target_price,
            "stop_loss_price": self.stop_loss_price,
            "notes": self.notes,
            "tags": self.tags,
        }


class Watchlist:
    """Watchlist manager for multiple stocks"""
    
    def __init__(self):
        self._items: Dict[str, WatchItem] = {}
    
    def add(self, stock_code: str, stock_name: str = "", **kwargs) -> WatchItem:
        """Add stock to watchlist"""
        if stock_code in self._items:
            item = self._items[stock_code]
            item.updated_at = datetime.now()
            return item
        
        item = WatchItem(
            stock_code=stock_code,
            stock_name=stock_name,
            **kwargs
        )
        self._items[stock_code] = item
        return item
    
    def remove(self, stock_code: str) -> bool:
        """Remove stock from watchlist"""
        if stock_code in self._items:
            del self._items[stock_code]
            return True
        return False
    
    def get(self, stock_code: str) -> Optional[WatchItem]:
        """Get watch item by stock code"""
        return self._items.get(stock_code)
    
    def get_all(self) -> List[WatchItem]:
        """Get all watch items"""
        return list(self._items.values())
    
    def get_by_status(self, status: WatchStatus) -> List[WatchItem]:
        """Get watch items by status"""
        return [item for item in self._items.values() if item.status == status]
    
    def update_status(self, stock_code: str, status: WatchStatus) -> bool:
        """Update watch item status"""
        if stock_code in self._items:
            self._items[stock_code].status = status
            self._items[stock_code].updated_at = datetime.now()
            return True
        return False
    
    def update_price(self, stock_code: str, price: float) -> bool:
        """Update watch price"""
        if stock_code in self._items:
            self._items[stock_code].watch_price = price
            self._items[stock_code].updated_at = datetime.now()
            return True
        return False
    
    def count(self) -> int:
        """Get total count of watch items"""
        return len(self._items)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "count": self.count(),
            "items": [item.to_dict() for item in self._items.values()],
        }
