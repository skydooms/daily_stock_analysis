#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试回测 - 只用几只股票进行测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_backtest import (
    load_watchlist_files,
    ZipDataLoader,
    SimpleBacktestEngine,
    generate_daily_kline_chart
)
from datetime import datetime, timedelta


def main():
    """快速测试"""
    watchlist_dir = r'd:\project\data\关注和持仓'
    data_dir = r'd:\project\data\A股分时数据'
    
    print("\n" + "=" * 80)
    print("快速测试：只对前5只有数据的股票进行回测")
    print("=" * 80 + "\n")
    
    stocks = load_watchlist_files(watchlist_dir)
    print(f"总共 {len(stocks)} 只股票\n")
    
    loader = ZipDataLoader(data_dir)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    engine = SimpleBacktestEngine(initial_capital=1000000.0)
    
    results = []
    tested_count = 0
    max_test = 5
    
    for stock in stocks:
        if tested_count >= max_test:
            break
            
        stock_code = stock['code']
        stock_name = stock['name']
        
        print(f"处理股票: {stock_code} {stock_name}")
        
        minute_data = loader.load_minute_data(
            stock_code,
            years=[2025, 2024],
            start_date=start_date,
            end_date=end_date
        )
        
        if minute_data.empty:
            print(f"  ✗ 没有找到数据，跳过")
            continue
        
        print(f"  ✓ 加载到 {len(minute_data)} 条1分钟数据")
        tested_count += 1
        
        data_60min = loader.load_60min_data(
            stock_code,
            years=[2025, 2024],
            start_date=start_date,
            end_date=end_date
        )
        
        if not data_60min.empty:
            print(f"  ✓ 加载到 {len(data_60min)} 条60分钟数据")
        
        buy_points = []
        
        position_size = min(engine.cash * 0.1, 100000)
        if len(minute_data) > 0:
            first_price = minute_data['close'].iloc[0]
            shares = int(position_size / first_price / 100) * 100
            
            if shares > 0 and engine.buy(stock_code, first_price, shares, 'demo'):
                buy_points.append({
                    'date': minute_data['datetime'].iloc[0],
                    'price': first_price,
                    'shares': shares
                })
                print(f"  ✓ 模拟买入: {stock_code} @ {first_price:.2f} x {shares}股")
        
        if buy_points:
            generate_daily_kline_chart(minute_data, buy_points, stock_code, stock_name)
        
        results.append({
            'stock_code': stock_code,
            'stock_name': stock_name,
            'has_data': not minute_data.empty,
            'data_points': len(minute_data)
        })
    
    print("\n" + "=" * 80)
    print("快速测试完成")
    print("=" * 80)
    print(f"测试了 {tested_count} 只股票")
    print(f"最终资金: {engine.cash:,.2f} 元")
    print(f"交易记录数: {len(engine.trade_records)}")
    print("=" * 80)
    
    for record in engine.trade_records:
        print(f"{record['type'].upper()}: {record['stock_code']} @ {record['price']:.2f} x {record['shares']}股")
    
    return {
        'engine': engine,
        'results': results,
        'trade_records': engine.trade_records
    }


if __name__ == '__main__':
    main()
