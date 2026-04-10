#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动运行回测 - 非交互式
先运行3个月回测，再运行1年回测
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_backtest import run_backtest


def main():
    """主函数"""
    watchlist_dir = r'd:\project\data\关注和持仓'
    data_dir = r'd:\project\data\A股分时数据'
    
    print("\n" + "=" * 80)
    print("第一阶段：3个月回测")
    print("=" * 80 + "\n")
    
    results_3month = run_backtest(
        watchlist_dir=watchlist_dir,
        data_dir=data_dir,
        years=[2025, 2024],
        duration_months=3,
        initial_capital=1000000.0
    )
    
    print("\n" + "=" * 80)
    print("第二阶段：1年回测")
    print("=" * 80 + "\n")
    
    results_1year = run_backtest(
        watchlist_dir=watchlist_dir,
        data_dir=data_dir,
        years=[2025, 2024, 2023, 2022, 2021],
        duration_months=12,
        initial_capital=1000000.0
    )
    
    print("\n" + "=" * 80)
    print("回测完成！")
    print("=" * 80)
    
    return results_3month, results_1year


if __name__ == '__main__':
    main()
