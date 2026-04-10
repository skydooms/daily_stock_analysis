# 监控脚本改进计划

## 需求概述

改进 `start_monitoring_03759.py` 脚本：

1. 使用 argparse 支持添加多只股票监控
2. 启动监控时推送消息给机器人
3. 记录监控日志时，将股票时间转换为国内时间，以便对比延迟时间
4. 添加美股阿里巴巴(BABA)、甲骨文(ORCL)、美光科技(MU)进行监控

## 实现步骤

### 1. 重命名脚本文件

* 将 `start_monitoring_03759.py` 重命名为 `start_stock_monitor.py`（更通用的名称）

### 2. 添加 argparse 命令行参数

```python
parser = argparse.ArgumentParser(description='股票实时监控脚本')
parser.add_argument('--stocks', '-s', nargs='+', help='股票代码列表，如: 03759.HK ORCL BABA')
parser.add_argument('--type', '-t', choices=['realtime', 'simulation'], default='realtime', help='监控类型')
parser.add_argument('--interval', '-i', type=int, default=30, help='监控间隔(秒)')
parser.add_argument('--window', '-w', type=int, default=10, help='时间窗口(分钟)')
parser.add_argument('--level1', type=float, default=3.5, help='一级阈值(%)')
parser.add_argument('--level2', type=float, default=2.0, help='二级阈值(%)')
parser.add_argument('--level3', type=float, default=0.2, help='三级阈值(%)')
parser.add_argument('--chat-id', type=str, help='飞书 chat_id')
parser.add_argument('--notify-start', action='store_true', help='启动时发送通知')
```

### 3. 启动监控时推送消息

在监控引擎启动后，发送一条启动通知到飞书机器人：

* 标题：🚀 股票监控已启动

* 内容：监控的股票列表、监控参数、启动时间

### 4. 时间转换优化

在监控日志中，将股票行情时间转换为国内时间（UTC+8）：

* 获取行情数据时记录原始时间戳

* 转换为北京时间显示

* 计算并显示延迟时间（当前时间 - 行情时间）

### 5. 默认监控股票

如果不指定 `--stocks` 参数，默认监控：

* 港股：03759.HK (康龙化成)

* 美股：BABA (阿里巴巴), ORCL (甲骨文), MU (美光科技)

## 文件修改

### 修改文件

1. `start_monitoring_03759.py` → 重命名为 `start_stock_monitor.py`
2. `src/monitor/engine.py` - 添加启动通知和时区转换日志

### 新增功能

* 启动通知发送函数

* 时区转换工具函数

* 延迟时间计算

## 使用示例

```bash
# 使用默认股票列表
python start_stock_monitor.py --notify-start

# 指定股票列表
python start_stock_monitor.py -s 03759.HK ORCL BABA MU --notify-start

# 模拟监控模式
python start_stock_monitor.py -s 03759.HK ORCL --type simulation

# 自定义参数
python start_stock_monitor.py -s 03759.HK ORCL BABA MU \
    --interval 30 \
    --window 5 \
    --level1 3.0 \
    --level2 1.5 \
    --notify-start
```

## 预期输出

```
============================================================
🚀 股票监控已启动
============================================================
监控股票: 康龙化成(03759.HK), 阿里巴巴(BABA), 甲骨文(ORCL), 美光科技(MU)
监控类型: realtime
监控间隔: 60秒
时间窗口: 10分钟
阈值: L1=3.5%, L2=2.0%, L3=0.5%
启动时间: 2026-03-19 08:30:00 CST
============================================================

[检查] 03759.HK 康龙化成
  行情时间: 2026-03-19 08:29:58 CST (延迟: 2秒)
  当前价格: 19.70 HKD
  今日涨跌: +1.81%
  窗口涨跌: +0.52%
  状态: 正常

[检查] ORCL 甲骨文
  行情时间: 2026-03-19 08:29:55 CST (延迟: 5秒)
  当前价格: 153.10 USD
  今日涨跌: -0.35%
  窗口涨跌: +0.12%
  状态: 正常
...
```

