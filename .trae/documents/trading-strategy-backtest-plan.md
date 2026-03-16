# 交易策略回测系统开发计划

## 一、项目概述

基于 daily_stock_analysis 项目，开发完整的交易策略回测系统，包括：
- 时间切片功能
- 交易策略回测
- 自动/手动交易策略
- 交易监控与风险控制
- 可视化展示

## 二、功能模块清单

### 模块 1：时间切片功能

#### 1.1 多时间维度切片
- **分钟级切片**：1分钟、5分钟、15分钟、30分钟、60分钟
- **小时级切片**：1小时、4小时
- **日级切片**：日线、周线、月线 
- **自定义切片**：用户自定义时间范围

#### 1.2 时间切片记录
- 存储每个时间切片的 OHLCV 数据
- 计算技术指标（MA、MACD、RSI、KDJ等）
- 支持切片数据导出

#### 1.3 实现文件
- `src/strategy/time_slice.py` - 时间切片核心逻辑
- `src/strategy/indicators.py` - 技术指标计算
- `api/v1/endpoints/time_slice.py` - API接口

### 模块 2：交易策略回测功能

#### 2.1 回测引擎
- 支持多时间框架回测
- 支持滑点、手续费模拟
- 支持资金曲线计算
- 支持多策略并行回测

#### 2.2 回测参数配置
- 回测时间范围
- 初始资金
- 手续费率
- 滑点设置
- 仓位管理策略

#### 2.3 回测结果记录
- 交易记录（买入/卖出时间、价格、数量）
- 资金曲线
- 收益统计
- 风险指标（最大回撤、夏普比率等）

#### 2.4 实现文件
- `src/strategy/backtest_engine.py` - 回测引擎
- `src/strategy/performance.py` - 绩效分析
- `api/v1/endpoints/backtest.py` - API接口

### 模块 3：交易策略系统

#### 3.1 策略基类
- 策略初始化
- 信号生成
- 参数优化

#### 3.2 预设策略
- **均线策略**：MA5/MA10金叉死叉
- **MACD策略**：DIF/DEA金叉死叉
- **RSI策略**：超买超卖
- **布林带策略**：突破上轨/下轨
- **多因子策略**：组合多个指标

#### 3.3 策略提醒
- 买入提醒（如5日线上穿10日线）
- 卖出提醒（如跌破止损线）
- 支持多渠道推送（微信/邮件）

#### 3.4 自动策略
- 根据预设规则自动执行
- 支持模拟交易和真实交易
- 定时检查信号

#### 3.5 实现文件
- `src/strategy/base.py` - 策略基类
- `src/strategy/strategies/` - 预设策略
  - `ma_strategy.py` - 均线策略
  - `macd_strategy.py` - MACD策略
  - `rsi_strategy.py` - RSI策略
  - `bollinger_strategy.py` - 布林带策略
- `src/strategy/signal_generator.py` - 信号生成器
- `src/strategy/alert_service.py` - 提醒服务

### 模块 4：交易监控功能

#### 4.1 交易记录
- 记录所有交易操作
- 支持交易记录查询、筛选
- 交易记录导出

#### 4.2 持仓监控
- 实时持仓展示
- 持仓盈亏计算
- 持仓占比分析

#### 4.3 风险控制
- 止损设置（固定金额/百分比）
- 止盈设置（固定金额/百分比）
- 最大回撤控制
- 仓位控制

#### 4.4 交易统计
- 总交易次数
- 胜率统计
- 盈亏比
- 最大单笔盈亏
- 平均持仓时间

#### 4.5 实现文件
- `src/monitoring/trade_log.py` - 交易记录
- `src/monitoring/position_tracker.py` - 持仓跟踪
- `src/monitoring/risk_manager.py` - 风险管理
- `src/monitoring/statistics.py` - 统计分析
- `api/v1/endpoints/monitoring.py` - API接口

### 模块 5：可视化功能

#### 5.1 交易图表
- K线图 + 买卖点标记
- 资金曲线图
- 收益分布图

#### 5.2 持仓图表
- 持仓占比饼图
- 持仓盈亏柱状图
- 行业分布图

#### 5.3 回测报告图表
- 回测收益曲线
- 回撤曲线
- 月度收益热力图

#### 5.4 实现文件
- `src/visualization/charts.py` - 图表生成
- `src/visualization/report_generator.py` - 报告生成
- `apps/dsa-web/src/components/charts/` - 前端图表组件

## 三、数据库设计

### 3.1 时间切片表 (time_slices)
```sql
CREATE TABLE time_slices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    timeframe TEXT NOT NULL,  -- 1m, 5m, 1h, 1d, etc.
    timestamp DATETIME NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    amount REAL,
    ma5 REAL,
    ma10 REAL,
    ma20 REAL,
    macd_dif REAL,
    macd_dea REAL,
    rsi REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 策略表 (strategies)
```sql
CREATE TABLE strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    strategy_type TEXT,  -- ma, macd, rsi, etc.
    parameters TEXT,  -- JSON格式
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 3.3 回测记录表 (backtest_records)
```sql
CREATE TABLE backtest_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER,
    stock_code TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    initial_capital REAL,
    final_capital REAL,
    total_return REAL,
    max_drawdown REAL,
    sharpe_ratio REAL,
    win_rate REAL,
    trade_count INTEGER,
    parameters TEXT,  -- JSON格式
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);
```

### 3.4 交易记录表 (trade_records)
```sql
CREATE TABLE trade_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_id INTEGER,
    stock_code TEXT NOT NULL,
    trade_type TEXT,  -- buy, sell
    trade_date DATETIME,
    price REAL,
    quantity INTEGER,
    amount REAL,
    fee REAL,
    signal_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (backtest_id) REFERENCES backtest_records(id)
);
```

### 3.5 持仓记录表 (positions)
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    quantity INTEGER,
    avg_cost REAL,
    current_price REAL,
    market_value REAL,
    profit_loss REAL,
    profit_loss_pct REAL,
    stop_loss_price REAL,
    take_profit_price REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 四、API 接口设计

### 4.1 时间切片接口
```
POST   /api/v1/strategy/time-slice/generate    # 生成时间切片
GET    /api/v1/strategy/time-slice/{stock_code} # 获取时间切片数据
GET    /api/v1/strategy/time-slice/{stock_code}/indicators # 获取技术指标
```

### 4.2 策略接口
```
GET    /api/v1/strategy/strategies              # 获取策略列表
POST   /api/v1/strategy/strategies              # 创建策略
GET    /api/v1/strategy/strategies/{id}         # 获取策略详情
PUT    /api/v1/strategy/strategies/{id}         # 更新策略
DELETE /api/v1/strategy/strategies/{id}         # 删除策略
POST   /api/v1/strategy/strategies/{id}/signals # 生成交易信号
```

### 4.3 回测接口
```
POST   /api/v1/strategy/backtest/run            # 执行回测
GET    /api/v1/strategy/backtest/records        # 获取回测记录
GET    /api/v1/strategy/backtest/records/{id}   # 获取回测详情
GET    /api/v1/strategy/backtest/records/{id}/trades # 获取交易记录
GET    /api/v1/strategy/backtest/records/{id}/chart  # 获取回测图表
```

### 4.4 监控接口
```
GET    /api/v1/strategy/monitoring/positions    # 获取持仓
GET    /api/v1/strategy/monitoring/trades       # 获取交易记录
GET    /api/v1/strategy/monitoring/statistics   # 获取交易统计
GET    /api/v1/strategy/monitoring/risk         # 获取风险指标
```

## 五、测试用例

### 5.1 时间切片测试
- 测试不同时间维度的切片生成
- 测试技术指标计算准确性
- 测试切片数据存储和查询

### 5.2 策略测试
- 测试各预设策略的信号生成
- 测试策略参数优化
- 测试策略提醒功能

### 5.3 回测测试
- 测试回测引擎计算准确性
- 测试绩效指标计算
- 测试多策略并行回测

### 5.4 监控测试
- 测试交易记录存储
- 测试持仓计算
- 测试风险控制触发

### 5.5 可视化测试
- 测试图表生成
- 测试报告导出

## 六、实施步骤

### 阶段 1：基础架构（第1-2周）
1. 创建策略模块目录结构
2. 设计数据库表
3. 实现时间切片功能
4. 实现技术指标计算

### 阶段 2：策略系统（第3-4周）
1. 实现策略基类
2. 实现预设策略（MA、MACD、RSI）
3. 实现信号生成器
4. 实现策略提醒服务

### 阶段 3：回测系统（第5-6周）
1. 实现回测引擎
2. 实现绩效分析
3. 实现回测API
4. 实现回测可视化

### 阶段 4：监控系统（第7-8周）
1. 实现交易记录
2. 实现持仓监控
3. 实现风险控制
4. 实现交易统计

### 阶段 5：可视化（第9-10周）
1. 实现图表生成
2. 实现前端图表组件
3. 实现报告生成
4. 集成测试

## 七、文件清单

### 后端文件
```
src/strategy/
├── __init__.py
├── base.py                 # 策略基类
├── time_slice.py           # 时间切片
├── indicators.py           # 技术指标
├── backtest_engine.py      # 回测引擎
├── performance.py          # 绩效分析
├── signal_generator.py     # 信号生成
├── alert_service.py        # 提醒服务
└── strategies/
    ├── __init__.py
    ├── ma_strategy.py      # 均线策略
    ├── macd_strategy.py    # MACD策略
    ├── rsi_strategy.py     # RSI策略
    └── bollinger_strategy.py # 布林带策略

src/monitoring/
├── __init__.py
├── trade_log.py            # 交易记录
├── position_tracker.py     # 持仓跟踪
├── risk_manager.py         # 风险管理
└── statistics.py           # 统计分析

src/visualization/
├── __init__.py
├── charts.py               # 图表生成
└── report_generator.py     # 报告生成

api/v1/endpoints/
├── time_slice.py           # 时间切片API
├── strategies.py           # 策略API
├── backtest.py             # 回测API
└── monitoring.py           # 监控API
```

### 前端文件
```
apps/dsa-web/src/components/charts/
├── KLineChart.tsx          # K线图
├── EquityCurve.tsx         # 资金曲线
├── PositionPieChart.tsx    # 持仓饼图
├── BacktestReport.tsx      # 回测报告
└── TradeHistoryTable.tsx   # 交易记录表
```

## 八、验收标准

1. 时间切片功能正常，支持多时间维度
2. 至少实现3种预设策略（MA、MACD、RSI）
3. 回测引擎计算准确，绩效指标正确
4. 交易监控功能完整，风险控制有效
5. 可视化图表清晰，报告生成正常
6. 所有功能都有对应的测试用例
7. 代码通过语法检查，符合项目规范
