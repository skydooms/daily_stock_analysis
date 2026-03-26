# 模拟交易模块开发计划

## 一、需求概述

开发一个完整的模拟交易模块，支持分钟级数据回测、股票状态管理、交易策略执行。

## 二、模块架构

```
src/trading/
├── __init__.py
├── portfolio.py          # 持仓管理
├── watchlist.py          # 关注列表管理
├── position.py           # 仓位管理
├── order.py              # 订单管理
├── fee_calculator.py     # 交易费用计算
├── price_tracker.py      # 价格追踪（3个月高低点）
├── strategies/
│   ├── __init__.py
│   ├── base.py           # 策略基类
│   ├── buy_strategies.py # 买入策略
│   └── sell_strategies.py # 卖出策略
├── backtest/
│   ├── __init__.py
│   ├── minute_engine.py  # 分钟级回测引擎
│   └── data_loader.py    # 分钟数据加载
└── signals/
    ├── __init__.py
    ├── divergence.py     # 背离检测
    └── volume_price.py   # 量价分析
```

## 三、实现步骤

### 步骤 1：创建基础数据结构

**文件**: `src/trading/portfolio.py`
- `Portfolio` 类：管理整体投资组合
- `Position` 类：单个股票持仓信息
- `WatchItem` 类：关注股票信息

**文件**: `src/trading/fee_calculator.py`
- `FeeCalculator` 类：计算交易费用
  - 佣金（默认万分之三）
  - 印花税（卖出千分之一）
  - 过户费（万分之零点二）

### 步骤 2：价格追踪模块

**文件**: `src/trading/price_tracker.py`
- `PriceTracker` 类
  - 记录3个月内 `price_min`（最低点）
  - 记录3个月内 `price_max`（最高点）
  - 记录3个月内 `open_min`（收盘最低价）
  - 记录3个月内 `close_max`（收盘最高价）
  - 每日更新统计数据

### 步骤 3：信号检测模块

**文件**: `src/trading/signals/divergence.py`
- `DivergenceDetector` 类
  - 检测120分钟级别顶背离
  - 检测120分钟级别底背离
  - 使用MACD/RSI指标判断背离

**文件**: `src/trading/signals/volume_price.py`
- `VolumePriceAnalyzer` 类
  - 检测量价齐涨（3天涨幅>10%）
  - 计算换手率变化
  - 判断单日换手率是否超过前3日平均值的1.5倍

### 步骤 4：买入策略实现

**文件**: `src/trading/strategies/buy_strategies.py`

```python
class BuyStrategy:
    """买入策略基类"""

class VolumePriceBreakout(BuyStrategy):
    """策略1: 量价齐涨突破"""
    # 3天内量价齐涨，涨幅>10%，换手率>前3日平均*1.5

class DivergenceBottom(BuyStrategy):
    """策略2: 120分钟底背离"""
    # 120分钟级别股价底背离

class DeepPullback(BuyStrategy):
    """策略3: 深度回调"""
    # 3个月内从close_max下降>35%
```

### 步骤 5：卖出策略实现

**文件**: `src/trading/strategies/sell_strategies.py`

```python
class SellStrategy:
    """卖出策略基类"""

class DivergenceTop(SellStrategy):
    """减仓策略1: 120分钟顶背离"""

class DailySurge(SellStrategy):
    """减仓策略2: 单日涨幅>10%"""

class PriceLevelReduce(SellStrategy):
    """减仓策略3: 价格达到阈值减仓"""
    # >open_min*1.22 减仓20%
    # >price_min*1.35 减仓20%

class MonthlySurge(SellStrategy):
    """减仓策略5: 月涨幅>40%清仓"""

class DivergenceBottomAdd(SellStrategy):
    """加仓策略1: 120分钟底背离"""

class DailyDrop(SellStrategy):
    """加仓策略2: 单日跌幅>10%"""
```

### 步骤 6：分钟级回测引擎

**文件**: `src/trading/backtest/minute_engine.py`

```python
class MinuteBacktestEngine:
    """分钟级回测引擎"""
    
    def __init__(self, initial_capital, fee_config):
        self.capital = initial_capital
        self.fee_calculator = FeeCalculator(fee_config)
        self.portfolio = Portfolio()
        self.watchlist = Watchlist()
    
    def run(self, data, strategies):
        """运行回测"""
        # 遍历每分钟数据
        # 检查买入信号
        # 检查卖出信号
        # 执行交易
        # 记录结果
```

### 步骤 7：数据加载器

**文件**: `src/trading/backtest/data_loader.py`

```python
class MinuteDataLoader:
    """分钟数据加载器"""
    
    def load(self, stock_code, start_date, end_date):
        """加载分钟数据"""
        # 支持从本地文件加载
        # 支持从API获取
```

### 步骤 8：Web API 接口

**文件**: `api/v1/endpoints/trading.py`

```python
@router.post("/trading/watchlist/add")
async def add_to_watchlist(stock_code: str):
    """添加关注股票"""

@router.post("/trading/position/open")
async def open_position(stock_code: str, shares: int):
    """开仓"""

@router.post("/trading/position/close")
async def close_position(stock_code: str, shares: int):
    """平仓"""

@router.get("/trading/portfolio")
async def get_portfolio():
    """获取投资组合"""

@router.post("/trading/backtest/run")
async def run_backtest(config: BacktestConfig):
    """运行回测"""
```

### 步骤 9：数据库模型

**文件**: `src/models/trading.py`

```python
class WatchItem(Base):
    """关注股票表"""
    id: int
    stock_code: str
    added_at: datetime
    status: str  # watching, position

class Position(Base):
    """持仓表"""
    id: int
    stock_code: str
    shares: int
    cost_price: float
    current_price: float
    market_value: float
    profit_loss: float
    opened_at: datetime

class Trade(Base):
    """交易记录表"""
    id: int
    stock_code: str
    trade_type: str  # buy, sell
    shares: int
    price: float
    amount: float
    fee: float
    traded_at: datetime
    strategy: str

class PriceStats(Base):
    """价格统计表"""
    id: int
    stock_code: str
    price_min: float
    price_max: float
    open_min: float
    close_max: float
    updated_at: datetime
```

### 步骤 10：测试用例

**文件**: `tests/test_trading.py`
- 测试交易费用计算
- 测试买入策略信号
- 测试卖出策略信号
- 测试回测引擎
- 测试持仓管理

## 四、配置项

在 `.env` 中添加：
```
# 交易费用配置
TRADING_COMMISSION_RATE=0.0003
TRADING_STAMP_TAX=0.001
TRADING_TRANSFER_FEE=0.00002

# 策略参数
STRATEGY_SURGE_THRESHOLD=0.10
STRATEGY_DROP_THRESHOLD=0.10
STRATEGY_OPEN_MIN_MULTIPLIER=1.22
STRATEGY_PRICE_MIN_MULTIPLIER=1.35
STRATEGY_MONTHLY_SURGE_THRESHOLD=0.40
STRATEGY_PULLBACK_THRESHOLD=0.35
```

## 五、执行顺序

1. ✅ 创建目录结构
2. ✅ 实现基础数据结构（Portfolio, Position, WatchItem）
3. ✅ 实现交易费用计算器
4. ✅ 实现价格追踪模块
5. ✅ 实现信号检测模块（背离、量价）
6. ✅ 实现买入策略
7. ✅ 实现卖出策略
8. ✅ 实现分钟级回测引擎
9. ✅ 实现数据加载器
10. ✅ 添加 Web API 接口
11. ✅ 创建数据库模型
12. ✅ 编写测试用例

## 六、依赖项

- pandas >= 2.0.0
- numpy >= 1.24.0
- sqlalchemy >= 2.0.0
- ta-lib (可选，用于技术指标)

## 七、预计工作量

- 基础模块：2小时
- 策略实现：3小时
- 回测引擎：2小时
- API接口：1小时
- 测试：1小时
- **总计：约9小时**
