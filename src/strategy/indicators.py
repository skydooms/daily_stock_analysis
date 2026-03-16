# -*- coding: utf-8 -*-
"""
Technical Indicators Module

This module provides technical indicator calculations for stock analysis.
Includes: MA, EMA, MACD, RSI, KDJ, Bollinger Bands, ATR, etc.
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class IndicatorResult:
    """Indicator calculation result"""
    name: str
    values: np.ndarray
    params: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "values": self.values.tolist(),
            "params": self.params,
        }
    
    def latest(self) -> float:
        """Get latest value"""
        if len(self.values) > 0:
            return float(self.values[-1])
        return 0.0


class IndicatorCalculator:
    """
    Technical indicator calculator
    
    Provides methods for calculating various technical indicators.
    """
    
    @staticmethod
    def sma(data: np.ndarray, period: int) -> np.ndarray:
        """
        Simple Moving Average
        
        Args:
            data: Input data array
            period: MA period
            
        Returns:
            SMA values
        """
        if len(data) < period:
            return np.full(len(data), np.nan)
        
        result = np.full(len(data), np.nan)
        for i in range(period - 1, len(data)):
            result[i] = np.mean(data[i - period + 1:i + 1])
        return result
    
    @staticmethod
    def ema(data: np.ndarray, period: int) -> np.ndarray:
        """
        Exponential Moving Average
        
        Args:
            data: Input data array
            period: EMA period
            
        Returns:
            EMA values
        """
        if len(data) == 0:
            return np.array([])
        
        result = np.zeros(len(data))
        multiplier = 2 / (period + 1)
        result[0] = data[0]
        
        for i in range(1, len(data)):
            result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
        
        return result
    
    @staticmethod
    def macd(
        close: np.ndarray,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        MACD (Moving Average Convergence Divergence)
        
        Args:
            close: Close prices
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period
            
        Returns:
            Tuple of (DIF, DEA, MACD histogram)
        """
        fast_ema = IndicatorCalculator.ema(close, fast_period)
        slow_ema = IndicatorCalculator.ema(close, slow_period)
        
        dif = fast_ema - slow_ema
        dea = IndicatorCalculator.ema(dif, signal_period)
        macd = (dif - dea) * 2
        
        return dif, dea, macd
    
    @staticmethod
    def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
        """
        Relative Strength Index
        
        Args:
            close: Close prices
            period: RSI period
            
        Returns:
            RSI values (0-100)
        """
        if len(close) < period + 1:
            return np.full(len(close), np.nan)
        
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.zeros(len(close))
        avg_loss = np.zeros(len(close))
        
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])
        
        for i in range(period + 1, len(close)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period
        
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 0)
        rsi = 100 - (100 / (1 + rs))
        
        rsi[:period] = np.nan
        
        return rsi
    
    @staticmethod
    def kdj(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        KDJ Indicator
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            n: RSV period
            m1: K period
            m2: D period
            
        Returns:
            Tuple of (K, D, J) values
        """
        if len(close) < n:
            return np.full(len(close), np.nan), np.full(len(close), np.nan), np.full(len(close), np.nan)
        
        rsv = np.full(len(close), np.nan)
        for i in range(n - 1, len(close)):
            high_n = high[i - n + 1:i + 1]
            low_n = low[i - n + 1:i + 1]
            highest = np.max(high_n)
            lowest = np.min(low_n)
            if highest != lowest:
                rsv[i] = (close[i] - lowest) / (highest - lowest) * 100
            else:
                rsv[i] = 50
        
        k = np.full(len(close), np.nan)
        d = np.full(len(close), np.nan)
        
        k[n - 1] = 50
        d[n - 1] = 50
        
        for i in range(n, len(close)):
            k[i] = (k[i - 1] * (m1 - 1) + rsv[i]) / m1
            d[i] = (d[i - 1] * (m2 - 1) + k[i]) / m2
        
        j = 3 * k - 2 * d
        
        return k, d, j
    
    @staticmethod
    def bollinger_bands(
        close: np.ndarray,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Bollinger Bands
        
        Args:
            close: Close prices
            period: MA period
            std_dev: Standard deviation multiplier
            
        Returns:
            Tuple of (upper band, middle band, lower band)
        """
        if len(close) < period:
            return np.full(len(close), np.nan), np.full(len(close), np.nan), np.full(len(close), np.nan)
        
        middle = IndicatorCalculator.sma(close, period)
        std = np.full(len(close), np.nan)
        
        for i in range(period - 1, len(close)):
            std[i] = np.std(close[i - period + 1:i + 1])
        
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        
        return upper, middle, lower
    
    @staticmethod
    def atr(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """
        Average True Range
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period
            
        Returns:
            ATR values
        """
        if len(close) < period + 1:
            return np.full(len(close), np.nan)
        
        tr = np.zeros(len(close))
        tr[0] = high[0] - low[0]
        
        for i in range(1, len(close)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1])
            )
        
        atr = np.full(len(close), np.nan)
        atr[period - 1] = np.mean(tr[:period])
        
        for i in range(period, len(close)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        
        return atr
    
    @staticmethod
    def obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """
        On Balance Volume
        
        Args:
            close: Close prices
            volume: Volume data
            
        Returns:
            OBV values
        """
        if len(close) != len(volume):
            return np.full(len(close), np.nan)
        
        obv = np.zeros(len(close))
        obv[0] = volume[0]
        
        for i in range(1, len(close)):
            if close[i] > close[i - 1]:
                obv[i] = obv[i - 1] + volume[i]
            elif close[i] < close[i - 1]:
                obv[i] = obv[i - 1] - volume[i]
            else:
                obv[i] = obv[i - 1]
        
        return obv
    
    @staticmethod
    def volume_ma(volume: np.ndarray, period: int = 5) -> np.ndarray:
        """
        Volume Moving Average
        
        Args:
            volume: Volume data
            period: MA period
            
        Returns:
            Volume MA values
        """
        return IndicatorCalculator.sma(volume, period)
    
    @staticmethod
    def volume_ratio(volume: np.ndarray, period: int = 5) -> np.ndarray:
        """
        Volume Ratio (current volume / average volume)
        
        Args:
            volume: Volume data
            period: Average period
            
        Returns:
            Volume ratio values
        """
        vol_ma = IndicatorCalculator.volume_ma(volume, period)
        return np.where(vol_ma > 0, volume / vol_ma, 0)
    
    @staticmethod
    def williams_r(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """
        Williams %R
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: Lookback period
            
        Returns:
            Williams %R values (-100 to 0)
        """
        if len(close) < period:
            return np.full(len(close), np.nan)
        
        wr = np.full(len(close), np.nan)
        
        for i in range(period - 1, len(close)):
            high_n = np.max(high[i - period + 1:i + 1])
            low_n = np.min(low[i - period + 1:i + 1])
            if high_n != low_n:
                wr[i] = (high_n - close[i]) / (high_n - low_n) * -100
            else:
                wr[i] = -50
        
        return wr
    
    @staticmethod
    def cci(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 20
    ) -> np.ndarray:
        """
        Commodity Channel Index
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: CCI period
            
        Returns:
            CCI values
        """
        if len(close) < period:
            return np.full(len(close), np.nan)
        
        tp = (high + low + close) / 3
        cci = np.full(len(close), np.nan)
        
        for i in range(period - 1, len(close)):
            tp_n = tp[i - period + 1:i + 1]
            ma = np.mean(tp_n)
            md = np.mean(np.abs(tp_n - ma))
            if md != 0:
                cci[i] = (tp[i] - ma) / (0.015 * md)
            else:
                cci[i] = 0
        
        return cci


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators for a DataFrame
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        DataFrame with added indicator columns
    """
    result = df.copy()
    
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    volume = df["volume"].values if "volume" in df.columns else np.zeros(len(df))
    
    result["ma5"] = IndicatorCalculator.sma(close, 5)
    result["ma10"] = IndicatorCalculator.sma(close, 10)
    result["ma20"] = IndicatorCalculator.sma(close, 20)
    result["ma60"] = IndicatorCalculator.sma(close, 60)
    
    result["ema12"] = IndicatorCalculator.ema(close, 12)
    result["ema26"] = IndicatorCalculator.ema(close, 26)
    
    dif, dea, macd = IndicatorCalculator.macd(close)
    result["macd_dif"] = dif
    result["macd_dea"] = dea
    result["macd"] = macd
    
    result["rsi6"] = IndicatorCalculator.rsi(close, 6)
    result["rsi14"] = IndicatorCalculator.rsi(close, 14)
    
    k, d, j = IndicatorCalculator.kdj(high, low, close)
    result["kdj_k"] = k
    result["kdj_d"] = d
    result["kdj_j"] = j
    
    upper, middle, lower = IndicatorCalculator.bollinger_bands(close)
    result["boll_upper"] = upper
    result["boll_middle"] = middle
    result["boll_lower"] = lower
    
    result["atr14"] = IndicatorCalculator.atr(high, low, close, 14)
    
    result["obv"] = IndicatorCalculator.obv(close, volume)
    result["vol_ma5"] = IndicatorCalculator.volume_ma(volume, 5)
    result["vol_ratio"] = IndicatorCalculator.volume_ratio(volume, 5)
    
    result["wr14"] = IndicatorCalculator.williams_r(high, low, close, 14)
    result["cci20"] = IndicatorCalculator.cci(high, low, close, 20)
    
    return result
