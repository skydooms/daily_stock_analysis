# -*- coding: utf-8 -*-
"""
Volume-Price Analysis Module

Detects volume-price patterns for trading signals:
- Volume-price surge (量价齐涨)
- Turnover rate analysis
"""

from dataclasses import dataclass
from typing import Optional, List
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class VolumePriceSignal:
    """Volume-price signal result"""
    signal_type: str  # 'surge', 'breakout', 'climax'
    days: int
    price_change_pct: float
    volume_ratio: float
    turnover_ratio: float
    strength: float
    timestamp: pd.Timestamp


class VolumePriceAnalyzer:
    """
    Analyze volume-price patterns
    
    Features:
    - Detect 3-day volume-price surge
    - Calculate turnover rate changes
    - Identify volume breakouts
    """
    
    def __init__(
        self,
        surge_days: int = 3,
        surge_threshold: float = 0.10,
        turnover_multiplier: float = 1.5,
    ):
        self.surge_days = surge_days
        self.surge_threshold = surge_threshold
        self.turnover_multiplier = turnover_multiplier
    
    def calculate_turnover_rate(
        self,
        volume: np.ndarray,
        shares_outstanding: float,
    ) -> np.ndarray:
        """
        Calculate turnover rate
        
        Args:
            volume: Trading volume array
            shares_outstanding: Total shares outstanding
        
        Returns:
            Turnover rate array
        """
        return volume / shares_outstanding
    
    def detect_volume_price_surge(
        self,
        close: np.ndarray,
        volume: np.ndarray,
        turnover: Optional[np.ndarray] = None,
    ) -> Optional[VolumePriceSignal]:
        """
        Detect volume-price surge pattern
        
        Conditions:
        1. Price rises for 3 consecutive days
        2. 3-day price change > 10%
        3. Single-day turnover > 1.5x average of previous 3 days
        
        Args:
            close: Close prices array
            volume: Volume array
            turnover: Turnover rate array (optional)
        
        Returns:
            VolumePriceSignal if detected, None otherwise
        """
        if len(close) < self.surge_days + 3:
            return None
        
        recent_close = close[-self.surge_days:]
        recent_volume = volume[-self.surge_days:]
        
        price_changes = np.diff(recent_close) / recent_close[:-1]
        
        if not np.all(price_changes > 0):
            return None
        
        total_change = (recent_close[-1] - recent_close[0]) / recent_close[0]
        
        if total_change <= self.surge_threshold:
            return None
        
        if turnover is not None and len(turnover) >= self.surge_days + 3:
            recent_turnover = turnover[-self.surge_days:]
            prev_turnover = turnover[-(self.surge_days + 3):-self.surge_days]
            avg_prev_turnover = np.mean(prev_turnover)
            
            max_turnover = np.max(recent_turnover)
            
            if max_turnover < avg_prev_turnover * self.turnover_multiplier:
                return None
            
            turnover_ratio = max_turnover / avg_prev_turnover
        else:
            prev_volume = volume[-(self.surge_days + 3):-self.surge_days]
            avg_prev_volume = np.mean(prev_volume)
            max_volume = np.max(recent_volume)
            
            if max_volume < avg_prev_volume * self.turnover_multiplier:
                return None
            
            turnover_ratio = max_volume / avg_prev_volume
        
        volume_ratio = np.mean(recent_volume) / np.mean(volume[-(self.surge_days + 3):-self.surge_days])
        
        strength = min(total_change / self.surge_threshold, 1.0)
        
        return VolumePriceSignal(
            signal_type='surge',
            days=self.surge_days,
            price_change_pct=total_change * 100,
            volume_ratio=volume_ratio,
            turnover_ratio=turnover_ratio,
            strength=strength,
            timestamp=pd.Timestamp.now(),
        )
    
    def detect_volume_breakout(
        self,
        close: np.ndarray,
        volume: np.ndarray,
        lookback: int = 20,
        threshold: float = 2.0,
    ) -> Optional[VolumePriceSignal]:
        """
        Detect volume breakout
        
        Conditions:
        1. Current volume > 2x average volume of lookback period
        2. Price increases on the day
        
        Args:
            close: Close prices array
            volume: Volume array
            lookback: Lookback period for average volume
            threshold: Volume ratio threshold
        
        Returns:
            VolumePriceSignal if detected, None otherwise
        """
        if len(close) < lookback + 1:
            return None
        
        current_volume = volume[-1]
        avg_volume = np.mean(volume[-lookback-1:-1])
        
        volume_ratio = current_volume / avg_volume
        
        if volume_ratio < threshold:
            return None
        
        current_close = close[-1]
        prev_close = close[-2]
        
        price_change = (current_close - prev_close) / prev_close
        
        if price_change <= 0:
            return None
        
        strength = min(volume_ratio / threshold, 1.0)
        
        return VolumePriceSignal(
            signal_type='breakout',
            days=1,
            price_change_pct=price_change * 100,
            volume_ratio=volume_ratio,
            turnover_ratio=volume_ratio,
            strength=strength,
            timestamp=pd.Timestamp.now(),
        )
    
    def detect_climax_top(
        self,
        close: np.ndarray,
        volume: np.ndarray,
        lookback: int = 20,
    ) -> Optional[VolumePriceSignal]:
        """
        Detect climax top (天量天价)
        
        Conditions:
        1. Price at recent high
        2. Volume at recent high
        3. Potential reversal signal
        
        Args:
            close: Close prices array
            volume: Volume array
            lookback: Lookback period
        
        Returns:
            VolumePriceSignal if detected, None otherwise
        """
        if len(close) < lookback:
            return None
        
        recent_close = close[-lookback:]
        recent_volume = volume[-lookback:]
        
        current_close = close[-1]
        current_volume = volume[-1]
        
        if current_close != np.max(recent_close):
            return None
        
        if current_volume != np.max(recent_volume):
            return None
        
        price_rank = np.argsort(np.argsort(recent_close))[-1]
        volume_rank = np.argsort(np.argsort(recent_volume))[-1]
        
        strength = (price_rank + volume_rank) / (2 * lookback)
        
        return VolumePriceSignal(
            signal_type='climax',
            days=1,
            price_change_pct=0,
            volume_ratio=current_volume / np.mean(recent_volume[:-1]),
            turnover_ratio=current_volume / np.mean(recent_volume[:-1]),
            strength=strength,
            timestamp=pd.Timestamp.now(),
        )
    
    def analyze(
        self,
        close: np.ndarray,
        volume: np.ndarray,
        turnover: Optional[np.ndarray] = None,
    ) -> List[VolumePriceSignal]:
        """
        Run full volume-price analysis
        
        Args:
            close: Close prices array
            volume: Volume array
            turnover: Turnover rate array (optional)
        
        Returns:
            List of detected signals
        """
        signals = []
        
        surge = self.detect_volume_price_surge(close, volume, turnover)
        if surge:
            signals.append(surge)
        
        breakout = self.detect_volume_breakout(close, volume)
        if breakout:
            signals.append(breakout)
        
        climax = self.detect_climax_top(close, volume)
        if climax:
            signals.append(climax)
        
        return signals
