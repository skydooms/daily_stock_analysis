# 模拟交易回测程序使用说明

## 概述

本程序用于对关注和持仓的股票进行模拟交易回测，支持以下功能：

1. 使用100万模拟资金进行回测
2. 读取 `d:\project\data\关注和持仓` 目录下的股票列表
3. 从 `d:\project\data\A股分时数据` 加载分钟级数据
4. 支持3个月和1年的回测
5. 买入后自动生成日K线图并标注买入点

## 文件说明

- `run_backtest.py`: 主回测程序
- `BACKTEST_README.md`: 使用说明文档（本文件）

## 功能模块

### 1. 股票代码转换

将普通股票代码（如 `301205`）转换为聚宽格式：
- 6开头的股票 → `.XSHG`（上证）
- 0或3开头的股票 → `.XSHE`（深证）

### 2. 关注列表加载

自动读取 `d:\project\data\关注和持仓` 目录下的所有 `.txt` 和 `.txt.txt` 文件，解析股票代码和名称。

### 3. 数据加载

支持从zip文件加载：
- 1分钟前复权数据：`{year}_1min.zip`
- 60分钟数据：`{year}_60min.zip`

### 4. 回测引擎

简化的回测引擎，包含：
- 资金管理（初始100万）
- 持仓管理
- 交易费用计算（佣金、印花税、过户费）
- 交易记录

### 5. K线图生成

自动生成日K线图，标注买入价格和数量，保存到 `backtest_charts` 目录。

## 使用方法

### 交互式运行

```bash
python run_backtest.py
```

程序会提示选择回测模式：
- 1: 3个月回测
- 2: 1年回测

### 程序化调用

```python
from run_backtest import run_backtest

results = run_backtest(
    watchlist_dir=r'd:\project\data\关注和持仓',
    data_dir=r'd:\project\data\A股分时数据',
    years=[2025, 2024],
    duration_months=3,
    initial_capital=1000000.0
)
```

## 配置说明

### 数据目录

确保以下目录存在并包含相应数据：

```
d:\project\data\
├── 关注和持仓\
│   ├── ai.txt.txt
│   ├── 半导体.txt.txt
│   ├── 机器人.txt.txt
│   └── 港股.txt.txt
└── A股分时数据\
    └── A股_分时数据_沪深\
        ├── 1分钟_前复权_按年汇总\
        │   ├── 2021_1min.zip
        │   ├── 2024_1min.zip
        │   └── 2025_1min.zip
        └── 60分钟_按年汇总\
            ├── 2021_60min.zip
            ├── 2024_60min.zip
            └── 2025_60min.zip
```

### 交易费用

默认费用配置：
- 佣金率：0.03%（最低5元）
- 印花税率：0.1%（仅卖出）
- 过户费：0.002%

## 输出说明

### 日志输出

程序会输出详细的回测日志，包括：
- 加载的股票数量
- 每只股票的数据加载情况
- 交易记录
- 最终资金情况

### K线图

生成的K线图保存在 `backtest_charts` 目录下，文件名格式为 `{股票代码}_kline.png`。

## 扩展功能

### 添加买入策略

修改 `run_backtest` 函数中的买入逻辑：

```python
# 在加载数据后添加策略判断
if should_buy(data_60min, minute_data):
    # 执行买入
    shares = calculate_shares(engine.cash, price)
    engine.buy(stock_code, price, shares, 'custom_strategy')
```

### 添加卖出策略

类似地，添加卖出逻辑：

```python
if should_sell(data_60min, position):
    # 执行卖出
    engine.sell(stock_code, price, position['shares'], 'custom_strategy')
```

## 注意事项

1. 确保数据文件存在且格式正确
2. 首次运行可能需要安装依赖：`pip install pandas matplotlib numpy`
3. 生成的K线图使用中文标签，确保系统支持中文字体
4. 大文件加载可能需要较长时间

## 下一步计划

- 集成完整的买入策略（量价齐涨、底背离、深度回调）
- 集成完整的卖出策略（顶背离、单日涨幅、价格阈值等）
- 添加更详细的回测报告和统计指标
- 支持策略参数优化
