# -*- coding: utf-8 -*-
"""
Advanced Trading Strategies for Backtesting

Strategies included:
1. KDJ Strategy - KDJ overbought/oversold
2. Bollinger Bands Strategy - Breakout from bands
3. Volume-Price Strategy - Volume breakout
4. Multi-Factor Strategy - Combined indicators
5. Momentum Strategy - Price momentum
6. MA Divergence Strategy - Multiple MA divergence
7. ATR Channel Strategy - Volatility-based
8. Triple Screen Strategy - Multiple timeframe confirmation
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.strategy.base import Signal, SignalType
from src.strategy.indicators import IndicatorCalculator
from src.strategy.backtest_engine import BacktestEngine, BacktestConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)


class KDJStrategy:
    """
    KDJ Strategy - Stochastic Oscillator
    
    Buy Signal: K line crosses above D line from below, both in oversold zone (<20)
    Sell Signal: K line crosses below D line from above, both in overbought zone (>80)
    """
    
    name = "KDJ_Strategy"
    description = "KDJ Stochastic Oscillator Strategy"
    
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3, oversold: float = 20, overbought: float = 80):
        self.n = n
        self.m1 = m1
        self.m2 = m2
        self.oversold = oversold
        self.overbought = overbought
        self.name = f"KDJ_{n}_{m1}_{m2}"
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        signals = []
        
        high = data["high"].values
        low = data["low"].values
        close = data["close"].values
        
        k, d, j = IndicatorCalculator.kdj(high, low, close, self.n, self.m1, self.m2)
        
        for i in range(self.n + 5, len(data)):
            if pd.isna(k[i]) or pd.isna(d[i]) or pd.isna(k[i-1]) or pd.isna(d[i-1]):
                continue
            
            if k[i-1] <= d[i-1] and k[i] > d[i] and k[i] < self.oversold + 10:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.BUY,
                    price=data.iloc[i]["close"],
                    timestamp=timestamp,
                    confidence=0.7,
                    reason=f"KDJ golden cross in oversold zone (K={k[i]:.1f}, D={d[i]:.1f})",
                    strategy_name=self.name,
                ))
            
            elif k[i-1] >= d[i-1] and k[i] < d[i] and k[i] > self.overbought - 10:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.SELL,
                    price=data.iloc[i]["close"],
                    timestamp=timestamp,
                    confidence=0.7,
                    reason=f"KDJ death cross in overbought zone (K={k[i]:.1f}, D={d[i]:.1f})",
                    strategy_name=self.name,
                ))
        
        return signals


class BollingerBandsStrategy:
    """
    Bollinger Bands Strategy
    
    Buy Signal: Price breaks below lower band and returns
    Sell Signal: Price breaks above upper band and returns
    """
    
    name = "Bollinger_Strategy"
    description = "Bollinger Bands Breakout Strategy"
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
        self.name = f"BOLL_{period}_{int(std_dev)}"
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        signals = []
        
        close = data["close"].values
        upper, middle, lower = IndicatorCalculator.bollinger_bands(close, self.period, self.std_dev)
        
        for i in range(self.period + 2, len(data)):
            if pd.isna(upper[i]) or pd.isna(lower[i]) or pd.isna(upper[i-1]) or pd.isna(lower[i-1]):
                continue
            
            prev_close = close[i-1]
            curr_close = close[i]
            
            if prev_close < lower[i-1] and curr_close > lower[i]:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.BUY,
                    price=curr_close,
                    timestamp=timestamp,
                    confidence=0.65,
                    reason=f"Price bounced from lower Bollinger Band ({lower[i]:.2f})",
                    strategy_name=self.name,
                ))
            
            elif prev_close > upper[i-1] and curr_close < upper[i]:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.SELL,
                    price=curr_close,
                    timestamp=timestamp,
                    confidence=0.65,
                    reason=f"Price reversed from upper Bollinger Band ({upper[i]:.2f})",
                    strategy_name=self.name,
                ))
        
        return signals


class VolumePriceStrategy:
    """
    Volume-Price Strategy
    
    Buy Signal: Price breaks out with high volume
    Sell Signal: Price drops with high volume
    """
    
    name = "VolumePrice_Strategy"
    description = "Volume-Price Breakout Strategy"
    
    def __init__(self, volume_ma: int = 20, volume_threshold: float = 2.0, price_ma: int = 20):
        self.volume_ma = volume_ma
        self.volume_threshold = volume_threshold
        self.price_ma = price_ma
        self.name = f"VP_{volume_ma}_{volume_threshold}"
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        signals = []
        
        close = data["close"].values
        volume = data["volume"].values.astype(float)
        
        vol_ma = IndicatorCalculator.sma(volume, self.volume_ma)
        price_ma = IndicatorCalculator.sma(close, self.price_ma)
        
        for i in range(max(self.volume_ma, self.price_ma) + 2, len(data)):
            if pd.isna(vol_ma[i]) or pd.isna(price_ma[i]):
                continue
            
            vol_ratio = volume[i] / vol_ma[i] if vol_ma[i] > 0 else 0
            
            if vol_ratio >= self.volume_threshold:
                if close[i] > close[i-1] and close[i] > price_ma[i]:
                    timestamp = data.iloc[i].get("date", i)
                    if isinstance(timestamp, str):
                        timestamp = pd.to_datetime(timestamp)
                    
                    signals.append(Signal(
                        stock_code="",
                        signal_type=SignalType.BUY,
                        price=close[i],
                        timestamp=timestamp,
                        confidence=0.7,
                        reason=f"High volume breakout (vol ratio: {vol_ratio:.1f}x)",
                        strategy_name=self.name,
                    ))
                
                elif close[i] < close[i-1] and close[i] < price_ma[i]:
                    timestamp = data.iloc[i].get("date", i)
                    if isinstance(timestamp, str):
                        timestamp = pd.to_datetime(timestamp)
                    
                    signals.append(Signal(
                        stock_code="",
                        signal_type=SignalType.SELL,
                        price=close[i],
                        timestamp=timestamp,
                        confidence=0.7,
                        reason=f"High volume breakdown (vol ratio: {vol_ratio:.1f}x)",
                        strategy_name=self.name,
                    ))
        
        return signals


class MultiFactorStrategy:
    """
    Multi-Factor Strategy - Combines multiple indicators
    
    Buy Signal: Multiple indicators show bullish signals
    Sell Signal: Multiple indicators show bearish signals
    """
    
    name = "MultiFactor_Strategy"
    description = "Multi-Factor Combined Strategy"
    
    def __init__(self, ma_fast: int = 5, ma_slow: int = 20, rsi_period: int = 14, 
                 rsi_oversold: float = 30, rsi_overbought: float = 70):
        self.ma_fast = ma_fast
        self.ma_slow = ma_slow
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.name = f"MultiFactor_{ma_fast}_{ma_slow}"
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        signals = []
        
        close = data["close"].values
        
        fast_ma = IndicatorCalculator.sma(close, self.ma_fast)
        slow_ma = IndicatorCalculator.sma(close, self.ma_slow)
        rsi = IndicatorCalculator.rsi(close, self.rsi_period)
        macd, signal_line, hist = IndicatorCalculator.macd(close)
        
        for i in range(max(self.ma_slow, self.rsi_period, 26) + 2, len(data)):
            if pd.isna(fast_ma[i]) or pd.isna(slow_ma[i]) or pd.isna(rsi[i]):
                continue
            
            bullish_score = 0
            bearish_score = 0
            
            if fast_ma[i] > slow_ma[i]:
                bullish_score += 1
            else:
                bearish_score += 1
            
            if rsi[i] < self.rsi_oversold + 10:
                bullish_score += 1
            elif rsi[i] > self.rsi_overbought - 10:
                bearish_score += 1
            
            if not pd.isna(hist[i]):
                if hist[i] > 0:
                    bullish_score += 1
                else:
                    bearish_score += 1
            
            if bullish_score >= 2 and fast_ma[i-1] <= slow_ma[i-1]:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.BUY,
                    price=close[i],
                    timestamp=timestamp,
                    confidence=0.75,
                    reason=f"Multi-factor bullish (score: {bullish_score}/3)",
                    strategy_name=self.name,
                ))
            
            elif bearish_score >= 2 and fast_ma[i-1] >= slow_ma[i-1]:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.SELL,
                    price=close[i],
                    timestamp=timestamp,
                    confidence=0.75,
                    reason=f"Multi-factor bearish (score: {bearish_score}/3)",
                    strategy_name=self.name,
                ))
        
        return signals


class MomentumStrategy:
    """
    Momentum Strategy - Based on price momentum
    
    Buy Signal: Strong positive momentum
    Sell Signal: Strong negative momentum
    """
    
    name = "Momentum_Strategy"
    description = "Price Momentum Strategy"
    
    def __init__(self, period: int = 14, threshold: float = 5.0):
        self.period = period
        self.threshold = threshold
        self.name = f"MOM_{period}"
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        signals = []
        
        close = data["close"].values
        
        momentum = np.zeros(len(close))
        for i in range(self.period, len(close)):
            momentum[i] = (close[i] - close[i-self.period]) / close[i-self.period] * 100
        
        momentum_ma = IndicatorCalculator.sma(momentum, 5)
        
        for i in range(self.period + 5, len(data)):
            if pd.isna(momentum_ma[i]) or pd.isna(momentum_ma[i-1]):
                continue
            
            if momentum_ma[i-1] < 0 and momentum_ma[i] > 0 and momentum[i] > self.threshold:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.BUY,
                    price=close[i],
                    timestamp=timestamp,
                    confidence=0.65,
                    reason=f"Strong positive momentum ({momentum[i]:.1f}%)",
                    strategy_name=self.name,
                ))
            
            elif momentum_ma[i-1] > 0 and momentum_ma[i] < 0 and momentum[i] < -self.threshold:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.SELL,
                    price=close[i],
                    timestamp=timestamp,
                    confidence=0.65,
                    reason=f"Strong negative momentum ({momentum[i]:.1f}%)",
                    strategy_name=self.name,
                ))
        
        return signals


class ATRChannelStrategy:
    """
    ATR Channel Strategy - Volatility-based breakout
    
    Buy Signal: Price breaks above upper ATR channel
    Sell Signal: Price breaks below lower ATR channel
    """
    
    name = "ATRChannel_Strategy"
    description = "ATR Channel Breakout Strategy"
    
    def __init__(self, period: int = 14, multiplier: float = 2.0):
        self.period = period
        self.multiplier = multiplier
        self.name = f"ATR_{period}_{int(multiplier)}"
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        signals = []
        
        high = data["high"].values
        low = data["low"].values
        close = data["close"].values
        
        atr = IndicatorCalculator.atr(high, low, close, self.period)
        sma = IndicatorCalculator.sma(close, self.period)
        
        upper_channel = sma + atr * self.multiplier
        lower_channel = sma - atr * self.multiplier
        
        for i in range(self.period + 2, len(data)):
            if pd.isna(upper_channel[i]) or pd.isna(lower_channel[i]):
                continue
            
            prev_close = close[i-1]
            curr_close = close[i]
            
            if prev_close < upper_channel[i-1] and curr_close > upper_channel[i]:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.BUY,
                    price=curr_close,
                    timestamp=timestamp,
                    confidence=0.7,
                    reason=f"ATR channel breakout (ATR: {atr[i]:.2f})",
                    strategy_name=self.name,
                ))
            
            elif prev_close > lower_channel[i-1] and curr_close < lower_channel[i]:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.SELL,
                    price=curr_close,
                    timestamp=timestamp,
                    confidence=0.7,
                    reason=f"ATR channel breakdown (ATR: {atr[i]:.2f})",
                    strategy_name=self.name,
                ))
        
        return signals


class TripleScreenStrategy:
    """
    Triple Screen Strategy - Multiple timeframe confirmation
    
    Screen 1: Long-term trend (MA50)
    Screen 2: Medium-term oscillator (MACD)
    Screen 3: Short-term trigger (MA5/MA10 crossover)
    """
    
    name = "TripleScreen_Strategy"
    description = "Triple Screen Strategy"
    
    def __init__(self, long_ma: int = 50, fast_ma: int = 5, slow_ma: int = 10):
        self.long_ma = long_ma
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.name = f"Triple_{long_ma}"
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        signals = []
        
        close = data["close"].values
        
        long_ma = IndicatorCalculator.sma(close, self.long_ma)
        fast_ma = IndicatorCalculator.sma(close, self.fast_ma)
        slow_ma = IndicatorCalculator.sma(close, self.slow_ma)
        macd, signal_line, hist = IndicatorCalculator.macd(close)
        
        for i in range(max(self.long_ma, 26) + 2, len(data)):
            if pd.isna(long_ma[i]) or pd.isna(fast_ma[i]) or pd.isna(slow_ma[i]):
                continue
            
            trend_up = close[i] > long_ma[i]
            trend_down = close[i] < long_ma[i]
            
            macd_up = not pd.isna(hist[i]) and hist[i] > 0
            macd_down = not pd.isna(hist[i]) and hist[i] < 0
            
            ma_cross_up = fast_ma[i] > slow_ma[i] and fast_ma[i-1] <= slow_ma[i-1]
            ma_cross_down = fast_ma[i] < slow_ma[i] and fast_ma[i-1] >= slow_ma[i-1]
            
            if trend_up and macd_up and ma_cross_up:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.BUY,
                    price=close[i],
                    timestamp=timestamp,
                    confidence=0.8,
                    reason="Triple screen bullish alignment",
                    strategy_name=self.name,
                ))
            
            elif trend_down and macd_down and ma_cross_down:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.SELL,
                    price=close[i],
                    timestamp=timestamp,
                    confidence=0.8,
                    reason="Triple screen bearish alignment",
                    strategy_name=self.name,
                ))
        
        return signals


class OBVStrategy:
    """
    OBV (On-Balance Volume) Strategy
    
    Buy Signal: OBV breaks above its MA while price is stable
    Sell Signal: OBV breaks below its MA while price is stable
    """
    
    name = "OBV_Strategy"
    description = "On-Balance Volume Strategy"
    
    def __init__(self, obv_ma: int = 20):
        self.obv_ma = obv_ma
        self.name = f"OBV_{obv_ma}"
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        signals = []
        
        close = data["close"].values
        volume = data["volume"].values.astype(float)
        
        obv = IndicatorCalculator.obv(close, volume)
        obv_ma = IndicatorCalculator.sma(obv, self.obv_ma)
        
        for i in range(self.obv_ma + 2, len(data)):
            if pd.isna(obv_ma[i]) or pd.isna(obv_ma[i-1]):
                continue
            
            obv_slope = (obv[i] - obv[i-5]) / abs(obv[i-5]) if obv[i-5] != 0 else 0
            
            if obv[i-1] < obv_ma[i-1] and obv[i] > obv_ma[i] and obv_slope > 0.05:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.BUY,
                    price=close[i],
                    timestamp=timestamp,
                    confidence=0.65,
                    reason=f"OBV breakout with accumulation",
                    strategy_name=self.name,
                ))
            
            elif obv[i-1] > obv_ma[i-1] and obv[i] < obv_ma[i] and obv_slope < -0.05:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.SELL,
                    price=close[i],
                    timestamp=timestamp,
                    confidence=0.65,
                    reason=f"OBV breakdown with distribution",
                    strategy_name=self.name,
                ))
        
        return signals


ALL_STRATEGIES = [
    {"name": "KDJ", "class": KDJStrategy, "params": {"n": 9, "m1": 3, "m2": 3}},
    {"name": "BOLL", "class": BollingerBandsStrategy, "params": {"period": 20, "std_dev": 2.0}},
    {"name": "VP", "class": VolumePriceStrategy, "params": {"volume_ma": 20, "volume_threshold": 2.0}},
    {"name": "MultiFactor", "class": MultiFactorStrategy, "params": {"ma_fast": 5, "ma_slow": 20}},
    {"name": "MOM", "class": MomentumStrategy, "params": {"period": 14, "threshold": 5.0}},
    {"name": "ATR", "class": ATRChannelStrategy, "params": {"period": 14, "multiplier": 2.0}},
    {"name": "TripleScreen", "class": TripleScreenStrategy, "params": {"long_ma": 50}},
    {"name": "OBV", "class": OBVStrategy, "params": {"obv_ma": 20}},
]


def generate_sample_data(days: int, stock_code: str) -> pd.DataFrame:
    """Generate sample data for testing"""
    np.random.seed(hash(stock_code) % 2**32)
    
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


def run_backtest_for_strategy(data: pd.DataFrame, strategy_class, params: dict, 
                              stock_code: str, initial_capital: float) -> dict:
    """Run backtest for a single strategy"""
    strategy = strategy_class(**params)
    
    backtest_config = BacktestConfig(
        initial_capital=initial_capital,
        commission_rate=0.0003,
        slippage_rate=0.001,
        position_size_pct=0.2,
    )
    
    engine = BacktestEngine(backtest_config)
    result = engine.run(strategy, data, stock_code)
    
    return {
        "strategy": strategy.name,
        "initial_capital": result.initial_capital,
        "final_capital": result.final_capital,
        "total_return": result.total_return,
        "total_return_pct": result.total_return_pct,
        "max_drawdown": result.max_drawdown,
        "max_drawdown_pct": result.max_drawdown_pct,
        "sharpe_ratio": result.sharpe_ratio,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "total_trades": result.total_trades,
        "winning_trades": result.winning_trades,
        "losing_trades": result.losing_trades,
    }


def main():
    """Main function to test all strategies"""
    print("=" * 70)
    print("Advanced Trading Strategies Backtest")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    STOCKS = [
        {"code": "03759.HK", "name": "康龙化成"},
        {"code": "002821.SZ", "name": "凯莱英"},
        {"code": "09880.HK", "name": "优必选"},
        {"code": "300850.SZ", "name": "新强联"},
        {"code": "02382.HK", "name": "舜宇光学科技"},
    ]
    
    initial_capital = 1000000
    days = 252
    
    all_results = []
    
    for stock in STOCKS:
        print(f"\n{'='*70}")
        print(f"Stock: {stock['name']} ({stock['code']})")
        print("=" * 70)
        
        data = generate_sample_data(days, stock["code"])
        
        for strategy_config in ALL_STRATEGIES:
            result = run_backtest_for_strategy(
                data, 
                strategy_config["class"], 
                strategy_config["params"],
                stock["code"],
                initial_capital
            )
            result["stock_name"] = stock["name"]
            result["stock_code"] = stock["code"]
            all_results.append(result)
            
            print(f"  {result['strategy']:20s} | Return: {result['total_return_pct']:7.2f}% | "
                  f"Sharpe: {result['sharpe_ratio']:6.2f} | Win: {result['win_rate']:5.1f}% | "
                  f"Trades: {result['total_trades']:3d}")
    
    print(f"\n{'='*70}")
    print("Strategy Summary")
    print("=" * 70)
    
    df = pd.DataFrame(all_results)
    
    strategy_stats = df.groupby("strategy").agg({
        "total_return_pct": ["mean", "std"],
        "sharpe_ratio": "mean",
        "win_rate": "mean",
        "total_trades": "sum",
    }).round(2)
    
    strategy_stats.columns = ["Avg Return%", "Std Dev", "Avg Sharpe", "Win Rate%", "Total Trades"]
    strategy_stats = strategy_stats.sort_values("Avg Sharpe", ascending=False)
    
    print("\n" + strategy_stats.to_string())
    
    output_dir = "reports"
    data_path = os.path.join(output_dir, "advanced_strategy_results.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to: {data_path}")
    
    return all_results


if __name__ == "__main__":
    results = main()
