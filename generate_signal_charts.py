# -*- coding: utf-8 -*-
"""
Generate buy/sell signal charts for each stock with price annotations
"""

import json
import os
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


STOCKS = [
    {"code": "03759.HK", "name": "康龙化成", "market": "HK"},
    {"code": "002821.SZ", "name": "凯莱英", "market": "A"},
    {"code": "09880.HK", "name": "优必选", "market": "HK"},
    {"code": "300850.SZ", "name": "新强联", "market": "A"},
    {"code": "02382.HK", "name": "舜宇光学科技", "market": "HK"},
]

STRATEGIES = ["MA_5_10", "MA_10_20", "MA_5_20", "MACD", "RSI"]


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


def calculate_ma_signals(data: pd.DataFrame, fast: int, slow: int) -> list:
    """Calculate MA crossover signals"""
    signals = []
    close = data["close"].values
    
    fast_ma = np.convolve(close, np.ones(fast)/fast, mode='valid')
    slow_ma = np.convolve(close, np.ones(slow)/slow, mode='valid')
    
    offset = slow - 1
    
    for i in range(1, len(slow_ma)):
        idx = i + offset
        if idx >= len(data):
            continue
            
        prev_fast = fast_ma[i-1] if i-1 < len(fast_ma) else fast_ma[i]
        prev_slow = slow_ma[i-1]
        curr_fast = fast_ma[i] if i < len(fast_ma) else fast_ma[-1]
        curr_slow = slow_ma[i]
        
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            signals.append({
                "idx": idx,
                "date": data.iloc[idx]["date"],
                "price": data.iloc[idx]["close"],
                "type": "BUY",
                "reason": f"MA{fast}金叉MA{slow}"
            })
        elif prev_fast >= prev_slow and curr_fast < curr_slow:
            signals.append({
                "idx": idx,
                "date": data.iloc[idx]["date"],
                "price": data.iloc[idx]["close"],
                "type": "SELL",
                "reason": f"MA{fast}死叉MA{slow}"
            })
    
    return signals


def calculate_macd_signals(data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> list:
    """Calculate MACD signals"""
    signals = []
    close = data["close"].values
    
    ema_fast = pd.Series(close).ewm(span=fast, adjust=False).mean()
    ema_slow = pd.Series(close).ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    
    for i in range(slow + signal, len(data)):
        if pd.isna(dif.iloc[i]) or pd.isna(dea.iloc[i]):
            continue
        if pd.isna(dif.iloc[i-1]) or pd.isna(dea.iloc[i-1]):
            continue
            
        if dif.iloc[i-1] <= dea.iloc[i-1] and dif.iloc[i] > dea.iloc[i]:
            signals.append({
                "idx": i,
                "date": data.iloc[i]["date"],
                "price": data.iloc[i]["close"],
                "type": "BUY",
                "reason": "MACD金叉"
            })
        elif dif.iloc[i-1] >= dea.iloc[i-1] and dif.iloc[i] < dea.iloc[i]:
            signals.append({
                "idx": i,
                "date": data.iloc[i]["date"],
                "price": data.iloc[i]["close"],
                "type": "SELL",
                "reason": "MACD死叉"
            })
    
    return signals


def calculate_rsi_signals(data: pd.DataFrame, period: int = 14, overbought: float = 70, oversold: float = 30) -> list:
    """Calculate RSI signals"""
    signals = []
    close = data["close"].values
    
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    
    avg_gain = np.convolve(gain, np.ones(period)/period, mode='valid')
    avg_loss = np.convolve(loss, np.ones(period)/period, mode='valid')
    
    rs = np.where(avg_loss != 0, avg_gain / avg_loss, 0)
    rsi = 100 - (100 / (1 + rs))
    
    offset = period
    
    for i in range(1, len(rsi)):
        idx = i + offset
        if idx >= len(data):
            continue
            
        prev_rsi = rsi[i-1]
        curr_rsi = rsi[i]
        
        if prev_rsi <= oversold and curr_rsi > oversold:
            signals.append({
                "idx": idx,
                "date": data.iloc[idx]["date"],
                "price": data.iloc[idx]["close"],
                "type": "BUY",
                "reason": f"RSI突破超卖线({oversold})"
            })
        elif prev_rsi >= overbought and curr_rsi < overbought:
            signals.append({
                "idx": idx,
                "date": data.iloc[idx]["date"],
                "price": data.iloc[idx]["close"],
                "type": "SELL",
                "reason": f"RSI跌破超买线({overbought})"
            })
    
    return signals


def get_signals_for_strategy(data: pd.DataFrame, strategy: str) -> list:
    """Get signals for a specific strategy"""
    if strategy == "MA_5_10":
        return calculate_ma_signals(data, 5, 10)
    elif strategy == "MA_10_20":
        return calculate_ma_signals(data, 10, 20)
    elif strategy == "MA_5_20":
        return calculate_ma_signals(data, 5, 20)
    elif strategy == "MACD":
        return calculate_macd_signals(data)
    elif strategy == "RSI":
        return calculate_rsi_signals(data)
    return []


def plot_stock_signals(data: pd.DataFrame, stock_name: str, stock_code: str, strategy: str, signals: list, output_dir: str):
    """Plot stock price with buy/sell signals"""
    fig, ax = plt.subplots(figsize=(16, 8))
    
    dates = data["date"].values
    close = data["close"].values
    
    ax.plot(dates, close, 'b-', linewidth=1.5, label='Close Price', alpha=0.8)
    
    if strategy.startswith("MA_"):
        parts = strategy.split("_")
        fast, slow = int(parts[1]), int(parts[2])
        fast_ma = np.convolve(close, np.ones(fast)/fast, mode='valid')
        slow_ma = np.convolve(close, np.ones(slow)/slow, mode='valid')
        ax.plot(dates[fast-1:], fast_ma, 'g-', linewidth=1, label=f'MA{fast}', alpha=0.6)
        ax.plot(dates[slow-1:], slow_ma, 'r-', linewidth=1, label=f'MA{slow}', alpha=0.6)
    
    buy_signals = [s for s in signals if s["type"] == "BUY"]
    sell_signals = [s for s in signals if s["type"] == "SELL"]
    
    buy_dates = [data.iloc[s["idx"]]["date"] for s in buy_signals]
    buy_prices = [s["price"] for s in buy_signals]
    sell_dates = [data.iloc[s["idx"]]["date"] for s in sell_signals]
    sell_prices = [s["price"] for s in sell_signals]
    
    ax.scatter(buy_dates, buy_prices, c='red', s=150, marker='^', label='BUY', zorder=5, edgecolors='black', linewidths=0.5)
    ax.scatter(sell_dates, sell_prices, c='green', s=150, marker='v', label='SELL', zorder=5, edgecolors='black', linewidths=0.5)
    
    for s in buy_signals[:10]:
        date = data.iloc[s["idx"]]["date"]
        price = s["price"]
        ax.annotate(f'买入\n{price:.2f}',
                   xy=(date, price),
                   xytext=(0, 20),
                   textcoords='offset points',
                   ha='center',
                   fontsize=7,
                   color='red',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='red', alpha=0.8),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='red'))
    
    for s in sell_signals[:10]:
        date = data.iloc[s["idx"]]["date"]
        price = s["price"]
        ax.annotate(f'卖出\n{price:.2f}',
                   xy=(date, price),
                   xytext=(0, -25),
                   textcoords='offset points',
                   ha='center',
                   fontsize=7,
                   color='green',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='green', alpha=0.8),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='green'))
    
    ax.set_title(f'{stock_name} ({stock_code}) - {strategy} Strategy\nBuy/Sell Signals', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date', fontsize=11)
    ax.set_ylabel('Price', fontsize=11)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    output_path = os.path.join(output_dir, f"{stock_name}_{strategy}.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path


def generate_signal_table(signals: list, data: pd.DataFrame) -> str:
    """Generate markdown table for signals"""
    if not signals:
        return "无交易信号"
    
    table = "| 序号 | 日期 | 类型 | 价格 | 原因 |\n"
    table += "|------|------|------|------|------|\n"
    
    for i, s in enumerate(signals[:30], 1):
        date_str = s["date"].strftime("%Y-%m-%d") if hasattr(s["date"], "strftime") else str(s["date"])[:10]
        signal_type = "买入" if s["type"] == "BUY" else "卖出"
        table += f"| {i} | {date_str} | {signal_type} | {s['price']:.2f} | {s['reason']} |\n"
    
    return table


def main():
    """Main function"""
    print("=" * 60)
    print("Generating Buy/Sell Signal Charts for Each Stock")
    print("=" * 60)
    
    output_dir = os.path.join("reports", "signals")
    os.makedirs(output_dir, exist_ok=True)
    
    days = 252
    
    all_reports = {}
    
    for stock in STOCKS:
        print(f"\n处理股票: {stock['name']} ({stock['code']})")
        
        data = generate_sample_data(days, stock["code"])
        
        stock_signals = {}
        
        for strategy in STRATEGIES:
            print(f"  计算 {strategy} 策略信号...")
            
            signals = get_signals_for_strategy(data, strategy)
            stock_signals[strategy] = signals
            
            chart_path = plot_stock_signals(data, stock["name"], stock["code"], strategy, signals, output_dir)
            print(f"    生成图表: {chart_path}")
        
        all_reports[stock["name"]] = {
            "code": stock["code"],
            "signals": stock_signals
        }
    
    report_path = os.path.join("reports", "signals_report.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 股票买卖点信号报告\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        for stock in STOCKS:
            f.write(f"## {stock['name']} ({stock['code']})\n\n")
            
            for strategy in STRATEGIES:
                signals = all_reports[stock["name"]]["signals"][strategy]
                
                buy_count = len([s for s in signals if s["type"] == "BUY"])
                sell_count = len([s for s in signals if s["type"] == "SELL"])
                
                f.write(f"### {strategy} 策略\n\n")
                f.write(f"- 买入信号: {buy_count} 次\n")
                f.write(f"- 卖出信号: {sell_count} 次\n\n")
                
                chart_path = f"signals/{stock['name']}_{strategy}.png"
                f.write(f"![{stock['name']} - {strategy}](../reports/{chart_path})\n\n")
                
                f.write("#### 交易信号明细\n\n")
                f.write(generate_signal_table(signals, None))
                f.write("\n\n")
            
            f.write("---\n\n")
    
    print(f"\n{'=' * 60}")
    print("信号图表生成完成!")
    print(f"{'=' * 60}")
    print(f"图表目录: {output_dir}")
    print(f"报告文件: {report_path}")


if __name__ == "__main__":
    main()
