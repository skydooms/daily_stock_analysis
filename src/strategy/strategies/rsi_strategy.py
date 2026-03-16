# -*- coding: utf-8 -*-
"""
RSI Strategy

This module implements trading strategies based on RSI indicator.
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
class RSIStrategyConfig(StrategyConfig):
    """RSI Strategy configuration"""
    name: str = "RSIStrategy"
    description: str = "RSI Overbought/Oversold Strategy"
    strategy_type: StrategyType = StrategyType.MEAN_REVERSION
    period: int = 14
    oversold_threshold: float = 30.0
    overbought_threshold: float = 70.0


class RSIStrategy(BaseStrategy):
    """
    RSI Strategy
    
    Generates buy/sell signals based on RSI overbought/oversold levels.
    
    Buy signals:
    - RSI crosses above oversold threshold (30)
    - RSI divergence with price
    
    Sell signals:
    - RSI crosses below overbought threshold (70)
    - RSI divergence with price
    """
    
    name = "RSIStrategy"
    description = "RSI Overbought/Oversold Strategy"
    strategy_type = StrategyType.MEAN_REVERSION
    
    def __init__(self, config: Optional[RSIStrategyConfig] = None):
        """Initialize RSI Strategy"""
        super().__init__(config or RSIStrategyConfig())
        self.period = self.get_param("period", 14)
        self.oversold = self.get_param("oversold_threshold", 30.0)
        self.overbought = self.get_param("overbought_threshold", 70.0)
    
    def get_required_indicators(self) -> List[str]:
        """Get required indicators"""
        return ["rsi14"]
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """Generate trading signals"""
        if not self.validate_data(data):
            return []
        
        signals = []
        df = self._calculate_indicators(data)
        
        for i in range(self.period + 2, len(df)):
            signal = self._check_signal(df, i)
            if signal:
                signals.append(signal)
        
        return signals
    
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI indicator"""
        df = data.copy()
        close = df["close"].values
        df["rsi"] = IndicatorCalculator.rsi(close, self.period)
        return df
    
    def _check_signal(self, df: pd.DataFrame, i: int) -> Optional[Signal]:
        """Check for trading signal"""
        if i < 1:
            return None
        
        current = df.iloc[i]
        previous = df.iloc[i - 1]
        
        rsi = current["rsi"]
        prev_rsi = previous["rsi"]
        
        if pd.isna(rsi) or pd.isna(prev_rsi):
            return None
        
        timestamp = current.get("date", current.name)
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
        
        if prev_rsi <= self.oversold and rsi > self.oversold:
            return Signal(
                stock_code="",
                signal_type=SignalType.BUY,
                price=current["close"],
                timestamp=timestamp,
                confidence=self._calculate_confidence(df, i, SignalType.BUY),
                reason=f"RSI crossed above oversold level ({self.oversold})",
                indicators={
                    "rsi": rsi,
                    "prev_rsi": prev_rsi,
                }
            )
        
        if prev_rsi >= self.overbought and rsi < self.overbought:
            return Signal(
                stock_code="",
                signal_type=SignalType.SELL,
                price=current["close"],
                timestamp=timestamp,
                confidence=self._calculate_confidence(df, i, SignalType.SELL),
                reason=f"RSI crossed below overbought level ({self.overbought})",
                indicators={
                    "rsi": rsi,
                    "prev_rsi": prev_rsi,
                }
            )
        
        return None
    
    def _calculate_confidence(
        self,
        df: pd.DataFrame,
        i: int,
        signal_type: SignalType
    ) -> float:
        """Calculate signal confidence"""
        current = df.iloc[i]
        rsi = current["rsi"]
        confidence = 0.5
        
        if signal_type == SignalType.BUY:
            if rsi < 20:
                confidence += 0.2
            elif rsi < 25:
                confidence += 0.1
            
            if i >= 5:
                prices = df.iloc[i-5:i+1]["close"].values
                rsi_values = df.iloc[i-5:i+1]["rsi"].values
                
                if len(prices) == 6:
                    if prices[-1] < prices[0] and rsi_values[-1] > rsi_values[0]:
                        confidence += 0.15
        
        elif signal_type == SignalType.SELL:
            if rsi > 80:
                confidence += 0.2
            elif rsi > 75:
                confidence += 0.1
            
            if i >= 5:
                prices = df.iloc[i-5:i+1]["close"].values
                rsi_values = df.iloc[i-5:i+1]["rsi"].values
                
                if len(prices) == 6:
                    if prices[-1] > prices[0] and rsi_values[-1] < rsi_values[0]:
                        confidence += 0.15
        
        return min(max(confidence, 0.0), 1.0)
