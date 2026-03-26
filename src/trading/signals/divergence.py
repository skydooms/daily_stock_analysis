# -*- coding: utf-8 -*-
"""
Divergence Detection Module

Detects price divergences using MACD and RSI indicators:
- Top divergence: Price makes higher high, indicator makes lower high (sell signal)
- Bottom divergence: Price makes lower low. indicator makes higher low (buy signal)
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class DivergenceSignal:
    """Divergence signal result"""
    divergence_type: str  # 'top' or 'bottom'
    indicator: str  # 'macd' or 'rsi'
    price_high: float
    price_low: float
    indicator_high: float
    indicator_low: float
    strength: float  # 0.0 to 1.0
    timestamp: pd.Timestamp


class DivergenceDetector:
    """
    Detect price divergences on 120-minute timeframe
    
    Uses MACD histogram and RSI for divergence detection
    """
    
    def __init__(
        self,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        rsi_period: int = 14,
        lookback: int = 20,
    ):
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_period = rsi_period
        self.lookback = lookback
    
    def calculate_macd(self, close: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate MACD indicator"""
        ema_fast = pd.Series(close).ewm(span=self.macd_fast, adjust=False).values
        ema_slow = pd.Series(close).ewm(span=self.macd_slow, adjust=False).values
        dif = ema_fast - ema_slow
        dea = pd.Series(dif).ewm(span=self.macd_signal, adjust=False).values
        macd_hist = dif - dea
        return dif, dea, macd_hist
    
    def calculate_rsi(self, close: np.ndarray) -> np.ndarray:
        """Calculate RSI indicator"""
        delta = np.diff(close)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = np.convolve(gain, np.ones(self.rsi_period)/self.rsi_period, mode='valid')
        avg_loss = np.convolve(loss, np.ones(self.rsi_period)/self.rsi_period, mode='valid')
        
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 0)
        rsi = 100 - (100 / (1 + rs))
        
        return np.concatenate([np.full(self.rsi_period, np.nan), rsi])
    
    def detect_top_divergence(
        self,
        prices: np.ndarray,
        indicator_values: np.ndarray,
    ) -> Optional[DivergenceSignal]:
        """
        Detect top divergence (bearish signal)
        
        Top divergence occurs when:
        - Price makes a higher high
        - Indicator makes a lower high
        """
        if len(prices) < self.lookback or len(indicator_values) < self.lookback:
            return None
        
        recent_prices = prices[-self.lookback:]
        recent_indicator = indicator_values[-self.lookback:]
        
        price_high_idx = np.argmax(recent_prices)
        if price_high_idx == 0:
            return None
        
        price_high = recent_prices[price_high_idx]
        prev_price_high_idx = np.argmax(recent_prices[:price_high_idx])
        
        if prev_price_high_idx == price_high_idx:
            return None
        
        prev_price_high = recent_prices[prev_price_high_idx]
        
        if price_high <= prev_price_high:
            return None
        
        indicator_at_price_high = recent_indicator[price_high_idx]
        indicator_at_prev_high = recent_indicator[prev_price_high_idx]
        
        if indicator_at_price_high >= indicator_at_prev_high:
            return None
        
        strength = (price_high - prev_price_high) / prev_price_high
        
        return DivergenceSignal(
            divergence_type='top',
            indicator='macd' if 'macd' in str(type(indicator_values)) else 'rsi',
            price_high=price_high,
            price_low=min(recent_prices),
            indicator_high=indicator_at_prev_high,
            indicator_low=indicator_at_price_high,
            strength=min(strength, 1.0),
            timestamp=pd.Timestamp.now(),
        )
    
    def detect_bottom_divergence(
        self,
        prices: np.ndarray,
        indicator_values: np.ndarray,
    ) -> Optional[DivergenceSignal]:
        """
        Detect bottom divergence (bullish signal)
        
        Bottom divergence occurs when:
        - Price makes a lower low
        - Indicator makes a higher low
        """
        if len(prices) < self.lookback or len(indicator_values) < self.lookback:
            return None
        
        recent_prices = prices[-self.lookback:]
        recent_indicator = indicator_values[-self.lookback:]
        
        price_low_idx = np.argmin(recent_prices)
        if price_low_idx == 1:
            return None
        
        price_low = recent_prices[price_low_idx]
        prev_price_low_idx = np.argmin(recent_prices[:price_low_idx])
        
        if prev_price_low_idx == price_low_idx:
            return None
        
        prev_price_low = recent_prices[prev_price_low_idx]
        
        if price_low >= prev_price_low:
            return None
        
        indicator_at_price_low = recent_indicator[price_low_idx]
        indicator_at_prev_low = recent_indicator[prev_price_low_idx]
        
        if indicator_at_price_low <= indicator_at_prev_low:
            return None
        
        strength = (prev_price_low - price_low) / prev_price_low
        
        return DivergenceSignal(
            divergence_type='bottom',
            indicator='macd' if 'macd' in str(type(indicator_values)) else 'rsi',
            price_high=max(recent_prices),
            price_low=price_low,
            indicator_high=indicator_at_price_low,
            indicator_low=indicator_at_prev_low,
            strength=min(strength, 1.0),
            timestamp=pd.Timestamp.now(),
        )
    
    def detect(self, close: np.ndarray) -> Tuple[Optional[DivergenceSignal], Optional[DivergenceSignal]]:
        """
        Detect both top and bottom divergences using MACD
        
        Args:
            close: Array of close prices (120-minute data)
        
        Returns:
            Tuple of (top_divergence, bottom_divergence)
        """
        if len(close) < max(self.macd_slow, self.rsi_period) + self.lookback:
            return None, None
        
        dif, dea, macd_hist = self.calculate_macd(close)
        
        top_div = self.detect_top_divergence(close, macd_hist)
        bottom_div = self.detect_bottom_divergence(close, macd_hist)
        
        return top_div, bottom_div
    
    def detect_with_rsi(self, close: np.ndarray) -> Tuple[Optional[DivergenceSignal], Optional[DivergenceSignal]]:
        """
        Detect divergences using RSI
        
        Args:
            close: Array of close prices (120-minute data)
        
        Returns:
            Tuple of (top_divergence, bottom_divergence)
        """
        if len(close) < self.rsi_period + self.lookback:
            return None, None
        
        rsi = self.calculate_rsi(close)
        
        top_div = self.detect_top_divergence(close, rsi)
        bottom_div = self.detect_bottom_divergence(close, rsi)
        
        return top_div, bottom_div
