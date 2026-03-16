# -*- coding: utf-8 -*-
"""
Batch Backtest Script for 5 Stocks with Multiple Strategies

This script performs backtesting on 5 stocks with multiple strategies:
- Stocks: 康龙化成(03759.HK), 凯莱英(002821.SZ), 优必选(09880.HK), 新强联(300850.SZ), 舜宇光学科技(02382.HK)
- Strategies: MA_5_10, MA_10_20, MA_5_20, MACD, RSI
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
from src.strategy.performance import PerformanceAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)


STOCKS = [
    {"code": "03759.HK", "name": "康龙化成", "market": "HK"},
    {"code": "002821.SZ", "name": "凯莱英", "market": "A"},
    {"code": "09880.HK", "name": "优必选", "market": "HK"},
    {"code": "300850.SZ", "name": "新强联", "market": "A"},
    {"code": "02382.HK", "name": "舜宇光学科技", "market": "HK"},
]

STRATEGIES = [
    {"name": "MA_5_10", "type": "MA", "fast": 5, "slow": 10},
    {"name": "MA_10_20", "type": "MA", "fast": 10, "slow": 20},
    {"name": "MA_5_20", "type": "MA", "fast": 5, "slow": 20},
    {"name": "MACD", "type": "MACD", "fast": 12, "slow": 26, "signal": 9},
    {"name": "RSI", "type": "RSI", "period": 14, "overbought": 70, "oversold": 30},
]


class SimpleMAStrategy:
    """Simple Moving Average Strategy"""
    
    name = "MA_Strategy"
    description = "Moving Average Crossover Strategy"
    
    def __init__(self, fast_period: int = 5, slow_period: int = 10):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = f"MA_{fast_period}_{slow_period}"
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        signals = []
        
        close = data["close"].values
        fast_ma = IndicatorCalculator.sma(close, self.fast_period)
        slow_ma = IndicatorCalculator.sma(close, self.slow_period)
        
        for i in range(max(self.fast_period, self.slow_period), len(data)):
            if pd.isna(fast_ma[i]) or pd.isna(slow_ma[i]) or pd.isna(fast_ma[i-1]) or pd.isna(slow_ma[i-1]):
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
                ))
        
        return signals


class SimpleMACDStrategy:
    """Simple MACD Strategy"""
    
    name = "MACD_Strategy"
    description = "MACD Crossover Strategy"
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.name = "MACD"
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        signals = []
        
        close = data["close"].values
        dif, dea, macd = IndicatorCalculator.macd(close, self.fast, self.slow, self.signal)
        
        for i in range(self.slow + self.signal, len(data)):
            if pd.isna(dif[i]) or pd.isna(dea[i]) or pd.isna(dif[i-1]) or pd.isna(dea[i-1]):
                continue
            
            if dif[i-1] <= dea[i-1] and dif[i] > dea[i]:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.BUY,
                    price=data.iloc[i]["close"],
                    timestamp=timestamp,
                    confidence=0.6,
                    reason="MACD golden cross",
                    strategy_name=self.name,
                ))
            
            elif dif[i-1] >= dea[i-1] and dif[i] < dea[i]:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.SELL,
                    price=data.iloc[i]["close"],
                    timestamp=timestamp,
                    confidence=0.6,
                    reason="MACD death cross",
                    strategy_name=self.name,
                ))
        
        return signals


class SimpleRSIStrategy:
    """Simple RSI Strategy"""
    
    name = "RSI_Strategy"
    description = "RSI Overbought/Oversold Strategy"
    
    def __init__(self, period: int = 14, overbought: float = 70, oversold: float = 30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.name = "RSI"
    
    def generate_signals(self, data: pd.DataFrame) -> list:
        signals = []
        
        close = data["close"].values
        rsi = IndicatorCalculator.rsi(close, self.period)
        
        for i in range(self.period + 2, len(data)):
            if pd.isna(rsi[i]) or pd.isna(rsi[i-1]):
                continue
            
            if rsi[i-1] <= self.oversold and rsi[i] > self.oversold:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.BUY,
                    price=data.iloc[i]["close"],
                    timestamp=timestamp,
                    confidence=0.6,
                    reason=f"RSI crossed above oversold ({self.oversold})",
                    strategy_name=self.name,
                ))
            
            elif rsi[i-1] >= self.overbought and rsi[i] < self.overbought:
                timestamp = data.iloc[i].get("date", i)
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                signals.append(Signal(
                    stock_code="",
                    signal_type=SignalType.SELL,
                    price=data.iloc[i]["close"],
                    timestamp=timestamp,
                    confidence=0.6,
                    reason=f"RSI crossed below overbought ({self.overbought})",
                    strategy_name=self.name,
                ))
        
        return signals


def get_stock_data(stock_code: str, market: str, days: int = 252) -> pd.DataFrame:
    """Get stock historical data"""
    logger.info(f"Fetching data for {stock_code} ({market})...")
    
    if market == "HK":
        return get_hk_stock_data(stock_code, days)
    else:
        return get_a_stock_data(stock_code, days)


def setup_proxy():
    """Setup proxy for YFinance"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    use_proxy = os.getenv("USE_PROXY", "false").lower() == "true"
    if use_proxy:
        proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
        proxy_port = os.getenv("PROXY_PORT", "1087")
        proxy_url = f"http://{proxy_host}:{proxy_port}"
        
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        os.environ["http_proxy"] = proxy_url
        os.environ["https_proxy"] = proxy_url
        
        domestic_domains = [
            "eastmoney.com", "push2.eastmoney.com", "push2his.eastmoney.com",
            "fund.eastmoney.com", "fundgz.eastmoney.com", "api.fund.eastmoney.com",
            "sinajs.cn", "hq.sinajs.cn", "hq.sinajs.cn",
            "sse.com.cn", "szse.cn", "sina.com.cn",
            "akshare.xyz", "tushare.pro", "baostock.com",
            "127.0.0.1", "localhost",
        ]
        os.environ["NO_PROXY"] = ",".join(domestic_domains)
        os.environ["no_proxy"] = ",".join(domestic_domains)
        
        logger.info(f"Proxy configured: {proxy_url}")
        return True
    return False


def get_hk_stock_data(stock_code: str, days: int) -> pd.DataFrame:
    """Get Hong Kong stock data using Akshare (no proxy needed)"""
    import time
    
    try:
        import akshare as ak
        
        time.sleep(1)
        
        code = stock_code.replace(".HK", "").replace(".hk", "").zfill(5)
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days + 50)).strftime("%Y%m%d")
        
        df = ak.stock_hk_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        if df is None or df.empty:
            logger.error(f"No data found for {stock_code}")
            return generate_sample_data(days, stock_code)
        
        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
        })
        
        df["date"] = pd.to_datetime(df["date"])
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df = df.tail(days)
        
        logger.info(f"Got {len(df)} records for {stock_code} via Akshare")
        return df
        
    except Exception as e:
        logger.error(f"Failed to get HK stock data via Akshare: {e}")
        logger.info(f"Using simulated data for {stock_code}")
        return generate_sample_data(days, stock_code)


def get_hk_stock_data_yfinance(stock_code: str, days: int) -> pd.DataFrame:
    """Fallback: Get Hong Kong stock data using YFinance with proxy support"""
    import time
    
    try:
        import yfinance as yf
        
        setup_proxy()
        
        time.sleep(2)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 50)
        
        ticker = yf.Ticker(stock_code)
        df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
            logger.error(f"No data found for {stock_code}")
            return pd.DataFrame()
        
        df = df.reset_index()
        df = df.rename(columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })
        
        df["date"] = pd.to_datetime(df["date"])
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df = df.tail(days)
        
        logger.info(f"Got {len(df)} records for {stock_code} via YFinance")
        return df
        
    except Exception as e:
        logger.error(f"Failed to get HK stock data via YFinance: {e}")
        return pd.DataFrame()


def get_a_stock_data(stock_code: str, days: int) -> pd.DataFrame:
    """Get A-share stock data using AkShare"""
    try:
        import akshare as ak
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days + 50)).strftime("%Y%m%d")
        
        symbol = stock_code.split(".")[0]
        
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df.empty:
            logger.error(f"No data found for {stock_code}")
            return generate_sample_data(days, stock_code)
        
        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
        })
        
        df["date"] = pd.to_datetime(df["date"])
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df = df.tail(days)
        
        logger.info(f"Got {len(df)} records for {stock_code}")
        return df
        
    except Exception as e:
        logger.error(f"Failed to get A-share data: {e}")
        logger.info(f"Using simulated data for {stock_code}")
        return generate_sample_data(days, stock_code)


def generate_sample_data(days: int, stock_code: str) -> pd.DataFrame:
    """Generate sample data for testing when real data is not available"""
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


def create_strategy(strategy_config: dict):
    """Create strategy instance from config"""
    if strategy_config["type"] == "MA":
        return SimpleMAStrategy(strategy_config["fast"], strategy_config["slow"])
    elif strategy_config["type"] == "MACD":
        return SimpleMACDStrategy(strategy_config["fast"], strategy_config["slow"], strategy_config["signal"])
    elif strategy_config["type"] == "RSI":
        return SimpleRSIStrategy(strategy_config["period"], strategy_config["overbought"], strategy_config["oversold"])
    else:
        raise ValueError(f"Unknown strategy type: {strategy_config['type']}")


def run_backtest_for_stock(stock: dict, data: pd.DataFrame, initial_capital: float) -> List[dict]:
    """Run all strategies for a single stock"""
    results = []
    
    for strategy_config in STRATEGIES:
        strategy = create_strategy(strategy_config)
        
        backtest_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_rate=0.0003,
            slippage_rate=0.001,
            position_size_pct=0.2,
        )
        
        engine = BacktestEngine(backtest_config)
        result = engine.run(strategy, data, stock["code"])
        
        results.append({
            "stock_code": stock["code"],
            "stock_name": stock["name"],
            "strategy": strategy_config["name"],
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
            "start_date": result.start_date.isoformat() if result.start_date else None,
            "end_date": result.end_date.isoformat() if result.end_date else None,
        })
        
        logger.info(f"  {stock['name']} - {strategy_config['name']}: {result.total_return_pct:.2f}%")
    
    return results


def analyze_results(all_results: List[dict]) -> dict:
    """Analyze backtest results"""
    df = pd.DataFrame(all_results)
    
    strategy_stats = df.groupby("strategy").agg({
        "total_return_pct": ["mean", "std", "min", "max"],
        "sharpe_ratio": ["mean", "std"],
        "max_drawdown_pct": ["mean", "max"],
        "win_rate": ["mean"],
    }).round(2)
    
    strategy_ranking = df.groupby("strategy").agg({
        "total_return_pct": "mean",
        "sharpe_ratio": "mean",
    }).round(2)
    
    strategy_ranking["score"] = strategy_ranking["total_return_pct"] * 0.4 + strategy_ranking["sharpe_ratio"] * 10 * 0.6
    strategy_ranking = strategy_ranking.sort_values("score", ascending=False)
    
    stock_ranking = df.groupby(["stock_name", "strategy"]).agg({
        "total_return_pct": "mean",
        "sharpe_ratio": "mean",
    }).round(2)
    
    return {
        "strategy_stats": strategy_stats.to_dict(),
        "strategy_ranking": strategy_ranking.reset_index().to_dict("records"),
        "best_strategy": strategy_ranking.index[0] if len(strategy_ranking) > 0 else None,
        "best_return": df.loc[df["total_return_pct"].idxmax()].to_dict() if len(df) > 0 else None,
    }


def generate_report(all_results: List[dict], analysis: dict, output_path: str) -> str:
    """Generate Markdown report"""
    report = f"""# 5只股票多策略回测报告

## 一、回测概述

- **回测时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **股票数量**: 5只
- **策略数量**: 5种
- **初始资金**: 1,000,000 元

## 二、回测股票列表

| 序号 | 股票名称 | 股票代码 | 市场 |
|------|----------|----------|------|
"""
    
    for i, stock in enumerate(STOCKS, 1):
        report += f"| {i} | {stock['name']} | {stock['code']} | {'港股' if stock['market'] == 'HK' else 'A股'} |\n"
    
    report += """
## 三、回测策略

| 策略 | 参数 | 说明 |
|------|------|------|
| MA_5_10 | MA5/MA10交叉 | 短期趋势 |
| MA_10_20 | MA10/MA20交叉 | 中期趋势 |
| MA_5_20 | MA5/MA20交叉 | 短中期交叉 |
| MACD | (12,26,9) | 趋势动量 |
| RSI | (14,70,30) | 超买超卖 |

## 四、回测结果汇总

### 4.1 详细结果

| 股票 | 策略 | 收益率 | 最大回撤 | 夏普比率 | 胜率 | 交易次数 |
|------|------|--------|----------|----------|------|----------|
"""
    
    for result in all_results:
        report += f"| {result['stock_name']} | {result['strategy']} | {result['total_return_pct']:.2f}% | {result['max_drawdown_pct']:.2f}% | {result['sharpe_ratio']:.2f} | {result['win_rate']:.2f}% | {result['total_trades']} |\n"
    
    report += """
### 4.2 策略排名

| 排名 | 策略 | 平均收益率 | 平均夏普比率 | 综合评分 |
|------|------|------------|--------------|----------|
"""
    
    for i, row in enumerate(analysis["strategy_ranking"], 1):
        report += f"| {i} | {row['strategy']} | {row['total_return_pct']:.2f}% | {row['sharpe_ratio']:.2f} | {row['score']:.2f} |\n"
    
    report += f"""
## 五、分析结论

### 5.1 最佳策略
- **综合最佳策略**: {analysis.get('best_strategy', 'N/A')}

### 5.2 最佳收益
"""
    
    best = analysis.get("best_return")
    if best:
        report += f"""
- **股票**: {best['stock_name']}
- **策略**: {best['strategy']}
- **收益率**: {best['total_return_pct']:.2f}%
- **夏普比率**: {best['sharpe_ratio']:.2f}
"""
    
    report += """
### 5.3 策略有效性分析

1. **MA策略**: 适合趋势明显的行情，在震荡市中可能产生较多假信号
2. **MACD策略**: 对趋势转换敏感，但存在滞后性
3. **RSI策略**: 适合震荡行情，在强趋势中可能过早反转

### 5.4 建议

1. 建议结合多种策略进行综合判断
2. 注意控制仓位和风险
3. 定期评估策略有效性并调整参数

---

*报告生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "*"
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    return report


def main():
    """Main function"""
    import time
    
    print("=" * 70)
    print("5只股票多策略回测系统")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    setup_proxy()
    
    initial_capital = 1000000
    days = 252
    
    all_results = []
    
    for i, stock in enumerate(STOCKS):
        print(f"\n{'='*70}")
        print(f"处理股票: {stock['name']} ({stock['code']}) [{i+1}/{len(STOCKS)}]")
        print("=" * 70)
        
        data = get_stock_data(stock["code"], stock["market"], days)
        
        if data.empty:
            print(f"无法获取 {stock['name']} 数据，跳过")
            continue
        
        results = run_backtest_for_stock(stock, data, initial_capital)
        all_results.extend(results)
        
        if i < len(STOCKS) - 1:
            delay = 3 if stock["market"] == "HK" else 1
            print(f"等待 {delay} 秒后处理下一只股票...")
            time.sleep(delay)
    
    print(f"\n{'='*70}")
    print("分析结果")
    print("=" * 70)
    
    analysis = analyze_results(all_results)
    
    print(f"\n策略排名:")
    for i, row in enumerate(analysis["strategy_ranking"], 1):
        print(f"  {i}. {row['strategy']}: 平均收益 {row['total_return_pct']:.2f}%, 夏普 {row['sharpe_ratio']:.2f}")
    
    print(f"\n最佳策略: {analysis.get('best_strategy', 'N/A')}")
    
    output_dir = "reports"
    report_path = os.path.join(output_dir, "batch_backtest_report.md")
    
    print(f"\n生成报告: {report_path}")
    generate_report(all_results, analysis, report_path)
    
    data_path = os.path.join(output_dir, "backtest_data", "backtest_results.json")
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*70}")
    print("回测完成!")
    print("=" * 70)
    print(f"报告路径: {report_path}")
    print(f"数据路径: {data_path}")
    
    return all_results


if __name__ == "__main__":
    results = main()
