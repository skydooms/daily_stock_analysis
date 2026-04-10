#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
底部放量策略回测验证

测试 BottomVolumeSurge 策略在5只股票、3个时间段上的表现。
数据来源: 日线CSV文件（含预计算指标）
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.trading.strategies.buy_strategies import BottomVolumeSurge, BuySignal
from src.trading.strategies.sell_strategies import BottomVolumeSell, SellSignal
from src.trading.portfolio import Portfolio
from src.trading.fee_calculator import FeeConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# Configuration
# ============================================================
STOCKS = {
    "603259": "药明康德",
    "300759": "康龙化成",
    "600276": "恒瑞医药",
    "300850": "新强联",
    "300760": "迈瑞医疗",
}

PERIODS = [
    ("2023-01-01", "2023-12-31"),
    ("2024-01-01", "2024-12-31"),
    ("2025-01-01", "2025-12-31"),
]

DATA_DIR = "/home/sky/project/日_按年归档"
CHART_DIR = "backtest_charts"
INITIAL_CAPITAL = 1_000_000.0
POSITION_SIZE_PCT = 0.25
MAX_POSITION_PCT = 0.80
SLIPPAGE_RATE = 0.001
LOOKBACK_DAYS = 60  # Extra days before start for indicator warmup

# Chinese font setup
for font in ['SimHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'AR PL UMing CN']:
    try:
        matplotlib.font_manager.FontProperties(fname=font)
        plt.rcParams['font.sans-serif'] = [font]
        break
    except Exception:
        continue
plt.rcParams['axes.unicode_minus'] = False


# ============================================================
# Data Loading
# ============================================================
def load_daily_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Load daily CSV data with indicator warmup period."""
    file_path = os.path.join(DATA_DIR, f"{stock_code}_daily_with_indicators.csv")
    if not os.path.exists(file_path):
        logger.warning(f"Data file not found: {file_path}")
        return pd.DataFrame()

    df = pd.read_csv(file_path, encoding='utf-8-sig')
    df['date'] = pd.to_datetime(df['date'])

    # Load extra lookback days before start_date for warmup
    warmup_start = pd.to_datetime(start_date) - timedelta(days=LOOKBACK_DAYS)
    mask = (df['date'] >= warmup_start) & (df['date'] <= pd.to_datetime(end_date))
    df = df[mask].reset_index(drop=True)

    return df


# ============================================================
# Backtest Engine
# ============================================================
def run_single_backtest(
    stock_code: str,
    stock_name: str,
    daily_data: pd.DataFrame,
    trade_start_date: str,
) -> Dict:
    """Run backtest for a single stock in a single period."""
    if daily_data.empty or len(daily_data) < 30:
        return {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "trade_records": [],
            "equity_curve": [],
            "signals": [],
        }

    buy_strategy = BottomVolumeSurge()
    sell_strategy = BottomVolumeSell()

    portfolio = Portfolio(
        initial_capital=INITIAL_CAPITAL,
        fee_config=FeeConfig(),
    )

    trade_records = []
    equity_curve = []
    signals_log = []
    trade_start = pd.to_datetime(trade_start_date)

    # Find the index where trading starts (after warmup)
    start_idx = 30  # Minimum warmup
    for i in range(len(daily_data)):
        if daily_data['date'].iloc[i] >= trade_start:
            start_idx = max(start_idx, i)
            break

    for i in range(start_idx, len(daily_data)):
        current_date = daily_data['date'].iloc[i]
        current_close = float(daily_data['close'].iloc[i])
        data_slice = daily_data.iloc[:i + 1]

        position = portfolio.get_position(stock_code)

        # Check buy signals if no position
        if position is None or position.shares == 0:
            signal = buy_strategy.check(stock_code, data_slice)
            if signal:
                # Position sizing: 25% of available cash
                buy_price = current_close * (1 + SLIPPAGE_RATE)
                shares = int(portfolio.cash * POSITION_SIZE_PCT / buy_price / 100) * 100

                if shares > 0:
                    result = portfolio.buy(
                        stock_code=stock_code,
                        shares=shares,
                        price=buy_price,
                        stock_name=stock_name,
                        strategy=signal.strategy_name,
                    )
                    if result:
                        # Set stop-loss on sell strategy
                        sell_strategy.set_stop_loss(
                            stock_code,
                            signal.details.get("stop_loss_price", float(signal.details.get("recent_low", current_close * 0.95)) * 0.98)
                        )
                        trade_records.append({
                            "type": "buy",
                            "date": current_date.strftime("%Y-%m-%d"),
                            "price": buy_price,
                            "shares": shares,
                            "reason": signal.reason,
                            "confidence": signal.confidence,
                        })
                        signals_log.append({
                            "type": "buy",
                            "date": current_date,
                            "price": buy_price,
                        })
                        logger.info(
                            f"  BUY {stock_code} {stock_name} @ {buy_price:.2f} x {shares} "
                            f"on {current_date.strftime('%Y-%m-%d')} | {signal.reason}"
                        )

        # Check sell signals if has position
        elif position and position.shares > 0:
            # Update position current price
            position.update_price(current_close)

            pos_dict = position.to_dict()
            sell_signal = sell_strategy.check(stock_code, data_slice, pos_dict)

            if sell_signal:
                sell_price = current_close * (1 - SLIPPAGE_RATE)

                if sell_signal.shares_pct >= 1.0:
                    shares_to_sell = position.shares
                else:
                    shares_to_sell = int(position.shares * sell_signal.shares_pct / 100) * 100
                    shares_to_sell = max(shares_to_sell, 100)
                    shares_to_sell = min(shares_to_sell, position.shares)

                if shares_to_sell > 0:
                    result = portfolio.sell(
                        stock_code=stock_code,
                        shares=shares_to_sell,
                        price=sell_price,
                        strategy=sell_signal.strategy_name,
                    )
                    if result:
                        realized_pl = result.get("realized_pl", 0)
                        trade_records.append({
                            "type": "sell",
                            "date": current_date.strftime("%Y-%m-%d"),
                            "price": sell_price,
                            "shares": shares_to_sell,
                            "reason": sell_signal.reason,
                            "realized_pl": realized_pl,
                        })
                        signals_log.append({
                            "type": "sell",
                            "date": current_date,
                            "price": sell_price,
                        })
                        logger.info(
                            f"  SELL {stock_code} {stock_name} @ {sell_price:.2f} x {shares_to_sell} "
                            f"on {current_date.strftime('%Y-%m-%d')} | {sell_signal.reason} | PL: {realized_pl:.2f}"
                        )

        equity_curve.append(portfolio.total_value)

    # Calculate metrics
    final_value = portfolio.total_value
    total_return_pct = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    equity_array = np.array(equity_curve)
    max_drawdown_pct = 0.0
    sharpe_ratio = 0.0
    if len(equity_array) > 1:
        # Max drawdown
        peak = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array - peak) / peak
        max_drawdown_pct = float(np.min(drawdowns) * 100)

        # Sharpe ratio
        daily_returns = np.diff(equity_array) / equity_array[:-1]
        if np.std(daily_returns) > 0:
            sharpe_ratio = float(np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252))

    sell_trades = [t for t in trade_records if t["type"] == "sell"]
    winning_trades = sum(1 for t in sell_trades if t.get("realized_pl", 0) > 0)
    losing_trades = sum(1 for t in sell_trades if t.get("realized_pl", 0) <= 0)
    total_trades = winning_trades + losing_trades
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "total_return_pct": total_return_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "sharpe_ratio": sharpe_ratio,
        "win_rate": win_rate,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "trade_records": trade_records,
        "equity_curve": equity_curve,
        "signals": signals_log,
        "final_value": final_value,
    }


# ============================================================
# Chart Generation
# ============================================================
def generate_kline_chart(
    daily_data: pd.DataFrame,
    signals: List[Dict],
    stock_code: str,
    stock_name: str,
    period_label: str,
    result: Dict,
    output_dir: str = CHART_DIR,
):
    """Generate K-line chart with buy/sell markers and volume subplot."""
    os.makedirs(output_dir, exist_ok=True)

    # Filter to trading period only (exclude warmup)
    trade_start = pd.to_datetime(period_label.split("~")[0])
    df = daily_data[daily_data['date'] >= trade_start].copy()
    if df.empty:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[3, 1],
                                     gridspec_kw={'hspace': 0.15})

    dates = df['date'].values
    opens = df['open'].values
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    volumes = df['volume'].values

    # Draw candlesticks
    up = closes >= opens
    down = ~up

    width = 0.6
    thin_width = 0.15

    # Up candles (red)
    if np.any(up):
        up_dates = dates[up]
        ax1.bar(up_dates, closes[up] - opens[up], width, bottom=opens[up], color='red', alpha=0.8)
        ax1.bar(up_dates, highs[up] - closes[up], thin_width, bottom=closes[up], color='red', alpha=0.8)
        ax1.bar(up_dates, lows[up] - opens[up], thin_width, bottom=opens[up], color='red', alpha=0.8)

    # Down candles (green)
    if np.any(down):
        down_dates = dates[down]
        ax1.bar(down_dates, closes[down] - opens[down], width, bottom=opens[down], color='green', alpha=0.8)
        ax1.bar(down_dates, highs[down] - opens[down], thin_width, bottom=opens[down], color='green', alpha=0.8)
        ax1.bar(down_dates, lows[down] - closes[down], thin_width, bottom=closes[down], color='green', alpha=0.8)

    # MA lines
    for col, color, label in [('MA5', '#FF6600', 'MA5'), ('MA10', '#0066FF', 'MA10'), ('MA20', '#CC00CC', 'MA20')]:
        if col in df.columns:
            ma_vals = df[col].values
            valid = ~pd.isna(ma_vals)
            if np.any(valid):
                ax1.plot(dates[valid], ma_vals[valid], color=color, linewidth=1, label=label, alpha=0.7)

    # Buy/Sell markers
    for sig in signals:
        sig_date = sig['date']
        sig_price = sig['price']
        if sig['type'] == 'buy':
            ax1.scatter(sig_date, sig_price * 0.98, color='blue', s=120, zorder=5, marker='^')
            ax1.annotate(
                f'买入\n{sig_price:.2f}',
                xy=(sig_date, sig_price * 0.98),
                xytext=(10, -25),
                textcoords='offset points',
                fontsize=8,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8),
                arrowprops=dict(arrowstyle='->', color='blue'),
            )
        else:
            ax1.scatter(sig_date, sig_price * 1.02, color='purple', s=120, zorder=5, marker='v')
            ax1.annotate(
                f'卖出\n{sig_price:.2f}',
                xy=(sig_date, sig_price * 1.02),
                xytext=(10, 15),
                textcoords='offset points',
                fontsize=8,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFCCCC', alpha=0.8),
                arrowprops=dict(arrowstyle='->', color='purple'),
            )

    ax1.legend(loc='upper left', fontsize=9)
    ax1.set_title(
        f'{stock_name} ({stock_code}) 底部放量策略回测 [{period_label}]\n'
        f'收益率: {result["total_return_pct"]:.2f}% | 最大回撤: {result["max_drawdown_pct"]:.2f}% | '
        f'胜率: {result["win_rate"]:.1f}% | 交易次数: {result["total_trades"]}',
        fontsize=13,
    )
    ax1.set_ylabel('价格', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator())

    # Volume subplot
    vol_colors = np.where(closes >= opens, 'red', 'green')
    ax2.bar(dates, volumes, width=0.6, color=vol_colors, alpha=0.6)
    ax2.set_ylabel('成交量', fontsize=11)
    ax2.set_xlabel('日期', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator())

    plt.xticks(rotation=30)
    plt.tight_layout()

    year_label = period_label.replace("~", "_")
    output_file = os.path.join(output_dir, f'{stock_code}_{year_label}_bottom_volume.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    logger.info(f"  Chart saved: {output_file}")
    plt.close()


# ============================================================
# Results Display
# ============================================================
def print_results_table(all_results: List[Dict]):
    """Print formatted results table."""
    print("\n" + "=" * 120)
    print("底部放量策略回测结果汇总")
    print("=" * 120)
    print(f"{'股票':>12s} {'时间段':>24s} {'收益率%':>10s} {'最大回撤%':>10s} {'Sharpe':>8s} "
          f"{'胜率%':>8s} {'交易数':>8s} {'盈利':>6s} {'亏损':>6s} {'最终资金':>16s}")
    print("-" * 120)

    for r in all_results:
        print(
            f"{r['stock_name']:>10s}({r['stock_code']}) "
            f"{r['period']:>24s} "
            f"{r['total_return_pct']:>9.2f}% "
            f"{r['max_drawdown_pct']:>9.2f}% "
            f"{r['sharpe_ratio']:>8.2f} "
            f"{r['win_rate']:>7.1f}% "
            f"{r['total_trades']:>8d} "
            f"{r['winning_trades']:>6d} "
            f"{r['losing_trades']:>6d} "
            f"{r.get('final_value', INITIAL_CAPITAL):>14,.2f}"
        )

    print("=" * 120)

    # Aggregate stats
    if all_results:
        avg_return = np.mean([r['total_return_pct'] for r in all_results])
        avg_drawdown = np.mean([r['max_drawdown_pct'] for r in all_results])
        total_trades = sum(r['total_trades'] for r in all_results)
        total_wins = sum(r['winning_trades'] for r in all_results)
        total_losses = sum(r['losing_trades'] for r in all_results)
        overall_win_rate = (total_wins / (total_wins + total_losses) * 100) if (total_wins + total_losses) > 0 else 0

        print(f"\n汇总统计:")
        print(f"  平均收益率:  {avg_return:.2f}%")
        print(f"  平均最大回撤: {avg_drawdown:.2f}%")
        print(f"  总交易次数:  {total_trades}")
        print(f"  总胜率:     {overall_win_rate:.1f}% ({total_wins}胜/{total_losses}负)")

    # Print trade details
    print("\n" + "=" * 120)
    print("交易明细")
    print("=" * 120)
    for r in all_results:
        if r['trade_records']:
            print(f"\n--- {r['stock_name']}({r['stock_code']}) [{r['period']}] ---")
            for t in r['trade_records']:
                if t['type'] == 'buy':
                    print(f"  买入 {t['date']} @ {t['price']:.2f} x {t['shares']}股 | {t['reason']}")
                else:
                    pl = t.get('realized_pl', 0)
                    pl_str = f"+{pl:.2f}" if pl > 0 else f"{pl:.2f}"
                    print(f"  卖出 {t['date']} @ {t['price']:.2f} x {t['shares']}股 | {t['reason']} | 盈亏: {pl_str}")


# ============================================================
# Main
# ============================================================
def main():
    logger.info("=" * 60)
    logger.info("底部放量策略回测验证")
    logger.info(f"初始资金: {INITIAL_CAPITAL:,.0f} 元")
    logger.info(f"股票: {', '.join(f'{name}({code})' for code, name in STOCKS.items())}")
    logger.info(f"时间段: {len(PERIODS)} 个")
    logger.info("=" * 60)

    all_results = []

    for stock_code, stock_name in STOCKS.items():
        for start_date, end_date in PERIODS:
            period_label = f"{start_date}~{end_date}"
            logger.info(f"\n{'='*40}")
            logger.info(f"回测: {stock_name}({stock_code}) [{period_label}]")
            logger.info(f"{'='*40}")

            # Load data
            daily_data = load_daily_data(stock_code, start_date, end_date)
            if daily_data.empty:
                logger.warning(f"  No data for {stock_code}, skipping")
                all_results.append({
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "period": period_label,
                    "total_return_pct": 0.0,
                    "max_drawdown_pct": 0.0,
                    "sharpe_ratio": 0.0,
                    "win_rate": 0.0,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "trade_records": [],
                    "signals": [],
                })
                continue

            logger.info(f"  Loaded {len(daily_data)} rows, date range: "
                       f"{daily_data['date'].iloc[0].strftime('%Y-%m-%d')} to "
                       f"{daily_data['date'].iloc[-1].strftime('%Y-%m-%d')}")

            # Run backtest
            result = run_single_backtest(stock_code, stock_name, daily_data, start_date)
            result["period"] = period_label

            # Generate chart
            generate_kline_chart(
                daily_data, result["signals"], stock_code, stock_name,
                period_label, result,
            )

            all_results.append(result)

    # Print summary
    print_results_table(all_results)

    logger.info("\n回测完成!")
    return all_results


if __name__ == '__main__':
    main()
