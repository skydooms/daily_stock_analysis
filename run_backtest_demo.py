# -*- coding: utf-8 -*-
"""
Trading Strategy Backtest Demo

This script demonstrates the trading strategy backtest system.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategy.base import Signal, SignalType, StrategyConfig, StrategyType
from src.strategy.indicators import IndicatorCalculator, calculate_all_indicators
from src.strategy.backtest_engine import BacktestEngine, BacktestConfig
from src.strategy.performance import PerformanceAnalyzer


def generate_sample_data(days: int = 200) -> pd.DataFrame:
    """Generate sample stock data for testing"""
    np.random.seed(42)
    
    dates = pd.date_range(start="2024-01-01", periods=days, freq="D")
    
    trend = np.linspace(100, 130, days)
    noise = np.random.uniform(-3, 3, days)
    prices = trend + noise
    
    data = pd.DataFrame({
        "date": dates,
        "open": prices - np.random.uniform(0, 2, days),
        "high": prices + np.random.uniform(1, 4, days),
        "low": prices - np.random.uniform(1, 4, days),
        "close": prices,
        "volume": np.random.randint(1000000, 10000000, days),
    })
    
    return data


class SimpleMAStrategy:
    """Simple Moving Average Strategy for demo"""
    
    name = "SimpleMAStrategy"
    description = "Simple MA Crossover Strategy"
    
    def __init__(self, fast_period: int = 5, slow_period: int = 10):
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        """Generate trading signals"""
        signals = []
        
        close = data["close"].values
        fast_ma = IndicatorCalculator.sma(close, self.fast_period)
        slow_ma = IndicatorCalculator.sma(close, self.slow_period)
        
        for i in range(max(self.fast_period, self.slow_period), len(data)):
            if pd.isna(fast_ma[i]) or pd.isna(slow_ma[i]):
                continue
            
            if fast_ma[i-1] <= slow_ma[i-1] and fast_ma[i] > slow_ma[i]:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.BUY,
                    price=data.iloc[i]["close"],
                    timestamp=timestamp,
                    confidence=0.6,
                    reason=f"MA{self.fast_period} crossed above MA{self.slow_period}",
                    strategy_name=self.name,
                    indicators={"fast_ma": fast_ma[i], "slow_ma": slow_ma[i]}
                ))
            
            elif fast_ma[i-1] >= slow_ma[i-1] and fast_ma[i] < slow_ma[i]:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.SELL,
                    price=data.iloc[i]["close"],
                    timestamp=timestamp,
                    confidence=0.6,
                    reason=f"MA{self.fast_period} crossed below MA{self.slow_period}",
                    strategy_name=self.name,
                    indicators={"fast_ma": fast_ma[i], "slow_ma": slow_ma[i]}
                ))
        
        return signals


def run_backtest():
    """Run backtest demo"""
    print("=" * 60)
    print("Trading Strategy Backtest System Demo")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    data = generate_sample_data(200)
    print(f"\nGenerated {len(data)} days of sample data")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")
    print(f"Price range: {data['close'].min():.2f} to {data['close'].max():.2f}")
    
    print("\n" + "=" * 60)
    print("Running MA Strategy Backtest")
    print("=" * 60)
    
    strategy = SimpleMAStrategy(fast_period=5, slow_period=10)
    
    backtest_config = BacktestConfig(
        initial_capital=100000,
        commission_rate=0.0003,
        slippage_rate=0.001,
        position_size_pct=0.2,
        stop_loss_pct=0.08,
        take_profit_pct=0.15
    )
    
    engine = BacktestEngine(backtest_config)
    result = engine.run(strategy, data, "DEMO")
    
    print(f"\nStrategy: {result.strategy_name}")
    print(f"Stock: {result.stock_code}")
    print(f"Period: {result.start_date.date()} to {result.end_date.date()}")
    print(f"\n--- Performance Summary ---")
    print(f"Initial Capital: {result.initial_capital:,.2f}")
    print(f"Final Capital: {result.final_capital:,.2f}")
    print(f"Total Return: {result.total_return:,.2f} ({result.total_return_pct:.2f}%)")
    print(f"Max Drawdown: {result.max_drawdown:,.2f} ({result.max_drawdown_pct:.2f}%)")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"\n--- Trade Statistics ---")
    print(f"Total Trades: {result.total_trades}")
    print(f"Winning Trades: {result.winning_trades}")
    print(f"Losing Trades: {result.losing_trades}")
    print(f"Win Rate: {result.win_rate:.2f}%")
    print(f"Profit Factor: {result.profit_factor:.2f}")
    
    print("\n--- Trade Details (Last 10 Trades) ---")
    for trade in result.trades[-10:]:
        pnl_str = f", P&L: {trade.pnl:.2f}" if trade.pnl != 0 else ""
        print(f"  {trade.trade_type.upper()}: {trade.quantity} shares @ {trade.price:.2f}{pnl_str}")
    
    print("\n" + "=" * 60)
    print("Demo Completed!")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    result = run_backtest()
