# -*- coding: utf-8 -*-
"""
Time Slice Module

This module provides time slice functionality for stock data analysis.
Supports multiple timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


class TimeFrame(Enum):
    """Time frame enumeration"""
    MIN_1 = "1m"
    MIN_5 = "5m"
    MIN_15 = "15m"
    MIN_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"
    
    @classmethod
    def from_string(cls, value: str) -> "TimeFrame":
        """Create TimeFrame from string"""
        mapping = {
            "1m": cls.MIN_1,
            "5m": cls.MIN_5,
            "15m": cls.MIN_15,
            "30m": cls.MIN_30,
            "1h": cls.HOUR_1,
            "4h": cls.HOUR_4,
            "1d": cls.DAY_1,
            "1w": cls.WEEK_1,
            "1M": cls.MONTH_1,
            "daily": cls.DAY_1,
            "weekly": cls.WEEK_1,
            "monthly": cls.MONTH_1,
        }
        return mapping.get(value.lower(), cls.DAY_1)
    
    @property
    def minutes(self) -> int:
        """Get time frame in minutes"""
        mapping = {
            TimeFrame.MIN_1: 1,
            TimeFrame.MIN_5: 5,
            TimeFrame.MIN_15: 15,
            TimeFrame.MIN_30: 30,
            TimeFrame.HOUR_1: 60,
            TimeFrame.HOUR_4: 240,
            TimeFrame.DAY_1: 1440,
            TimeFrame.WEEK_1: 10080,
            TimeFrame.MONTH_1: 43200,
        }
        return mapping[self]
    
    @property
    def is_intraday(self) -> bool:
        """Check if timeframe is intraday"""
        return self in (
            TimeFrame.MIN_1,
            TimeFrame.MIN_5,
            TimeFrame.MIN_15,
            TimeFrame.MIN_30,
            TimeFrame.HOUR_1,
            TimeFrame.HOUR_4,
        )


@dataclass
class TimeSliceConfig:
    """Time slice configuration"""
    timeframe: TimeFrame = TimeFrame.DAY_1
    include_indicators: bool = True
    include_volume: bool = True
    custom_start: Optional[datetime] = None
    custom_end: Optional[datetime] = None


@dataclass
class TimeSlice:
    """
    Time slice data class
    
    Represents a single time slice with OHLCV data and indicators.
    """
    stock_code: str
    timeframe: TimeFrame
    timestamp: datetime
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    amount: float = 0.0
    trade_count: int = 0
    indicators: Dict[str, float] = field(default_factory=dict)
    
    @property
    def range(self) -> float:
        """Get price range (high - low)"""
        return self.high - self.low
    
    @property
    def body(self) -> float:
        """Get candle body (close - open)"""
        return self.close - self.open
    
    @property
    def body_pct(self) -> float:
        """Get body percentage"""
        if self.open == 0:
            return 0
        return (self.close - self.open) / self.open * 100
    
    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish"""
        return self.close < self.open
    
    @property
    def upper_shadow(self) -> float:
        """Get upper shadow"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """Get lower shadow"""
        return min(self.open, self.close) - self.low
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stock_code": self.stock_code,
            "timeframe": self.timeframe.value,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "trade_count": self.trade_count,
            "indicators": self.indicators,
        }
    
    def to_ohlcv_dict(self) -> Dict[str, Any]:
        """Convert to OHLCV dictionary"""
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class TimeSliceGenerator:
    """
    Time slice generator for creating time slices from raw data
    """
    
    def __init__(self, config: Optional[TimeSliceConfig] = None):
        """
        Initialize time slice generator
        
        Args:
            config: Time slice configuration
        """
        self.config = config or TimeSliceConfig()
    
    def generate(
        self,
        data: pd.DataFrame,
        stock_code: str,
        timeframe: Optional[TimeFrame] = None
    ) -> List[TimeSlice]:
        """
        Generate time slices from data
        
        Args:
            data: DataFrame with timestamp and OHLCV columns
            stock_code: Stock code
            timeframe: Target timeframe (overrides config)
            
        Returns:
            List of TimeSlice objects
        """
        tf = timeframe or self.config.timeframe
        
        if data.empty:
            return []
        
        df = data.copy()
        
        if "date" in df.columns:
            df["timestamp"] = pd.to_datetime(df["date"])
        elif "timestamp" not in df.columns:
            df["timestamp"] = df.index
        
        df = df.set_index("timestamp")
        
        resampled = self._resample_data(df, tf)
        
        slices = []
        for timestamp, row in resampled.iterrows():
            time_slice = TimeSlice(
                stock_code=stock_code,
                timeframe=tf,
                timestamp=timestamp.to_pydatetime(),
                open=row.get("open", 0),
                high=row.get("high", 0),
                low=row.get("low", 0),
                close=row.get("close", 0),
                volume=int(row.get("volume", 0)),
                amount=row.get("amount", 0),
            )
            slices.append(time_slice)
        
        return slices
    
    def _resample_data(self, df: pd.DataFrame, timeframe: TimeFrame) -> pd.DataFrame:
        """
        Resample data to target timeframe
        
        Args:
            df: Input DataFrame
            timeframe: Target timeframe
            
        Returns:
            Resampled DataFrame
        """
        if timeframe == TimeFrame.MIN_1:
            return df
        elif timeframe == TimeFrame.MIN_5:
            rule = "5T"
        elif timeframe == TimeFrame.MIN_15:
            rule = "15T"
        elif timeframe == TimeFrame.MIN_30:
            rule = "30T"
        elif timeframe == TimeFrame.HOUR_1:
            rule = "1H"
        elif timeframe == TimeFrame.HOUR_4:
            rule = "4H"
        elif timeframe == TimeFrame.DAY_1:
            rule = "1D"
        elif timeframe == TimeFrame.WEEK_1:
            rule = "1W"
        elif timeframe == TimeFrame.MONTH_1:
            rule = "1M"
        else:
            return df
        
        agg_dict = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
        
        if "amount" in df.columns:
            agg_dict["amount"] = "sum"
        
        return df.resample(rule).agg(agg_dict).dropna()
    
    def generate_from_ticks(
        self,
        ticks: List[Dict[str, Any]],
        stock_code: str,
        timeframe: TimeFrame = TimeFrame.MIN_5
    ) -> List[TimeSlice]:
        """
        Generate time slices from tick data
        
        Args:
            ticks: List of tick dictionaries
            stock_code: Stock code
            timeframe: Target timeframe
            
        Returns:
            List of TimeSlice objects
        """
        if not ticks:
            return []
        
        df = pd.DataFrame(ticks)
        
        if "price" in df.columns and "close" not in df.columns:
            df["close"] = df["price"]
        
        if "timestamp" not in df.columns and "time" in df.columns:
            df["timestamp"] = pd.to_datetime(df["time"])
        
        return self.generate(df, stock_code, timeframe)


class TimeSliceAnalyzer:
    """
    Time slice analyzer for analyzing time slice patterns
    """
    
    def __init__(self):
        """Initialize time slice analyzer"""
        pass
    
    def analyze_pattern(self, slices: List[TimeSlice]) -> Dict[str, Any]:
        """
        Analyze time slice patterns
        
        Args:
            slices: List of time slices
            
        Returns:
            Pattern analysis results
        """
        if not slices:
            return {}
        
        closes = [s.close for s in slices]
        volumes = [s.volume for s in slices]
        
        bullish_count = sum(1 for s in slices if s.is_bullish)
        bearish_count = sum(1 for s in slices if s.is_bearish)
        
        avg_range = np.mean([s.range for s in slices])
        avg_body = np.mean([abs(s.body) for s in slices])
        
        return {
            "total_slices": len(slices),
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "bullish_ratio": bullish_count / len(slices) if slices else 0,
            "avg_range": avg_range,
            "avg_body": avg_body,
            "avg_volume": np.mean(volumes),
            "price_change": (closes[-1] - closes[0]) / closes[0] * 100 if closes else 0,
        }
    
    def find_support_resistance(
        self,
        slices: List[TimeSlice],
        window: int = 20
    ) -> Dict[str, List[float]]:
        """
        Find support and resistance levels
        
        Args:
            slices: List of time slices
            window: Window size for finding levels
            
        Returns:
            Dictionary with support and resistance levels
        """
        if len(slices) < window:
            return {"support": [], "resistance": []}
        
        df = pd.DataFrame([s.to_ohlcv_dict() for s in slices])
        
        df["local_high"] = df["high"].rolling(window, center=True).max()
        df["local_low"] = df["low"].rolling(window, center=True).min()
        
        resistance_levels = df[df["high"] == df["local_high"]]["high"].tolist()
        support_levels = df[df["low"] == df["local_low"]]["low"].tolist()
        
        return {
            "support": sorted(set(support_levels), reverse=True)[:5],
            "resistance": sorted(set(resistance_levels))[:5],
        }
    
    def detect_gaps(self, slices: List[TimeSlice]) -> List[Dict[str, Any]]:
        """
        Detect price gaps
        
        Args:
            slices: List of time slices
            
        Returns:
            List of gap information
        """
        if len(slices) < 2:
            return []
        
        gaps = []
        for i in range(1, len(slices)):
            prev = slices[i - 1]
            curr = slices[i]
            
            if curr.low > prev.high:
                gaps.append({
                    "type": "up",
                    "timestamp": curr.timestamp,
                    "gap_size": curr.low - prev.high,
                    "gap_pct": (curr.low - prev.high) / prev.high * 100,
                    "prev_close": prev.close,
                    "curr_open": curr.open,
                })
            elif curr.high < prev.low:
                gaps.append({
                    "type": "down",
                    "timestamp": curr.timestamp,
                    "gap_size": prev.low - curr.high,
                    "gap_pct": (prev.low - curr.high) / prev.low * 100,
                    "prev_close": prev.close,
                    "curr_open": curr.open,
                })
        
        return gaps
