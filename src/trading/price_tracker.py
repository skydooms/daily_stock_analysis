# -*- coding: utf-8 -*-
"""
Price Tracker - Track price statistics over 3 months

Tracks:
- price_min: Lowest price in 3 months
- price_max: Highest price in 3 months
- open_min: Lowest close price in 3 months
- close_max: Highest close price in 3 months
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class PriceStats:
    """Price statistics for a stock"""
    stock_code: str
    price_min: float
    price_max: float
    open_min: float
    close_max: float
    period_days: int = 90
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "stock_code": self.stock_code,
            "price_min": self.price_min,
            "price_max": self.price_max,
            "open_min": self.open_min,
            "close_max": self.close_max,
            "period_days": self.period_days,
            "updated_at": self.updated_at.isoformat(),
        }


class PriceTracker:
    """Track price statistics for stocks"""
    
    def __init__(self, period_days: int = 90):
        self.period_days = period_days
        self._stats: Dict[str, PriceStats] = {}
    
    def update(self, stock_code: str, data: pd.DataFrame) -> PriceStats:
        """
        Update price statistics for a stock
        
        Args:
            stock_code: Stock code
            data: DataFrame with columns: date, open, high, low, close
            
        Returns:
            Updated PriceStats
        """
        if data.empty:
            logger.warning(f"Empty data for {stock_code}")
            return self._stats.get(stock_code, PriceStats(
                stock_code=stock_code,
                price_min=0,
                price_max=0,
                open_min=0,
                close_max=0,
            ))
        
        cutoff_date = datetime.now() - timedelta(days=self.period_days)
        
        if "date" in data.columns:
            data = data.copy()
            data["date"] = pd.to_datetime(data["date"])
            recent_data = data[data["date"] >= cutoff_date]
        else:
            recent_data = data.tail(self.period_days)
        
        if recent_data.empty:
            recent_data = data
        
        low_col = "low" if "low" in recent_data.columns else "low"
        high_col = "high" if "high" in recent_data.columns else "high"
        close_col = "close" if "close" in recent_data.columns else "close"
        open_col = "open" if "open" in recent_data.columns else "open"
        
        price_min = float(recent_data[low_col].min())
        price_max = float(recent_data[high_col].max())
        open_min = float(recent_data[close_col].min())
        close_max = float(recent_data[close_col].max())
        
        stats = PriceStats(
            stock_code=stock_code,
            price_min=price_min,
            price_max=price_max,
            open_min=open_min,
            close_max=close_max,
            period_days=self.period_days,
        )
        
        self._stats[stock_code] = stats
        return stats
    
    def get(self, stock_code: str) -> Optional[PriceStats]:
        """Get price statistics for a stock"""
        return self._stats.get(stock_code)
    
    def get_all(self) -> Dict[str, PriceStats]:
        """Get all price statistics"""
        return self._stats
    
    def calculate_pullback_pct(self, stock_code: str, current_price: float) -> float:
        """
        Calculate pullback percentage from close_max
        
        Args:
            stock_code: Stock code
            current_price: Current price
            
        Returns:
            Pullback percentage (negative means price dropped)
        """
        stats = self.get(stock_code)
        if not stats or stats.close_max == 0:
            return 0.0
        
        return (current_price - stats.close_max) / stats.close_max
    
    def calculate_surge_pct(self, stock_code: str, current_price: float) -> float:
        """
        Calculate surge percentage from price_min
        
        Args:
            stock_code: Stock code
            current_price: Current price
            
        Returns:
            Surge percentage
        """
        stats = self.get(stock_code)
        if not stats or stats.price_min == 0:
            return 0.0
        
        return (current_price - stats.price_min) / stats.price_min
    
    def is_near_price_min(self, stock_code: str, current_price: float, threshold: float = 0.05) -> bool:
        """Check if price is near price_min"""
        stats = self.get(stock_code)
        if not stats:
            return False
        return current_price <= stats.price_min * (1 + threshold)
    
    def is_near_price_max(self, stock_code: str, current_price: float, threshold: float = 0.05) -> bool:
        """Check if price is near price_max"""
        stats = self.get(stock_code)
        if not stats:
            return False
        return current_price >= stats.price_max * (1 - threshold)
    
    def is_above_open_min_threshold(self, stock_code: str, current_price: float, multiplier: float = 1.22) -> bool:
        """Check if price is above open_min * multiplier"""
        stats = self.get(stock_code)
        if not stats:
            return False
        return current_price > stats.open_min * multiplier
    
    def is_above_price_min_threshold(self, stock_code: str, current_price: float, multiplier: float = 1.35) -> bool:
        """Check if price is above price_min * multiplier"""
        stats = self.get(stock_code)
        if not stats:
            return False
        return current_price > stats.price_min * multiplier
