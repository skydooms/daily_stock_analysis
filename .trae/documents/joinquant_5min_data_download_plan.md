# JoinQuant 五分钟级历史数据下载计划

## 需求概述

从 JoinQuant 下载五分钟级历史数据，包括：
- 时间范围：2019-01-01 至今日
- 数据内容：股票代码、股票名称、时间、价格、成交量、成交额等
- 存储路径：`d:\project\data\minute_data`
- 每个股票的五分钟级数据存储在单独的 CSV 文件中
- 目标股票：A股港股康龙化成、A股港股药明康德

## 账户信息

- 账户名称：13350387459
- 账户密码：127297Liu
- 每日限额：试用账号 100 万条/天，正式账号 2 亿条/天

## 技术方案

### 1. JoinQuant API 关键接口

```python
from jqdatasdk import *

# 登录认证
auth('13350387459', '127297Liu')

# 获取五分钟级数据
df = get_price(
    security='03759.XHKG',  # 港股代码格式
    start_date='2019-01-01',
    end_date='2026-03-21',
    frequency='5m',         # 五分钟级
    fields=['open', 'close', 'high', 'low', 'volume', 'money']
)

# 查询剩余流量
count = get_query_count()
print(count)  # {'total': 1000000, 'spare': 996927}
```

### 2. 股票代码映射

| 股票名称 | A股代码 | 港股代码 | JoinQuant格式 |
|---------|--------|---------|--------------|
| 康龙化成 | 300759.SZ | 03759.HK | 300759.XSHE / 03759.XHKG |
| 药明康德 | 603259.SH | 02359.HK | 603259.XSHG / 02359.XHKG |

### 3. 数据量估算

- 时间范围：2019-01-01 至 2026-03-21 ≈ 7 年
- 交易日：约 7 × 250 = 1750 天
- 每天五分钟K线数：4小时 × 12 = 48 根
- 单只股票数据量：1750 × 48 = 8.4 万条
- 4只股票总量：8.4万 × 4 = 33.6 万条

**注意**：五分钟数据量远小于一分钟数据，试用账号每日限额 100 万条足够一次性下载完成。

## 实现步骤

### Step 1: 创建下载脚本

文件路径：`scripts/download_5min_data.py`

功能：
- 使用 argparse 支持命令行参数
- 支持指定股票列表、日期范围
- 支持断点续传（检查已下载文件）
- 显示下载进度和剩余流量

### Step 2: 实现核心下载逻辑

```python
def download_5min_data(stock_code, stock_name, start_date, end_date, output_dir):
    """
    下载单只股票的五分钟级数据
    
    Args:
        stock_code: JoinQuant格式的股票代码
        stock_name: 股票名称（用于文件命名）
        start_date: 开始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        output_dir: 输出目录
    """
    # 分批下载，每次下载3个月的数据
    pass
```

### Step 3: 数据存储格式

CSV 文件列：
- datetime: 时间戳
- open: 开盘价
- close: 收盘价
- high: 最高价
- low: 最低价
- volume: 成交量
- money: 成交额

文件命名：`{stock_code}_{stock_name}_5min.csv`

### Step 4: 流量控制

- 每次下载前检查剩余流量
- 流量不足时暂停并提示
- 支持分批下载（按季度分割）

## 文件结构

```
d:\project\data\minute_data\
├── 300759_XSHE_康龙化成_5min.csv
├── 03759_XHKG_康龙化成_5min.csv
├── 603259_XSHG_药明康德_5min.csv
└── 02359_XHKG_药明康德_5min.csv
```

## 风险与注意事项

1. **流量限制**：试用账号每日 100 万条，五分钟数据约 34 万条，可一次性下载
2. **网络稳定性**：大数据量下载可能中断，需实现断点续传
3. **数据完整性**：港股数据可能不如 A 股完整
4. **账号安全**：密码建议使用环境变量存储

## 后续优化

1. 支持增量更新（只下载最新数据）
2. 支持数据压缩存储（Parquet 格式）
3. 添加数据校验和去重逻辑
