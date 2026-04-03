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


class BottomVolumeSurge(BuyStrategy):
    """
    Strategy 4: Bottom Volume Surge (底部放量)

    Conditions:
    - Price declined >15% from 20-day high (sustained decline)
    - MA5 < MA10 < MA20 (bearish alignment)
    - Current volume > 5-day average * 2 (volume spike)
    - Volume spike follows a period of shrinkage
    - Bullish candle (close > open) with price holding above recent low
    """

    name = "bottom_volume_surge"

    def __init__(
        self,
        decline_threshold: float = 0.15,
        volume_multiplier: float = 2.0,
        volume_avg_days: int = 5,
        high_lookback: int = 20,
        shrinkage_threshold: float = 0.7,
        shrinkage_days: int = 2,
    ):
        self.decline_threshold = decline_threshold
        self.volume_multiplier = volume_multiplier
        self.volume_avg_days = volume_avg_days
        self.high_lookback = high_lookback
        self.shrinkage_threshold = shrinkage_threshold
        self.shrinkage_days = shrinkage_days

    def check(self, stock_code: str, data: pd.DataFrame, **kwargs) -> Optional[BuySignal]:
        if data.empty or len(data) < self.high_lookback + 5:
            return None

        close = data["close"].values
        open_ = data["open"].values
        low = data["low"].values
        high = data["high"].values
        volume = data["volume"].values

        current_close = close[-1]
        current_open = open_[-1]
        current_low = low[-1]
        current_volume = volume[-1]

        # Condition 1: Sustained decline - price dropped >15% from 20-day high
        high_20d = np.max(high[-(self.high_lookback + 1):-1])
        recent_low = np.min(low[-self.high_lookback:])
        decline_pct = (high_20d - recent_low) / high_20d

        if decline_pct < self.decline_threshold:
            return None

        # Condition 1b: Bearish MA alignment (MA5 < MA10 < MA20)
        if "MA5" in data.columns and "MA10" in data.columns and "MA20" in data.columns:
            ma5 = data["MA5"].iloc[-1]
            ma10 = data["MA10"].iloc[-1]
            ma20 = data["MA20"].iloc[-1]
            if pd.isna(ma5) or pd.isna(ma10) or pd.isna(ma20):
                return None
            if not (ma5 < ma10 < ma20):
                return None
        else:
            # Fallback: compute from close prices
            if len(close) < 20:
                return None
            ma5 = np.mean(close[-5:])
            ma10 = np.mean(close[-10:])
            ma20 = np.mean(close[-20:])
            if not (ma5 < ma10 < ma20):
                return None

        # Condition 2: Volume spike - current volume > 5-day average * 3
        avg_vol_5 = np.mean(volume[-(self.volume_avg_days + 1):-1])
        if avg_vol_5 <= 0:
            return None
        vol_ratio = current_volume / avg_vol_5
        if vol_ratio < self.volume_multiplier:
            return None

        # Condition 2b: Prior shrinkage - at least N consecutive days with volume < 50% of 20-day avg
        avg_vol_20 = np.mean(volume[-(self.high_lookback + 1):-1])
        if avg_vol_20 <= 0:
            return None
        shrinkage_count = 0
        has_shrinkage = False
        for i in range(-2, -(self.high_lookback + 1), -1):
            if volume[i] < avg_vol_20 * self.shrinkage_threshold:
                shrinkage_count += 1
                if shrinkage_count >= self.shrinkage_days:
                    has_shrinkage = True
                    break
            else:
                shrinkage_count = 0

        if not has_shrinkage:
            return None

        # Condition 3: Price stabilization - bullish candle
        if current_close <= current_open:
            return None

        # Price holds above recent low
        if current_close < recent_low:
            return None

        # Calculate confidence
        confidence = 0.0
        # Decline depth contribution (max 0.4)
        confidence += min(decline_pct / 0.30, 0.4)
        # Volume spike strength (max 0.3)
        confidence += min((vol_ratio / self.volume_multiplier - 1.0) * 0.15 + 0.15, 0.3)
        # Lower shadow bonus (max 0.15)
        body = abs(current_close - current_open)
        lower_shadow = min(current_open, current_close) - current_low
        has_lower_shadow = lower_shadow > body if body > 0 else False
        if has_lower_shadow:
            confidence += 0.15
        # MACD turning positive bonus (max 0.15)
        if "MACD_BAR" in data.columns and len(data) >= 2:
            macd_bar_curr = data["MACD_BAR"].iloc[-1]
            macd_bar_prev = data["MACD_BAR"].iloc[-2]
            if not pd.isna(macd_bar_curr) and not pd.isna(macd_bar_prev):
                if macd_bar_curr > macd_bar_prev:
                    confidence += 0.15

        confidence = min(confidence, 1.0)

        stop_loss_price = recent_low * 0.98

        return BuySignal(
            strategy_name=self.name,
            stock_code=stock_code,
            signal_type="bottom_volume",
            price=float(current_close),
            confidence=confidence,
            reason=f"底部放量: 跌幅{decline_pct*100:.1f}%, 量比{vol_ratio:.1f}x, MA空头排列",
            timestamp=datetime.now(),
            details={
                "decline_pct": round(decline_pct * 100, 2),
                "volume_ratio": round(vol_ratio, 2),
                "recent_low": round(float(recent_low), 2),
                "stop_loss_price": round(float(stop_loss_price), 2),
                "position_size_hint": 0.25,
                "ma_bear_aligned": True,
                "has_lower_shadow": has_lower_shadow,
            }
        )


class ChanTheoryBuy(BuyStrategy):
    """
    Strategy 5: Chan Theory Buy (缠论买点)

    Detects chan theory buy points:
    - First buy (一买): Bottom divergence at end of downtrend after hub
    - Second buy (二买): Pullback after up-break doesn't re-enter hub
    - Third buy (三买): Pullback stays above hub ZG
    """

    name = "chan_theory_buy"

    def __init__(self, min_stroke_bars: int = 4, lookback_days: int = 120):
        from src.trading.signals.chan_theory import ChanTheoryAnalyzer
        self.analyzer = ChanTheoryAnalyzer(min_stroke_bars=min_stroke_bars)
        self.lookback_days = lookback_days

    def check(self, stock_code: str, data: pd.DataFrame, **kwargs) -> Optional[BuySignal]:
        if data.empty or len(data) < 60:
            return None

        result = self.analyzer.analyze(data)

        if not result.buy_points:
            return None

        # Take the most recent buy point
        latest_bp = result.buy_points[-1]
        bp_bar_index = latest_bp["bar_index"]

        # Only trigger if buy point is near the end (within 3 bars)
        if bp_bar_index < len(data) - 3:
            return None

        type_config = {
            "first_buy":  {"confidence": 0.90, "position": 0.40, "label": "一买"},
            "second_buy": {"confidence": 0.75, "position": 0.30, "label": "二买"},
            "third_buy":  {"confidence": 0.70, "position": 0.25, "label": "三买"},
        }
        bp_type = latest_bp["type"]
        config = type_config.get(bp_type, {"confidence": 0.6, "position": 0.20, "label": bp_type})

        current_close = float(data["close"].iloc[-1])
        stop_loss = latest_bp.get("fractal_low", current_close * 0.95) * 0.98

        return BuySignal(
            strategy_name=self.name,
            stock_code=stock_code,
            signal_type=f"chan_{bp_type}",
            price=current_close,
            confidence=config["confidence"],
            reason=f"缠论{config['label']}: {latest_bp.get('reason', '')}",
            timestamp=datetime.now(),
            details={
                "buy_point_type": bp_type,
                "hub_ZG": latest_bp.get("hub_ZG"),
                "hub_ZD": latest_bp.get("hub_ZD"),
                "macd_divergence": latest_bp.get("divergence", False),
                "stop_loss_price": round(float(stop_loss), 2),
                "position_size_hint": config["position"],
                "num_hubs": latest_bp.get("num_hubs", 0),
                "num_strokes": len(result.strokes),
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
