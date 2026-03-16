# 如何添加持有和关注的股票

## 方法一：直接编辑 .env 文件（推荐）

### 步骤：

1. 打开项目根目录的 `.env` 文件
2. 找到第 8 行的 `STOCK_LIST` 配置
3. 修改为您想要持有和关注的股票代码

### 示例：

```bash
# 原始配置（美股）
STOCK_LIST=AAPL,TSLA,NVDA,MSFT,GOOGL,AMZN,META

# 修改为 A 股和港股
STOCK_LIST=600519,002594,300750,03759.HK,09880.HK,02382.HK

# 或者混合配置
STOCK_LIST=AAPL,TSLA,600519,002594,03759.HK
```

### 股票代码格式：

- **A 股**：6 位数字，如 `600519`（贵州茅台）、`002594`（比亚迪）、`300750`（宁德时代）
- **港股**：5-6 位数字 + `.HK`，如 `03759.HK`（康龙化成）、`09880.HK`（优必选）
- **美股**：股票代码，如 `AAPL`（苹果）、`TSLA`（特斯拉）

---

## 方法二：使用管理脚本

### 创建股票管理脚本

```python
# save to: manage_stocks.py
# -*- coding: utf-8 -*-
"""
Stock List Manager - Add/Remove stocks from watchlist
"""

import os
from pathlib import Path
from typing import List

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

def add_stocks(new_stocks: List[str]) -> None:
    """Add stocks to watchlist"""
    current = load_stocks()
    print(f"📋 Current watchlist ({len(current)} stocks):")
    for stock in current:
        print(f"  - {stock}")
    
    # Add new stocks (avoid duplicates)
    for stock in new_stocks:
        if stock not in current:
            current.append(stock)
            print(f"✅ Added: {stock}")
        else:
            print(f"⚠️  Already exists: {stock}")
    
    if save_stocks(current):
        print(f"\n✨ Saved! Total stocks: {len(current)}")
    else:
        print("\n❌ Failed to save!")

def remove_stocks(stocks_to_remove: List[str]) -> None:
    """Remove stocks from watchlist"""
    current = load_stocks()
    print(f"📋 Current watchlist ({len(current)} stocks):")
    for stock in current:
        print(f"  - {stock}")
    
    # Remove stocks
    for stock in stocks_to_remove:
        if stock in current:
            current.remove(stock)
            print(f"✅ Removed: {stock}")
        else:
            print(f"⚠️  Not found: {stock}")
    
    if save_stocks(current):
        print(f"\n✨ Saved! Total stocks: {len(current)}")
    else:
        print("\n❌ Failed to save!")

def list_stocks() -> None:
    """List all stocks in watchlist"""
    stocks = load_stocks()
    print(f"📋 Watchlist ({len(stocks)} stocks):")
    for i, stock in enumerate(stocks, 1):
        print(f"  {i}. {stock}")

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python manage_stocks.py list                    # List all stocks")
        print("  python manage_stocks.py add 600519,002594      # Add stocks")
        print("  python manage_stocks.py remove 600519          # Remove stock")
        print("\nExamples:")
        print("  python manage_stocks.py add 600519,300750,03759.HK")
        print("  python manage_stocks.py remove AAPL,TSLA")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_stocks()
    
    elif command == 'add':
        if len(sys.argv) < 3:
            print("❌ Please specify stocks to add")
            return
        stocks = [s.strip() for s in sys.argv[2].split(',')]
        add_stocks(stocks)
    
    elif command == 'remove':
        if len(sys.argv) < 3:
            print("❌ Please specify stocks to remove")
            return
        stocks = [s.strip() for s in sys.argv[2].split(',')]
        remove_stocks(stocks)
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()
```

### 使用方法：

```bash
# 查看当前股票列表
python manage_stocks.py list

# 添加股票
python manage_stocks.py add 600519,002594,300750

# 添加港股
python manage_stocks.py add 03759.HK,09880.HK

# 添加美股
python manage_stocks.py add AAPL,TSLA,NVDA

# 移除股票
python manage_stocks.py remove AAPL,TSLA

# 混合操作
python manage_stocks.py add 600519,03759.HK
python manage_stocks.py remove META
```

---

## 方法三：通过 Web 界面（如果有）

如果项目部署了 Web 界面，可以通过设置页面管理股票列表。

---

## 常用股票代码参考

### A 股热门股票：
- **600519** - 贵州茅台
- **002594** - 比亚迪
- **300750** - 宁德时代
- **000858** - 五粮液
- **601318** - 中国平安

### 港股热门股票：
- **03759.HK** - 康龙化成
- **09880.HK** - 优必选
- **02382.HK** - 舜宇光学科技
- **00700.HK** - 腾讯控股
- **09988.HK** - 阿里巴巴

### 美股热门股票：
- **AAPL** - 苹果
- **TSLA** - 特斯拉
- **NVDA** - 英伟达
- **MSFT** - 微软
- **GOOGL** - 谷歌
- **AMZN** - 亚马逊
- **META** - Meta

---

## 验证配置

修改后运行以下命令验证：

```bash
# 查看配置
python -c "from src.config import get_config; cfg = get_config(); print('Stocks:', cfg.stock_list)"

# 或者运行分析
python main.py
```

---

## 注意事项

1. **股票代码格式**：确保格式正确，A 股 6 位数字，港股加 `.HK` 后缀
2. **逗号分隔**：多个股票用英文逗号分隔，不要有空格
3. **保存后重启**：修改配置后需要重启程序才能生效
4. **备份配置**：修改前建议备份 `.env` 文件
