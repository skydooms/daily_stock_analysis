#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行完整回测
先运行3个月回测，再运行1年回测
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_backtest import main as run_backtest_main


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("第一阶段：3个月回测")
    print("=" * 80 + "\n")
    
    results_3month = run_backtest_main(['1'])
    
    print("\n" + "=" * 80)
    print("第二阶段：1年回测")
    print("=" * 80 + "\n")
    
    results_1year = run_backtest_main(['2'])
    
    print("\n" + "=" * 80)
    print("回测全部完成！")
    print("=" * 80)
    
    return results_3month, results_1year


if __name__ == '__main__':
    main()
