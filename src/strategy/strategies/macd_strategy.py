# -*- coding: utf-8 -*-
"""
MACD Strategy

This module implements trading strategies based on MACD indicator.
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
class MACDStrategyConfig(StrategyConfig):
    """MACD Strategy configuration"""
    name: str = "MACDStrategy"
    description: str = "MACD Crossover Strategy"
    strategy_type: StrategyType = StrategyType.TREND_FOLLOWING
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9


class MACDStrategy(BaseStrategy):
    """
    MACD Strategy
    
    Generates buy/sell signals based on MACD crossovers.
    
    Buy signals:
    - DIF crosses above DEA (golden cross)
    - MACD histogram turns positive
    
    Sell signals:
    - DIF crosses below DEA (death cross)
    - MACD histogram turns negative
    """
    
    name = "MACDStrategy"
    description = "MACD Crossover Strategy"
    strategy_type = StrategyType.TREND_FOLLOWING
    
    def __init__(self, config: Optional[MACDStrategyConfig] = None):
        """Initialize MACD Strategy"""
        super().__init__(config or MACDStrategyConfig())
        self.fast_period = self.get_param("fast_period", 12)
        self.slow_period = self.get_param("slow_period", 26)
        self.signal_period = self.get_param("signal_period", 9)
    
    def get_required_indicators(self) -> List[str]:
        """Get required indicators"""
        return ["macd_dif", "macd_dea", "macd"]
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """Generate trading signals"""
        if not self.validate_data(data):
            return []
        
        signals = []
        df = self._calculate_indicators(data)
        
        for i in range(self.slow_period + self.signal_period, len(df)):
            signal = self._check_signal(df, i)
            if signal:
                signals.append(signal)
        
        return signals
    
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD indicators"""
        df = data.copy()
        close = df["close"].values
        
        dif, dea, macd = IndicatorCalculator.macd(
            close,
            self.fast_period,
            self.slow_period,
            self.signal_period
        )
        
        df["macd_dif"] = dif
        df["macd_dea"] = dea
        df["macd"] = macd
        
        return df
    
    def _check_signal(self, df: pd.DataFrame, i: int) -> Optional[Signal]:
        """Check for trading signal"""
        if i < 1:
            return None
        
        current = df.iloc[i]
        previous = df.iloc[i - 1]
        
        dif = current["macd_dif"]
        dea = current["macd_dea"]
        macd = current["macd"]
        
        prev_dif = previous["macd_dif"]
        prev_dea = previous["macd_dea"]
        
        if pd.isna(dif) or pd.isna(dea):
            return None
        
        timestamp = current.get("date", current.name)
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
        
        if prev_dif <= prev_dea and dif > dea:
            return Signal(
                stock_code="",
                signal_type=SignalType.BUY,
                price=current["close"],
                timestamp=timestamp,
                confidence=self._calculate_confidence(df, i, SignalType.BUY),
                reason="MACD golden cross: DIF crossed above DEA",
                indicators={
                    "dif": dif,
                    "dea": dea,
                    "macd": macd,
                }
            )
        
        if prev_dif >= prev_dea and dif < dea:
            return Signal(
                stock_code="",
                signal_type=SignalType.SELL,
                price=current["close"],
                timestamp=timestamp,
                confidence=self._calculate_confidence(df, i, SignalType.SELL),
                reason="MACD death cross: DIF crossed below DEA",
                indicators={
                    "dif": dif,
                    "dea": dea,
                    "macd": macd,
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
        confidence = 0.5
        
        macd = current["macd"]
        if signal_type == SignalType.BUY and macd > 0:
            confidence += 0.15
        elif signal_type == SignalType.SELL and macd < 0:
            confidence += 0.15
        
        if i >= 5:
            macd_values = df.iloc[i-5:i]["macd"].values
            if signal_type == SignalType.BUY:
                increasing = sum(1 for j in range(1, len(macd_values)) if macd_values[j] > macd_values[j-1])
                confidence += (increasing / (len(macd_values) - 1)) * 0.15
            else:
                decreasing = sum(1 for j in range(1, len(macd_values)) if macd_values[j] < macd_values[j-1])
                confidence += (decreasing / (len(macd_values) - 1)) * 0.15
        
        return min(max(confidence, 0.0), 1.0)
