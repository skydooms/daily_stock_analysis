# -*- coding: utf-8 -*-
"""
Trading Strategy Base Module

This module provides the base class for all trading strategies.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Trading signal type"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


class StrategyType(Enum):
    """Strategy type"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    MULTI_FACTOR = "multi_factor"


@dataclass
class Signal:
    """
    Trading signal data class
    
    Represents a trading signal with all necessary information.
    """
    stock_code: str
    signal_type: SignalType
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 0.5
    reason: str = ""
    strategy_name: str = ""
    indicators: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stock_code": self.stock_code,
            "signal_type": self.signal_type.value,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "reason": self.reason,
            "strategy_name": self.strategy_name,
            "indicators": self.indicators,
        }
    
    @property
    def is_buy(self) -> bool:
        """Check if signal is buy type"""
        return self.signal_type in (SignalType.BUY, SignalType.STRONG_BUY)
    
    @property
    def is_sell(self) -> bool:
        """Check if signal is sell type"""
        return self.signal_type in (SignalType.SELL, SignalType.STRONG_SELL)


@dataclass
class StrategyConfig:
    """Strategy configuration"""
    name: str = ""
    description: str = ""
    strategy_type: StrategyType = StrategyType.TREND_FOLLOWING
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type.value,
            "params": self.params,
            "enabled": self.enabled,
        }


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies
    
    All strategy implementations must inherit from this class
    and implement the required methods.
    """
    
    name: str = "BaseStrategy"
    description: str = "Base strategy class"
    strategy_type: StrategyType = StrategyType.TREND_FOLLOWING
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        """
        Initialize strategy
        
        Args:
            config: Strategy configuration
        """
        self.config = config or StrategyConfig()
        self.params = self.config.params or {}
        self._signals: List[Signal] = []
        self._last_signal: Optional[Signal] = None
        
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Generate trading signals from data
        
        Args:
            data: DataFrame with OHLCV data and indicators
            
        Returns:
            List of Signal objects
        """
        pass
    
    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """
        Get list of required indicators for this strategy
        
        Returns:
            List of indicator names
        """
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Validate input data has required columns
        
        Args:
            data: Input DataFrame
            
        Returns:
            True if data is valid
        """
        required_columns = ["open", "high", "low", "close", "volume"]
        for col in required_columns:
            if col not in data.columns:
                logger.error(f"Missing required column: {col}")
                return False
        return True
    
    def calculate_position_size(
        self,
        capital: float,
        price: float,
        risk_pct: float = 0.02
    ) -> int:
        """
        Calculate position size based on risk management
        
        Args:
            capital: Available capital
            price: Current price
            risk_pct: Risk percentage per trade
            
        Returns:
            Number of shares to trade
        """
        risk_amount = capital * risk_pct
        position_value = min(capital * 0.1, risk_amount * 10)  # Max 10% of capital
        shares = int(position_value / price)
        return max(shares, 0)
    
    def set_param(self, key: str, value: Any) -> None:
        """Set strategy parameter"""
        self.params[key] = value
        
    def get_param(self, key: str, default: Any = None) -> Any:
        """Get strategy parameter"""
        return self.params.get(key, default)
    
    def get_signals(self) -> List[Signal]:
        """Get all generated signals"""
        return self._signals
    
    def get_last_signal(self) -> Optional[Signal]:
        """Get last generated signal"""
        return self._last_signal
    
    def clear_signals(self) -> None:
        """Clear all signals"""
        self._signals.clear()
        self._last_signal = None
    
    def add_signal(self, signal: Signal) -> None:
        """Add a signal to the list"""
        signal.strategy_name = self.name
        self._signals.append(signal)
        self._last_signal = signal
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy info to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type.value,
            "params": self.params,
            "signal_count": len(self._signals),
            "last_signal": self._last_signal.to_dict() if self._last_signal else None,
        }


class StrategyManager:
    """
    Strategy manager for handling multiple strategies
    """
    
    def __init__(self):
        """Initialize strategy manager"""
        self._strategies: Dict[str, BaseStrategy] = {}
        self._signal_handlers: List[Callable[[Signal], None]] = []
    
    def register_strategy(self, strategy: BaseStrategy) -> None:
        """Register a strategy"""
        self._strategies[strategy.name] = strategy
        logger.info(f"Registered strategy: {strategy.name}")
    
    def unregister_strategy(self, name: str) -> None:
        """Unregister a strategy"""
        if name in self._strategies:
            del self._strategies[name]
            logger.info(f"Unregistered strategy: {name}")
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Get strategy by name"""
        return self._strategies.get(name)
    
    def get_all_strategies(self) -> List[BaseStrategy]:
        """Get all registered strategies"""
        return list(self._strategies.values())
    
    def add_signal_handler(self, handler: Callable[[Signal], None]) -> None:
        """Add a signal handler"""
        self._signal_handlers.append(handler)
    
    def run_all_strategies(self, data: pd.DataFrame, stock_code: str) -> List[Signal]:
        """
        Run all registered strategies on data
        
        Args:
            data: DataFrame with OHLCV data
            stock_code: Stock code
            
        Returns:
            List of all signals from all strategies
        """
        all_signals = []
        
        for name, strategy in self._strategies.items():
            try:
                signals = strategy.generate_signals(data)
                for signal in signals:
                    signal.stock_code = stock_code
                    all_signals.append(signal)
                    
                    for handler in self._signal_handlers:
                        try:
                            handler(signal)
                        except Exception as e:
                            logger.error(f"Signal handler error: {e}")
                            
            except Exception as e:
                logger.error(f"Strategy {name} failed: {e}")
        
        return all_signals
