# -*- coding: utf-8 -*-
"""
Sell Strategies Module

Sell strategies for position stocks:
1. DivergenceTop: 120-minute top divergence (reduce position)
2. DailySurge: Single-day price surge >10% (reduce position)
3. PriceLevelReduce: Price above threshold (reduce 20%)
4. MonthlySurge: Monthly gain >40% (close position)
5. DivergenceBottomAdd: 120-minute bottom divergence (add position)
6. DailyDrop: Single-day price drop >10% (add position)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List
import numpy as np
import pandas as pd
import logging

from src.trading.signals.divergence import DivergenceDetector, DivergenceSignal
from src.trading.price_tracker import PriceTracker

logger = logging.getLogger(__name__)


@dataclass
class SellSignal:
    """Sell signal result"""
    strategy_name: str
    stock_code: str
    signal_type: str  # 'reduce', 'close', 'add'
    action: str  # 'sell', 'buy'
    price: float
    shares_pct: float  # percentage of position to trade
    confidence: float
    reason: str
    timestamp: datetime
    details: dict = None


class SellStrategy(ABC):
    """Base class for sell strategies"""
    
    name: str = "base"
    action: str = "sell"
    
    @abstractmethod
    def check(self, stock_code: str, data: pd.DataFrame, position: dict, **kwargs) -> Optional[SellSignal]:
        """Check if sell signal is triggered"""
        pass


class DivergenceTop(SellStrategy):
    """
    Reduce Strategy 1: 120-Minute Top Divergence
    
    Conditions:
    - Price makes higher high
    - MACD histogram makes lower high
    - Action: Reduce position
    """
    
    name = "divergence_top"
    action = "sell"
    
    def __init__(self, reduce_pct: float = 0.20, lookback: int = 20):
        self.reduce_pct = reduce_pct
        self.lookback = lookback
        self.detector = DivergenceDetector(lookback=lookback)
    
    def check(
        self,
        stock_code: str,
        data: pd.DataFrame,
        position: dict,
        minute_data: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> Optional[SellSignal]:
        """Check for top divergence signal"""
        check_data = minute_data if minute_data is not None and not minute_data.empty else data
        
        if check_data.empty or len(check_data) < self.lookback + 26:
            return None
        
        close = check_data["close"].values
        top_div, _ = self.detector.detect(close)
        
        if not top_div:
            return None
        
        return SellSignal(
            strategy_name=self.name,
            stock_code=stock_code,
            signal_type="reduce",
            action="sell",
            price=float(close[-1]),
            shares_pct=self.reduce_pct,
            confidence=top_div.strength,
            reason=f"120-min top divergence detected, reduce {self.reduce_pct*100:.0f}% position",
            timestamp=datetime.now(),
            details={
                "divergence_type": top_div.divergence_type,
                "price_high": top_div.price_high,
                "price_low": top_div.price_low,
            }
        )


class DailySurge(SellStrategy):
    """
    Reduce Strategy 2: Single-Day Price Surge
    
    Conditions:
    - Single-day price increase > threshold (default 10%)
    - Action: Reduce position
    """
    
    name = "daily_surge"
    action = "sell"
    
    def __init__(self, surge_threshold: float = 0.10, reduce_pct: float = 0.20):
        self.surge_threshold = surge_threshold
        self.reduce_pct = reduce_pct
    
    def check(
        self,
        stock_code: str,
        data: pd.DataFrame,
        position: dict,
        **kwargs
    ) -> Optional[SellSignal]:
        """Check for daily surge signal"""
        if data.empty or len(data) < 2:
            return None
        
        current_close = float(data["close"].iloc[-1])
        prev_close = float(data["close"].iloc[-2])
        
        price_change = (current_close - prev_close) / prev_close
        
        if price_change <= self.surge_threshold:
            return None
        
        return SellSignal(
            strategy_name=self.name,
            stock_code=stock_code,
            signal_type="reduce",
            action="sell",
            price=current_close,
            shares_pct=self.reduce_pct,
            confidence=min(price_change / self.surge_threshold, 1.0),
            reason=f"Single-day surge {price_change*100:.1f}% > {self.surge_threshold*100:.0f}%, reduce {self.reduce_pct*100:.0f}% position",
            timestamp=datetime.now(),
            details={
                "price_change_pct": price_change * 100,
                "surge_threshold": self.surge_threshold * 100,
            }
        )


class PriceLevelReduce(SellStrategy):
    """
    Reduce Strategy 3 & 4: Price Level Threshold
    
    Conditions:
    - Price > open_min * 1.22 -> reduce 20%
    - Price > price_min * 1.35 -> reduce 20%
    """
    
    name = "price_level_reduce"
    action = "sell"
    
    def __init__(
        self,
        open_min_multiplier: float = 1.22,
        price_min_multiplier: float = 1.35,
        reduce_pct: float = 0.20,
        period_days: int = 90,
    ):
        self.open_min_multiplier = open_min_multiplier
        self.price_min_multiplier = price_min_multiplier
        self.reduce_pct = reduce_pct
        self.price_tracker = PriceTracker(period_days=period_days)
    
    def check(
        self,
        stock_code: str,
        data: pd.DataFrame,
        position: dict,
        **kwargs
    ) -> Optional[SellSignal]:
        """Check for price level reduce signal"""
        if data.empty:
            return None
        
        stats = self.price_tracker.update(stock_code, data)
        current_price = float(data["close"].iloc[-1])
        
        if stats.price_min > 0 and current_price > stats.price_min * self.price_min_multiplier:
            return SellSignal(
                strategy_name=self.name,
                stock_code=stock_code,
                signal_type="reduce",
                action="sell",
                price=current_price,
                shares_pct=self.reduce_pct,
                confidence=0.8,
                reason=f"Price {current_price:.2f} > price_min({stats.price_min:.2f}) * {self.price_min_multiplier}",
                timestamp=datetime.now(),
                details={
                    "threshold_type": "price_min",
                    "price_min": stats.price_min,
                    "multiplier": self.price_min_multiplier,
                }
            )
        
        if stats.open_min > 0 and current_price > stats.open_min * self.open_min_multiplier:
            return SellSignal(
                strategy_name=self.name,
                stock_code=stock_code,
                signal_type="reduce",
                action="sell",
                price=current_price,
                shares_pct=self.reduce_pct,
                confidence=0.7,
                reason=f"Price {current_price:.2f} > open_min({stats.open_min:.2f}) * {self.open_min_multiplier}",
                timestamp=datetime.now(),
                details={
                    "threshold_type": "open_min",
                    "open_min": stats.open_min,
                    "multiplier": self.open_min_multiplier,
                }
            )
        
        return None


class MonthlySurge(SellStrategy):
    """
    Reduce Strategy 5: Monthly Surge Close Position
    
    Conditions:
    - Monthly gain > threshold (default 40%)
    - Action: Close entire position
    """
    
    name = "monthly_surge"
    action = "sell"
    
    def __init__(self, surge_threshold: float = 0.40):
        self.surge_threshold = surge_threshold
    
    def check(
        self,
        stock_code: str,
        data: pd.DataFrame,
        position: dict,
        **kwargs
    ) -> Optional[SellSignal]:
        """Check for monthly surge signal"""
        if data.empty:
            return None
        
        month_ago = datetime.now() - timedelta(days=30)
        
        if "date" in data.columns:
            data = data.copy()
            data["date"] = pd.to_datetime(data["date"])
            month_data = data[data["date"] >= month_ago]
        else:
            month_data = data.tail(22)
        
        if month_data.empty or len(month_data) < 2:
            return None
        
        start_price = float(month_data["close"].iloc[0])
        current_price = float(month_data["close"].iloc[-1])
        
        monthly_change = (current_price - start_price) / start_price
        
        if monthly_change <= self.surge_threshold:
            return None
        
        return SellSignal(
            strategy_name=self.name,
            stock_code=stock_code,
            signal_type="close",
            action="sell",
            price=current_price,
            shares_pct=1.0,
            confidence=min(monthly_change / self.surge_threshold, 1.0),
            reason=f"Monthly surge {monthly_change*100:.1f}% > {self.surge_threshold*100:.0f}%, close position",
            timestamp=datetime.now(),
            details={
                "monthly_change_pct": monthly_change * 100,
                "start_price": start_price,
                "current_price": current_price,
            }
        )


class DivergenceBottomAdd(SellStrategy):
    """
    Add Strategy 1: 120-Minute Bottom Divergence
    
    Conditions:
    - Price makes lower low
    - MACD histogram makes higher low
    - Action: Add position
    """
    
    name = "divergence_bottom_add"
    action = "buy"
    
    def __init__(self, add_pct: float = 0.20, lookback: int = 20):
        self.add_pct = add_pct
        self.lookback = lookback
        self.detector = DivergenceDetector(lookback=lookback)
    
    def check(
        self,
        stock_code: str,
        data: pd.DataFrame,
        position: dict,
        minute_data: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> Optional[SellSignal]:
        """Check for bottom divergence add signal"""
        check_data = minute_data if minute_data is not None and not minute_data.empty else data
        
        if check_data.empty or len(check_data) < self.lookback + 26:
            return None
        
        close = check_data["close"].values
        _, bottom_div = self.detector.detect(close)
        
        if not bottom_div:
            return None
        
        return SellSignal(
            strategy_name=self.name,
            stock_code=stock_code,
            signal_type="add",
            action="buy",
            price=float(close[-1]),
            shares_pct=self.add_pct,
            confidence=bottom_div.strength,
            reason=f"120-min bottom divergence detected, add {self.add_pct*100:.0f}% position",
            timestamp=datetime.now(),
            details={
                "divergence_type": bottom_div.divergence_type,
                "price_low": bottom_div.price_low,
                "price_high": bottom_div.price_high,
            }
        )


class DailyDrop(SellStrategy):
    """
    Add Strategy 2: Single-Day Price Drop
    
    Conditions:
    - Single-day price drop > threshold (default 10%)
    - Action: Add position
    """
    
    name = "daily_drop"
    action = "buy"
    
    def __init__(self, drop_threshold: float = 0.10, add_pct: float = 0.20):
        self.drop_threshold = drop_threshold
        self.add_pct = add_pct
    
    def check(
        self,
        stock_code: str,
        data: pd.DataFrame,
        position: dict,
        **kwargs
    ) -> Optional[SellSignal]:
        """Check for daily drop add signal"""
        if data.empty or len(data) < 2:
            return None
        
        current_close = float(data["close"].iloc[-1])
        prev_close = float(data["close"].iloc[-2])
        
        price_change = (current_close - prev_close) / prev_close
        
        if price_change >= -self.drop_threshold:
            return None
        
        return SellSignal(
            strategy_name=self.name,
            stock_code=stock_code,
            signal_type="add",
            action="buy",
            price=current_close,
            shares_pct=self.add_pct,
            confidence=min(abs(price_change) / self.drop_threshold, 1.0),
            reason=f"Single-day drop {abs(price_change)*100:.1f}% > {self.drop_threshold*100:.0f}%, add {self.add_pct*100:.0f}% position",
            timestamp=datetime.now(),
            details={
                "price_change_pct": price_change * 100,
                "drop_threshold": self.drop_threshold * 100,
            }
        )


class SellStrategyManager:
    """Manager for multiple sell strategies"""
    
    def __init__(self, strategies: Optional[List[SellStrategy]] = None):
        self.strategies = strategies or [
            DivergenceTop(),
            DailySurge(),
            PriceLevelReduce(),
            MonthlySurge(),
            DivergenceBottomAdd(),
            DailyDrop(),
        ]
    
    def add_strategy(self, strategy: SellStrategy) -> None:
        """Add a sell strategy"""
        self.strategies.append(strategy)
    
    def check_all(
        self,
        stock_code: str,
        data: pd.DataFrame,
        position: dict,
        minute_data: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> List[SellSignal]:
        """
        Check all sell strategies
        
        Args:
            stock_code: Stock code
            data: Daily data DataFrame
            position: Current position info
            minute_data: Optional 120-minute data DataFrame
        
        Returns:
            List of triggered sell signals
        """
        signals = []
        
        for strategy in self.strategies:
            try:
                if isinstance(strategy, (DivergenceTop, DivergenceBottomAdd)) and minute_data is not None:
                    signal = strategy.check(stock_code, data, position, minute_data=minute_data, **kwargs)
                else:
                    signal = strategy.check(stock_code, data, position, **kwargs)
                
                if signal:
                    signals.append(signal)
                    logger.info(f"Sell signal triggered: {strategy.name} for {stock_code}")
            except Exception as e:
                logger.error(f"Error checking strategy {strategy.name}: {e}")
        
        return signals
    
    def get_reduce_signals(self, signals: List[SellSignal]) -> List[SellSignal]:
        """Get reduce position signals"""
        return [s for s in signals if s.signal_type == "reduce"]
    
    def get_close_signals(self, signals: List[SellSignal]) -> List[SellSignal]:
        """Get close position signals"""
        return [s for s in signals if s.signal_type == "close"]
    
    def get_add_signals(self, signals: List[SellSignal]) -> List[SellSignal]:
        """Get add position signals"""
        return [s for s in signals if s.signal_type == "add"]
