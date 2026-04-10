# 持仓股票实时监控功能实现计划

## 需求概述

设计一个持仓股票实时监控功能：
1. 监控用户持仓的股票，包括股票代码、股票名称
2. 触发条件：
   - 10分钟内涨跌幅超过正负1%
   - 涨跌幅超过正负2%时通知用户
3. 功能分为实时监控和模拟监控两部分

## 技术方案

### 1. 数据模型设计

#### 1.1 监控配置表 (stock_monitor_config)
存储用户的监控配置：
- `id`: 主键
- `stock_code`: 股票代码
- `stock_name`: 股票名称
- `user_id`: 用户ID（飞书 open_id）
- `chat_id`: 会话ID（用于发送通知）
- `monitor_type`: 监控类型 (realtime/simulation)
- `threshold_1pct_enabled`: 是否启用1%阈值监控
- `threshold_2pct_enabled`: 是否启用2%阈值监控
- `window_minutes`: 时间窗口（默认10分钟）
- `is_active`: 是否启用
- `created_at`: 创建时间
- `updated_at`: 更新时间

#### 1.2 监控状态表 (stock_monitor_state)
存储实时监控状态：
- `id`: 主键
- `config_id`: 关联配置ID
- `stock_code`: 股票代码
- `baseline_price`: 基准价格（窗口起始价）
- `baseline_time`: 基准时间
- `last_price`: 最新价格
- `last_change_pct`: 最新涨跌幅
- `last_check_time`: 最后检查时间
- `alert_1pct_triggered`: 1%阈值是否已触发
- `alert_2pct_triggered`: 2%阈值是否已触发
- `updated_at`: 更新时间

#### 1.3 告警历史表 (stock_monitor_alert)
存储告警历史：
- `id`: 主键
- `config_id`: 关联配置ID
- `stock_code`: 股票代码
- `alert_type`: 告警类型 (threshold_1pct/threshold_2pct)
- `change_pct`: 触发时的涨跌幅
- `price`: 触发时的价格
- `alert_time`: 告警时间
- `notified`: 是否已通知
- `created_at`: 创建时间

### 2. 核心模块设计

#### 2.1 监控服务 (src/services/stock_monitor_service.py)
- `StockMonitorService`: 监控服务主类
  - `add_monitor()`: 添加监控
  - `remove_monitor()`: 移除监控
  - `list_monitors()`: 列出监控列表
  - `start_monitoring()`: 启动监控循环
  - `stop_monitoring()`: 停止监控
  - `check_thresholds()`: 检查阈值触发
  - `send_alert()`: 发送告警通知

#### 2.2 监控引擎 (src/monitor/monitor_engine.py)
- `MonitorEngine`: 监控引擎
  - `run()`: 主循环
  - `check_stock()`: 检查单只股票
  - `update_baseline()`: 更新基准价格
  - `reset_alert_flags()`: 重置告警标志

#### 2.3 飞书命令处理器 (bot/commands/monitor.py)
- `/monitor add <股票代码>`: 添加监控
- `/monitor remove <股票代码>`: 移除监控
- `/monitor list`: 列出监控列表
- `/monitor start`: 启动监控
- `/monitor stop`: 停止监控
- `/monitor simulate`: 模拟监控模式

### 3. 配置项设计

新增环境变量：
```
# 股票监控配置
STOCK_MONITOR_ENABLED=false          # 是否启用股票监控
STOCK_MONITOR_INTERVAL_SECONDS=60    # 监控轮询间隔（秒）
STOCK_MONITOR_DEFAULT_WINDOW=10      # 默认时间窗口（分钟）
STOCK_MONITOR_THRESHOLD_1PCT=1.0     # 一级阈值（%）
STOCK_MONITOR_THRESHOLD_2PCT=2.0     # 二级阈值（%）
```

### 4. 实现步骤

#### 第一阶段：数据层
1. 创建数据库迁移脚本，添加监控相关表
2. 创建数据模型类 (models)
3. 创建数据访问层 (repository)

#### 第二阶段：服务层
1. 实现 `StockMonitorService` 核心服务
2. 实现 `MonitorEngine` 监控引擎
3. 集成实时行情获取 (`DataFetcherManager.get_realtime_quote`)
4. 集成飞书通知 (`FeishuReplyClient.send_to_chat`)

#### 第三阶段：命令层
1. 实现 `/monitor` 命令处理器
2. 注册命令到 `dispatcher`
3. 更新帮助文档

#### 第四阶段：配置与文档
1. 更新 `.env.example`
2. 更新 `src/config.py`
3. 更新 `README.md`

### 5. 文件结构

```
src/
├── services/
│   └── stock_monitor_service.py    # 监控服务
├── monitor/
│   ├── __init__.py
│   ├── engine.py                   # 监控引擎
│   └── models.py                   # 数据模型
├── repositories/
│   └── stock_monitor_repo.py       # 数据访问层
bot/
└── commands/
    └── monitor.py                  # 监控命令处理器
```

### 6. 关键技术点

#### 6.1 涨跌幅计算
```python
change_pct = (current_price - baseline_price) / baseline_price * 100
```

#### 6.2 时间窗口滑动
- 每隔 `window_minutes` 分钟重置基准价格
- 基准价格为窗口起始时刻的最新成交价

#### 6.3 告警去重
- 使用 `alert_1pct_triggered` 和 `alert_2pct_triggered` 标志
- 当涨跌幅回归到阈值内时重置标志

#### 6.4 模拟监控
- 与实时监控逻辑相同
- 不发送实际通知，只记录日志

### 7. 风险与降级

1. **数据源故障**: 使用 `DataFetcherManager` 的多数据源故障切换
2. **通知失败**: 记录日志，下次检查时重试
3. **性能问题**: 使用异步处理，限制并发监控数量

### 8. 测试计划

1. 单元测试：阈值计算、告警触发逻辑
2. 集成测试：监控流程端到端测试
3. 模拟测试：模拟监控模式验证

## 实现优先级

1. **P0 - 核心功能**
   - 数据模型与存储
   - 监控服务核心逻辑
   - 飞书通知集成

2. **P1 - 命令交互**
   - `/monitor` 命令处理器
   - 监控列表管理

3. **P2 - 增强功能**
   - 模拟监控模式
   - 监控统计与历史
