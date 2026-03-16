# -*- coding: utf-8 -*-
"""
Stock List Manager - Add/Remove stocks from watchlist

Usage:
    python manage_stocks.py list                    # List all stocks
    python manage_stocks.py add 600519,002594      # Add stocks
    python manage_stocks.py remove 600519          # Remove stock

Examples:
    python manage_stocks.py add 600519,300750,03759.HK
    python manage_stocks.py remove AAPL,TSLA
    python manage_stocks.py add AAPL,TSLA,NVDA
"""

import os
import sys
from pathlib import Path
from typing import List

# 常用股票名称映射
STOCK_NAMES = {
    # A 股
    '600519': '贵州茅台',
    '000858': '五粮液',
    '002594': '比亚迪',
    '300750': '宁德时代',
    '601318': '中国平安',
    '000333': '美的集团',
    '600036': '招商银行',
    '002415': '海康威视',
    '300059': '东方财富',
    '601888': '中国中免',
    
    # 港股
    '03759.HK': '康龙化成',
    '09880.HK': '优必选',
    '02382.HK': '舜宇光学科技',
    '00700.HK': '腾讯控股',
    '09988.HK': '阿里巴巴',
    '03690.HK': '美团',
    '01810.HK': '小米集团',
    '00941.HK': '中国移动',
    
    # 美股
    'AAPL': '苹果',
    'TSLA': '特斯拉',
    'NVDA': '英伟达',
    'MSFT': '微软',
    'GOOGL': '谷歌',
    'AMZN': '亚马逊',
    'META': 'Meta',
    'NFLX': '奈飞',
    'AMD': 'AMD',
    'INTC': '英特尔',
}


def load_stocks() -> List[str]:
    """Load current stock list from .env file"""
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        print("❌ .env file not found!")
        return []
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('STOCK_LIST='):
                stocks_str = line.strip().split('=', 1)[1]
                return [s.strip() for s in stocks_str.split(',') if s.strip()]
    
    return []


def save_stocks(stocks: List[str]) -> bool:
    """Save stock list to .env file"""
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    # Read all lines
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find and replace STOCK_LIST line
    found = False
    for i, line in enumerate(lines):
        if line.startswith('STOCK_LIST='):
            lines[i] = f"STOCK_LIST={','.join(stocks)}\n"
            found = True
            break
    
    if not found:
        # Add STOCK_LIST if not exists
        lines.insert(0, f"STOCK_LIST={','.join(stocks)}\n")
    
    # Write back
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True


def get_stock_name(stock_code: str) -> str:
    """Get stock name from code"""
    code = stock_code.upper().replace('.HK', '').replace('.SZ', '').replace('.SS', '')
    
    # Try exact match first
    if stock_code in STOCK_NAMES:
        return STOCK_NAMES[stock_code]
    
    # Try without suffix
    if code in STOCK_NAMES:
        return STOCK_NAMES[code]
    
    return '未知'


def list_stocks() -> None:
    """List all stocks in watchlist"""
    stocks = load_stocks()
    
    if not stocks:
        print("📋 自选股列表为空")
        return
    
    print(f"📋 自选股列表 ({len(stocks)} 只股票)\n")
    print(f"{'序号':<6} {'代码':<12} {'名称':<15} {'市场':<8}")
    print("-" * 45)
    
    for i, stock in enumerate(stocks, 1):
        name = get_stock_name(stock)
        
        # Determine market
        if stock.endswith('.HK'):
            market = '港股'
        elif stock.endswith('.SZ'):
            market = '深市'
        elif stock.endswith('.SS') or (stock[0].isdigit() and len(stock) == 6):
            market = 'A 股'
        else:
            market = '美股'
        
        print(f"{i:<6} {stock:<12} {name:<15} {market:<8}")
    
    print("-" * 45)


def add_stocks(new_stocks: List[str]) -> None:
    """Add stocks to watchlist"""
    current = load_stocks()
    
    print(f"📋 当前自选股 ({len(current)} 只):")
    if current:
        for stock in current:
            name = get_stock_name(stock)
            print(f"  - {stock} ({name})")
    else:
        print("  (空)")
    
    print()
    
    # Add new stocks (avoid duplicates)
    added_count = 0
    for stock in new_stocks:
        stock = stock.strip().upper()
        if stock not in current:
            current.append(stock)
            name = get_stock_name(stock)
            print(f"✅ 添加：{stock} ({name})")
            added_count += 1
        else:
            name = get_stock_name(stock)
            print(f"⚠️  已存在：{stock} ({name})")
    
    if added_count > 0:
        if save_stocks(current):
            print(f"\n✨ 保存成功！共 {len(current)} 只股票")
        else:
            print("\n❌ 保存失败！")
    else:
        print("\nℹ️  没有新增股票")


def remove_stocks(stocks_to_remove: List[str]) -> None:
    """Remove stocks from watchlist"""
    current = load_stocks()
    
    print(f"📋 当前自选股 ({len(current)} 只):")
    if current:
        for stock in current:
            name = get_stock_name(stock)
            print(f"  - {stock} ({name})")
    else:
        print("  (空)")
    
    print()
    
    # Remove stocks
    removed_count = 0
    for stock in stocks_to_remove:
        stock = stock.strip().upper()
        if stock in current:
            current.remove(stock)
            name = get_stock_name(stock)
            print(f"✅ 移除：{stock} ({name})")
            removed_count += 1
        else:
            name = get_stock_name(stock)
            print(f"⚠️  未找到：{stock} ({name})")
    
    if removed_count > 0:
        if save_stocks(current):
            print(f"\n✨ 保存成功！剩余 {len(current)} 只股票")
        else:
            print("\n❌ 保存失败！")
    else:
        print("\nℹ️  没有移除任何股票")


def clear_all() -> None:
    """Clear all stocks from watchlist"""
    current = load_stocks()
    
    if not current:
        print("ℹ️  自选股列表已为空")
        return
    
    print(f"📋 即将清空 {len(current)} 只股票:")
    for stock in current:
        name = get_stock_name(stock)
        print(f"  - {stock} ({name})")
    
    confirm = input("\n⚠️  确认清空？(y/n): ").strip().lower()
    if confirm == 'y':
        if save_stocks([]):
            print("\n✨ 已清空所有股票")
        else:
            print("\n❌ 清空失败！")
    else:
        print("\nℹ️  操作已取消")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n可用命令:")
        print("  list                    - 查看所有股票")
        print("  add <代码 1,代码 2,...>   - 添加股票")
        print("  remove <代码 1,代码 2,...> - 移除股票")
        print("  clear                   - 清空所有股票")
        print("\n示例:")
        print("  python manage_stocks.py add 600519,300750,03759.HK")
        print("  python manage_stocks.py remove AAPL,TSLA")
        print("  python manage_stocks.py add 002594")
        print("  python manage_stocks.py list")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_stocks()
    
    elif command == 'add':
        if len(sys.argv) < 3:
            print("❌ 请指定要添加的股票代码")
            print("示例：python manage_stocks.py add 600519,002594")
            return
        stocks = [s.strip() for s in sys.argv[2].split(',')]
        add_stocks(stocks)
    
    elif command == 'remove':
        if len(sys.argv) < 3:
            print("❌ 请指定要移除的股票代码")
            print("示例：python manage_stocks.py remove AAPL,TSLA")
            return
        stocks = [s.strip() for s in sys.argv[2].split(',')]
        remove_stocks(stocks)
    
    elif command == 'clear':
        clear_all()
    
    else:
        print(f"❌ 未知命令：{command}")
        print("\n可用命令：list, add, remove, clear")


if __name__ == "__main__":
    main()
