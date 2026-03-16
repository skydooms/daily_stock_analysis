# -*- coding: utf-8 -*-
"""
Moving Average Strategy

This module implements trading strategies based on moving averages.
Includes: MA crossover, MA support/resistance, MA trend following.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np

from ..base import BaseStrategy, Signal, SignalType, StrategyConfig, StrategyType
from ..indicators import IndicatorCalculator


logger = logging.getLogger(__name__)


@dataclass
class MAStrategyConfig(StrategyConfig):
    """MA Strategy configuration"""
    name: str = "MAStrategy"
    description: str = "Moving Average Crossover Strategy"
    strategy_type: StrategyType = StrategyType.TREND_FOLLOWING
    fast_period: int = 5
    slow_period: int = 10
    signal_period: int = 20
    ma_type: str = "sma"  # sma or ema
    cross_threshold: float = 0.0  # Minimum crossover percentage to trigger signal


class MAStrategy(BaseStrategy):
    """
    Moving Average Strategy
    
    Generates buy/sell signals based on moving average crossovers.
    
    Buy signals:
    - Fast MA crosses above slow MA (golden cross)
    - Price bounces off MA support
    
    Sell signals:
    - Fast MA crosses below slow MA (death cross)
    - Price breaks below MA support
    """
    
    name = "MAStrategy"
    description = "Moving Average Crossover Strategy"
    strategy_type = StrategyType.TREND_FOLLOWING
    
    def __init__(self, config: Optional[MAStrategyConfig] = None):
        """
        Initialize MA Strategy
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config or MAStrategyConfig())
        self.fast_period = self.get_param("fast_period", 5)
        self.slow_period = self.get_param("slow_period", 10)
        self.signal_period = self.get_param("signal_period", 20)
        self.ma_type = self.get_param("ma_type", "sma")
        self.cross_threshold = self.get_param("cross_threshold", 0.0)
    
    def get_required_indicators(self) -> List[str]:
        """Get required indicators"""
        return ["ma5", "ma10", "ma20"]
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Generate trading signals
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            List of Signal objects
        """
        if not self.validate_data(data):
            return []
        
        signals = []
        
        df = self._calculate_indicators(data)
        
        for i in range(max(self.fast_period, self.slow_period, self.signal_period), len(df)):
            signal = self._check_signal(df, i)
            if signal:
                signals.append(signal)
        
        return signals
    
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MA indicators
        
        Args:
            data: Input DataFrame
            
        Returns:
            DataFrame with MA columns
        """
        df = data.copy()
        close = df["close"].values
        
        if self.ma_type == "ema":
            df["fast_ma"] = IndicatorCalculator.ema(close, self.fast_period)
            df["slow_ma"] = IndicatorCalculator.ema(close, self.slow_period)
            df["signal_ma"] = IndicatorCalculator.ema(close, self.signal_period)
        else:
            df["fast_ma"] = IndicatorCalculator.sma(close, self.fast_period)
            df["slow_ma"] = IndicatorCalculator.sma(close, self.slow_period)
            df["signal_ma"] = IndicatorCalculator.sma(close, self.signal_period)
        
        df["ma_diff"] = df["fast_ma"] - df["slow_ma"]
        df["ma_diff_pct"] = (df["fast_ma"] / df["slow_ma"] - 1) * 100
        
        return df
    
    def _check_signal(self, df: pd.DataFrame, i: int) -> Optional[Signal]:
        """
        Check for trading signal at index i
        
        Args:
            df: DataFrame with indicators
            i: Current index
            
        Returns:
            Signal if found, None otherwise
        """
        if i < 1:
            return None
        
        current = df.iloc[i]
        previous = df.iloc[i - 1]
        
        current_diff = current["ma_diff"]
        previous_diff = previous["ma_diff"]
        
        timestamp = current.get("date", current.name)
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
        elif isinstance(timestamp, (int, float)):
            timestamp = pd.to_datetime(timestamp, unit="s")
        
        if previous_diff <= 0 and current_diff > 0:
            if abs(current["ma_diff_pct"]) >= self.cross_threshold:
                return Signal(
                    stock_code="",
                    signal_type=SignalType.BUY,
                    price=current["close"],
                    timestamp=timestamp,
                    confidence=self._calculate_confidence(df, i, SignalType.BUY),
                    reason=f"Golden cross: MA{self.fast_period} crossed above MA{self.slow_period}",
                    indicators={
                        "fast_ma": current["fast_ma"],
                        "slow_ma": current["slow_ma"],
                        "signal_ma": current["signal_ma"],
                        "ma_diff_pct": current["ma_diff_pct"],
                    }
                )
        
        elif previous_diff >= 0 and current_diff < 0:
            if abs(current["ma_diff_pct"]) >= self.cross_threshold:
                return Signal(
                    stock_code="",
                    signal_type=SignalType.SELL,
                    price=current["close"],
                    timestamp=timestamp,
                    confidence=self._calculate_confidence(df, i, SignalType.SELL),
                    reason=f"Death cross: MA{self.fast_period} crossed below MA{self.slow_period}",
                    indicators={
                        "fast_ma": current["fast_ma"],
                        "slow_ma": current["slow_ma"],
                        "signal_ma": current["signal_ma"],
                        "ma_diff_pct": current["ma_diff_pct"],
                    }
                )
        
        return None
    
    def _calculate_confidence(
        self,
        df: pd.DataFrame,
        i: int,
        signal_type: SignalType
    ) -> float:
        """
        Calculate signal confidence
        
        Args:
            df: DataFrame with indicators
            i: Current index
            signal_type: Type of signal
            
        Returns:
            Confidence score (0-1)
        """
        current = df.iloc[i]
        confidence = 0.5
        
        if signal_type == SignalType.BUY:
            if current["close"] > current["signal_ma"]:
                confidence += 0.1
            
            if i >= 5:
                recent_trend = df.iloc[i-5:i]["close"].pct_change().mean()
                if recent_trend > 0:
                    confidence += 0.1
            
            volume = current.get("volume", 0)
            if i >= 5:
                avg_volume = df.iloc[i-5:i]["volume"].mean()
                if volume > avg_volume * 1.5:
                    confidence += 0.1
        
        elif signal_type == SignalType.SELL:
            if current["close"] < current["signal_ma"]:
                confidence += 0.1
            
            if i >= 5:
                recent_trend = df.iloc[i-5:i]["close"].pct_change().mean()
                if recent_trend < 0:
                    confidence += 0.1
        
        return min(max(confidence, 0.0), 1.0)
    
    def get_ma_status(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get current MA status
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with MA status information
        """
        if len(data) < self.signal_period:
            return {}
        
        df = self._calculate_indicators(data)
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        return {
            "fast_ma": current["fast_ma"],
            "slow_ma": current["slow_ma"],
            "signal_ma": current["signal_ma"],
            "ma_diff": current["ma_diff"],
            "ma_diff_pct": current["ma_diff_pct"],
            "trend": "up" if current["ma_diff"] > 0 else "down",
            "trend_strength": abs(current["ma_diff_pct"]),
            "cross_signal": "golden" if previous["ma_diff"] <= 0 and current["ma_diff"] > 0
                           else "death" if previous["ma_diff"] >= 0 and current["ma_diff"] < 0
                           else "none",
            "price_vs_signal_ma": "above" if current["close"] > current["signal_ma"] else "below",
            "price_distance_ma": (current["close"] / current["signal_ma"] - 1) * 100,
        }


class MASupportStrategy(BaseStrategy):
    """
    MA Support/Resistance Strategy
    
    Generates signals when price bounces off or breaks through MA levels.
    """
    
    name = "MASupportStrategy"
    description = "MA Support/Resistance Strategy"
    strategy_type = StrategyType.MEAN_REVERSION
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        """Initialize MA Support Strategy"""
        super().__init__(config or StrategyConfig())
        self.ma_period = self.get_param("ma_period", 20)
        self.bounce_threshold = self.get_param("bounce_threshold", 0.02)
    
    def get_required_indicators(self) -> List[str]:
        """Get required indicators"""
        return ["ma20"]
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """Generate trading signals"""
        if not self.validate_data(data):
            return []
        
        signals = []
        df = data.copy()
        
        close = df["close"].values
        df["ma"] = IndicatorCalculator.sma(close, self.ma_period)
        
        for i in range(self.ma_period + 2, len(df)):
            signal = self._check_bounce_signal(df, i)
            if signal:
                signals.append(signal)
        
        return signals
    
    def _check_bounce_signal(self, df: pd.DataFrame, i: int) -> Optional[Signal]:
        """Check for bounce signal"""
        current = df.iloc[i]
        prev1 = df.iloc[i - 1]
        prev2 = df.iloc[i - 2]
        
        ma = current["ma"]
        close = current["close"]
        
        if pd.isna(ma):
            return None
        
        distance_pct = (close - ma) / ma
        
        timestamp = current.get("date", current.name)
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
        
        if (prev2["low"] <= ma <= prev1["low"] and 
            prev1["close"] > prev1["low"] and
            current["close"] > prev1["close"]):
            
            return Signal(
                stock_code="",
                signal_type=SignalType.BUY,
                price=close,
                timestamp=timestamp,
                confidence=0.6,
                reason=f"Price bounced off MA{self.ma_period} support",
                indicators={
                    "ma": ma,
                    "distance_pct": distance_pct * 100,
                }
            )
        
        if (prev2["high"] >= ma >= prev1["high"] and
            prev1["close"] < prev1["high"] and
            current["close"] < prev1["close"]):
            
            return Signal(
                stock_code="",
                signal_type=SignalType.SELL,
                price=close,
                timestamp=timestamp,
                confidence=0.6,
                reason=f"Price rejected at MA{self.ma_period} resistance",
                indicators={
                    "ma": ma,
                    "distance_pct": distance_pct * 100,
                }
            )
        
        return None
