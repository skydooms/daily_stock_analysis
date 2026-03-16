# -*- coding: utf-8 -*-
"""
Trading Strategy Module

This module provides trading strategy functionality including:
- Time slice analysis
- Technical indicators
- Backtest engine
- Signal generation
- Strategy alerts
"""

from .base import BaseStrategy, Signal, SignalType
from .time_slice import TimeSlice, TimeFrame
from .indicators import IndicatorCalculator
from .backtest_engine import BacktestEngine
from .performance import PerformanceAnalyzer
from .signal_generator import SignalGenerator
from .alert_service import AlertService

__all__ = [
    "BaseStrategy",
    "Signal",
    "SignalType",
    "TimeSlice",
    "TimeFrame",
    "IndicatorCalculator",
    "BacktestEngine",
    "PerformanceAnalyzer",
    "SignalGenerator",
    "AlertService",
]
