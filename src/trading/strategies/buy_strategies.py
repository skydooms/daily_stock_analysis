# -*- coding: utf-8 -*-
"""
Buy Strategies Module

Buy strategies for watchlist stocks:
1. VolumePriceBreakout: 3-day volume-price surge, price up >10%, turnover >1.5x avg
2. DivergenceBottom: 120-minute bottom divergence
3. DeepPullback: Price dropped >35% from 3-month high
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Any
import numpy as np
import pandas as pd
import logging

from src.trading.signals.divergence import DivergenceDetector, DivergenceSignal
from src.trading.signals.volume_price import VolumePriceAnalyzer, VolumePriceSignal
from src.trading.price_tracker import PriceTracker

logger = logging.getLogger(__name__)


@dataclass
class BuySignal:
    """Buy signal result"""
    strategy_name: str
    stock_code: str
    signal_type: str
    price: float
    confidence: float
    reason: str
    timestamp: datetime
    details: dict = None


class BuyStrategy(ABC):
    """Base class for buy strategies"""
    
    name: str = "base"
    
    @abstractmethod
    def check(self, stock_code: str, data: pd.DataFrame, **kwargs) -> Optional[BuySignal]:
        """Check if buy signal is triggered"""
        pass


class VolumePriceBreakout(BuyStrategy):
    """
    Strategy 1: Volume-Price Breakout
    
    Conditions:
    - 3-day consecutive price rise
    - 3-day price change > 10%
    - Single-day turnover > 1.5x average of previous 3 days
    """
    
    name = "volume_price_breakout"
    
    def __init__(
        self,
        surge_days: int = 3,
        surge_threshold: float = 0.10,
        turnover_multiplier: float = 1.5,
    ):
        self.surge_days = surge_days
        self.surge_threshold = surge_threshold
        self.turnover_multiplier = turnover_multiplier
        self.analyzer = VolumePriceAnalyzer(
            surge_days=surge_days,
            surge_threshold=surge_threshold,
            turnover_multiplier=turnover_multiplier,
        )
    
    def check(
        self,
        stock_code: str,
        data: pd.DataFrame,
        turnover: Optional[np.ndarray] = None,
        **kwargs
    ) -> Optional[BuySignal]:
        """
        Check for volume-price breakout signal
        
        Args:
            stock_code: Stock code
            data: DataFrame with columns: date, open, high, low, close, volume
            turnover: Optional turnover rate array
        
        Returns:
            BuySignal if triggered, None otherwise
        """
        if data.empty or len(data) < self.surge_days + 3:
            return None
        
        close = data["close"].values
        volume = data["volume"].values
        
        signal = self.analyzer.detect_volume_price_surge(close, volume, turnover)
        
        if not signal:
            return None
        
        return BuySignal(
            strategy_name=self.name,
            stock_code=stock_code,
            signal_type="surge",
            price=float(close[-1]),
            confidence=signal.strength,
            reason=f"3-day surge: {signal.price_change_pct:.1f}%, volume ratio: {signal.volume_ratio:.2f}x",
            timestamp=datetime.now(),
            details={
                "price_change_pct": signal.price_change_pct,
                "volume_ratio": signal.volume_ratio,
                "turnover_ratio": signal.turnover_ratio,
                "days": signal.days,
            }
        )


class DivergenceBottom(BuyStrategy):
    """
    Strategy 2: 120-Minute Bottom Divergence
    
    Conditions:
    - Price makes lower low
    - MACD histogram makes higher low
    - Bullish reversal signal
    """
    
    name = "divergence_bottom"
    
    def __init__(
        self,
        timeframe_minutes: int = 120,
        lookback: int = 20,
    ):
        self.timeframe_minutes = timeframe_minutes
        self.lookback = lookback
        self.detector = DivergenceDetector(lookback=lookback)
    
    def check(
        self,
        stock_code: str,
        data: pd.DataFrame,
        **kwargs
    ) -> Optional[BuySignal]:
        """
        Check for bottom divergence signal
        
        Args:
            stock_code: Stock code
            data: DataFrame with 120-minute data: date, open, high, low, close, volume
        
        Returns:
            BuySignal if triggered, None otherwise
        """
        if data.empty or len(data) < self.lookback + 26:
            return None
        
        close = data["close"].values
        
        top_div, bottom_div = self.detector.detect(close)
        
        if not bottom_div:
            return None
        
        return BuySignal(
            strategy_name=self.name,
            stock_code=stock_code,
            signal_type="divergence_bottom",
            price=float(close[-1]),
            confidence=bottom_div.strength,
            reason=f"120-min bottom divergence detected, price low: {bottom_div.price_low:.2f}",
            timestamp=datetime.now(),
            details={
                "divergence_type": bottom_div.divergence_type,
                "indicator": bottom_div.indicator,
                "price_low": bottom_div.price_low,
                "price_high": bottom_div.price_high,
            }
        )


class DeepPullback(BuyStrategy):
    """
    Strategy 3: Deep Pullback from 3-Month High
    
    Conditions:
    - Price dropped > 35% from 3-month close_max
    - Potential oversold opportunity
    """
    
    name = "deep_pullback"
    
    def __init__(
        self,
        pullback_threshold: float = 0.35,
        period_days: int = 90,
    ):
        self.pullback_threshold = pullback_threshold
        self.period_days = period_days
        self.price_tracker = PriceTracker(period_days=period_days)
    
    def check(
        self,
        stock_code: str,
        data: pd.DataFrame,
        **kwargs
    ) -> Optional[BuySignal]:
        """
        Check for deep pullback signal
        
        Args:
            stock_code: Stock code
            data: DataFrame with columns: date, open, high, low, close, volume
        
        Returns:
            BuySignal if triggered, None otherwise
        """
        if data.empty:
            return None
        
        stats = self.price_tracker.update(stock_code, data)
        
        current_price = float(data["close"].iloc[-1])
        pullback_pct = self.price_tracker.calculate_pullback_pct(stock_code, current_price)
        
        if pullback_pct >= -self.pullback_threshold:
            return None
        
        return BuySignal(
            strategy_name=self.name,
            stock_code=stock_code,
            signal_type="deep_pullback",
            price=current_price,
            confidence=min(abs(pullback_pct) / self.pullback_threshold, 1.0),
            reason=f"Price dropped {abs(pullback_pct)*100:.1f}% from 3-month high ({stats.close_max:.2f})",
            timestamp=datetime.now(),
            details={
                "pullback_pct": pullback_pct,
                "close_max": stats.close_max,
                "price_min": stats.price_min,
                "price_max": stats.price_max,
            }
        )


class BuyStrategyManager:
    """Manager for multiple buy strategies"""
    
    def __init__(self, strategies: Optional[List[BuyStrategy]] = None):
        self.strategies = strategies or [
            VolumePriceBreakout(),
            DivergenceBottom(),
            DeepPullback(),
        ]
    
    def add_strategy(self, strategy: BuyStrategy) -> None:
        """Add a buy strategy"""
        self.strategies.append(strategy)
    
    def check_all(
        self,
        stock_code: str,
        data: pd.DataFrame,
        minute_data: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> List[BuySignal]:
        """
        Check all buy strategies
        
        Args:
            stock_code: Stock code
            data: Daily data DataFrame
            minute_data: Optional 120-minute data DataFrame
            **kwargs: Additional parameters
        
        Returns:
            List of triggered buy signals
        """
        signals = []
        
        for strategy in self.strategies:
            try:
                if isinstance(strategy, DivergenceBottom) and minute_data is not None:
                    signal = strategy.check(stock_code, minute_data, **kwargs)
                else:
                    signal = strategy.check(stock_code, data, **kwargs)
                
                if signal:
                    signals.append(signal)
                    logger.info(f"Buy signal triggered: {strategy.name} for {stock_code}")
            except Exception as e:
                logger.error(f"Error checking strategy {strategy.name}: {e}")
        
        return signals
    
    def get_best_signal(self, signals: List[BuySignal]) -> Optional[BuySignal]:
        """Get the signal with highest confidence"""
        if not signals:
            return None
        return max(signals, key=lambda s: s.confidence)
