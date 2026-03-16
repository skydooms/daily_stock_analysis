# -*- coding: utf-8 -*-
"""
Signal Generator Module

This module provides signal generation functionality for trading strategies.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import pandas as pd
import numpy as np

from .base import Signal, SignalType, BaseStrategy


logger = logging.getLogger(__name__)


@dataclass
class SignalGeneratorConfig:
    """Signal generator configuration"""
    min_confidence: float = 0.5
    max_signals_per_day: int = 10
    signal_cooldown_minutes: int = 30
    require_confirmation: bool = False


class SignalGenerator:
    """
    Signal generator for producing trading signals
    
    Combines multiple strategies and filters signals based on rules.
    """
    
    def __init__(self, config: Optional[SignalGeneratorConfig] = None):
        """
        Initialize signal generator
        
        Args:
            config: Signal generator configuration
        """
        self.config = config or SignalGeneratorConfig()
        self._strategies: List[BaseStrategy] = []
        self._signal_handlers: List[Callable[[Signal], None]] = []
        self._last_signal_time: Optional[datetime] = None
        self._signals_today: int = 0
    
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """
        Add a strategy to the generator
        
        Args:
            strategy: Strategy to add
        """
        self._strategies.append(strategy)
        logger.info(f"Added strategy: {strategy.name}")
    
    def remove_strategy(self, strategy_name: str) -> None:
        """
        Remove a strategy by name
        
        Args:
            strategy_name: Name of strategy to remove
        """
        self._strategies = [s for s in self._strategies if s.name != strategy_name]
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        stock_code: str
    ) -> List[Signal]:
        """
        Generate signals from all strategies
        
        Args:
            data: Market data
            stock_code: Stock code
            
        Returns:
            List of filtered signals
        """
        all_signals = []
        
        for strategy in self._strategies:
            try:
                signals = strategy.generate_signals(data)
                for signal in signals:
                    signal.stock_code = stock_code
                    all_signals.append(signal)
            except Exception as e:
                logger.error(f"Strategy {strategy.name} failed: {e}")
        
        filtered_signals = self._filter_signals(all_signals)
        
        for signal in filtered_signals:
            for handler in self._signal_handlers:
                try:
                    handler(signal)
                except Exception as e:
                    logger.error(f"Signal handler error: {e}")
        
        return filtered_signals
    
    def _filter_signals(self, signals: List[Signal]) -> List[Signal]:
        """
        Filter signals based on rules
        
        Args:
            signals: List of signals to filter
            
        Returns:
            Filtered signals
        """
        filtered = []
        
        for signal in signals:
            if signal.confidence < self.config.min_confidence:
                continue
            
            if self._signals_today >= self.config.max_signals_per_day:
                continue
            
            if self._last_signal_time:
                minutes_since = (datetime.now() - self._last_signal_time).total_seconds() / 60
                if minutes_since < self.config.signal_cooldown_minutes:
                    continue
            
            filtered.append(signal)
            self._last_signal_time = datetime.now()
            self._signals_today += 1
        
        return filtered
    
    def add_signal_handler(self, handler: Callable[[Signal], None]) -> None:
        """
        Add a signal handler
        
        Args:
            handler: Handler function
        """
        self._signal_handlers.append(handler)
    
    def reset_daily(self) -> None:
        """Reset daily counters"""
        self._signals_today = 0
        self._last_signal_time = None
    
    def get_latest_signal(
        self,
        data: pd.DataFrame,
        stock_code: str
    ) -> Optional[Signal]:
        """
        Get the most recent signal
        
        Args:
            data: Market data
            stock_code: Stock code
            
        Returns:
            Latest signal or None
        """
        signals = self.generate_signals(data, stock_code)
        
        if signals:
            return max(signals, key=lambda s: s.timestamp)
        
        return None
    
    def get_signal_summary(
        self,
        data: pd.DataFrame,
        stock_code: str
    ) -> Dict[str, Any]:
        """
        Get signal summary for a stock
        
        Args:
            data: Market data
            stock_code: Stock code
            
        Returns:
            Signal summary dictionary
        """
        signals = self.generate_signals(data, stock_code)
        
        buy_signals = [s for s in signals if s.is_buy]
        sell_signals = [s for s in signals if s.is_sell]
        
        avg_confidence = np.mean([s.confidence for s in signals]) if signals else 0
        
        return {
            "stock_code": stock_code,
            "total_signals": len(signals),
            "buy_signals": len(buy_signals),
            "sell_signals": len(sell_signals),
            "avg_confidence": avg_confidence,
            "latest_signal": signals[-1].to_dict() if signals else None,
        }
