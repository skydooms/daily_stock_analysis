# 股票监控系统测试计划

## 📋 测试目标

系统性测试 `start_stock_monitor_v2.py` 的 Level1-Level3 预警触发功能，验证：
- Level1（今日涨跌幅 >= 3.5%）预警正常触发
- Level2（今日涨跌幅 >= 2.0%）预警正常触发
- Level3（窗口涨跌幅 >= 0.1%）预警正常触发
- 预警只触发一次（防止重复预警）
- 飞书通知正常发送

---

## 🛠️ 测试环境准备

### 1. 检查代码文件

- ✅ `start_stock_monitor_v2.py` 已存在
- ✅ 股票映射表包含测试股票：
  - 300759：康龙化成
  - 03759.HK：康龙化成
  - 300418：昆仑万维

### 2. 配置检查

- ✅ 飞书配置已正确设置
  - `FEISHU_APP_ID=cli_a924f365e2f89cc0`
  - `FEISHU_APP_SECRET=Fq1fQ3kyEoa6zneJHbtsuA3kQKiybVyt`
  - `FEISHU_CHAT_ID=oc_c4f728163782081095ba208e2cd0ae3e`

### 3. 测试脚本创建

创建 `test_monitor_trigger.py` 用于模拟测试。

---

## 🧪 测试用例

### 测试用例 1：Level3 预警触发（窗口涨跌幅）

**目标**：验证 Level3（窗口涨跌幅 >= 0.1%）预警正常触发

**测试步骤**：
1. 启动监控：`python3 start_stock_monitor_v2.py -s 300759 --level3 0.1 --feishu-on --notify-start`
2. 观察日志输出
3. 等待实时行情波动
4. 验证 Level3 预警是否发送到飞书
5. 验证是否只触发一次

**预期结果**：
- 启动时发送启动通知
- 当 300759 窗口涨跌幅 >= 0.1% 时，发送 Level3 预警
- 🟡 三级预警，内容包含：
  - 康龙化成 (300759)
  - 涨/跌幅 > 0.1%
  - 当前价格
  - 监控窗口（10分钟）

---

### 测试用例 2：Level2 预警触发（今日涨跌幅）

**目标**：验证 Level2（今日涨跌幅 >= 2.0%）预警正常触发

**测试步骤**：
1. 启动监控：`python3 start_stock_monitor_v2.py -s 300418 --level2 2.0 --feishu-on --notify-start`
2. 观察日志输出
3. 等待实时行情
4. 验证 Level2 预警是否发送

**预期结果**：
- 当 300418 今日涨跌幅 >= 2.0% 时，发送 Level2 预警
- 🟠 二级预警，内容包含：
  - 昆仑万维 (300418)
  - 涨/跌幅 > 2.0%
  - 当前价格

---

### 测试用例 3：Level1 预警触发（今日涨跌幅）

**目标**：验证 Level1（今日涨跌幅 >= 3.5%）预警正常触发

**测试步骤**：
1. 启动监控：`python3 start_stock_monitor_v2.py -s 03759.HK --level1 3.5 --feishu-on --notify-start`
2. 观察日志输出
3. 等待实时行情
4. 验证 Level1 预警是否发送

**预期结果**：
- 当 03759.HK 今日涨跌幅 >= 3.5% 时，发送 Level1 预警
- 🔴 一级预警，内容包含：
  - 康龙化成 (03759.HK)
  - 涨/跌幅 > 3.5%
  - 当前价格

---

### 测试用例 4：多股票同时监控

**目标**：验证同时监控多只股票的预警功能

**测试步骤**：
1. 启动监控：`python3 start_stock_monitor_v2.py -s 300759 03759.HK 300418 --level3 0.1 --feishu-on --notify-start`
2. 观察 3 只股票的监控状态
3. 验证各股票的预警是否正确触发

**预期结果**：
- 启动时显示 3 只股票的启动通知
- 各股票独立触发预警，互相不影响

---

### 测试用例 5：预警去重（只触发一次）

**目标**：验证同一级别预警只触发一次

**测试步骤**：
1. 启动监控并等待 Level3 预警触发
2. 继续观察，验证是否重复发送

**预期结果**：
- Level3 预警只触发一次
- 窗口重置后，重新监控（`alert_level3_triggered` 重置为 False）

---

## 📊 测试记录模板

### 测试结果记录表

| 测试用例 | 测试时间 | 结果（✅/❌） | 备注 | 飞书通知截图 |
|----------|----------|--------------|------|--------------|
| 1. Level3 触发 | | | | |
| 2. Level2 触发 | | | | |
| 3. Level1 触发 | | | | |
| 4. 多股票监控 | | | | |
| 5. 预警去重 | | | | |

---

## 🔍 关键检查点

### 代码逻辑检查

1. **预警条件判断**（`_check_alerts`）：
   ```python
   # Level 1: 今日涨跌幅
   if abs_today >= config.level1_threshold and not state.alert_level1_triggered:
   
   # Level 2: 今日涨跌幅
   if abs_today >= config.level2_threshold and not state.alert_level2_triggered:
   
   # Level 3: 窗口涨跌幅
   if abs_window >= config.level3_threshold and not state.alert_level3_triggered:
   ```

2. **窗口重置逻辑**（`_check_single_monitor`）：
   ```python
   # 检查是否需要重置窗口
   if window_elapsed >= config.window_minutes:
       state.window_start_price = current_price
       state.window_start_time = now
       state.alert_level3_triggered = False  # 重置 Level3 预警标志
   ```

3. **预警发送格式**（`_send_alert`）：
   - 标题：`{icon} {level_name} {stock_name}({stock_code}) {direction}`
   - 内容包含：股票名称、代码、涨跌幅、预警级别、当前价格、触发时间

### 飞书通知检查

- ✅ 同时显示股票代码和名称
- ✅ 预警级别图标正确（🔴🟠🟡）
- ✅ 消息格式符合 Markdown 规范

---

## 🚀 执行测试

### 快速测试命令

```bash
# 测试 1：Level3（0.1%）
python3 start_stock_monitor_v2.py -s 300759 --level3 0.1 --feishu-on --notify-start

# 测试 2：Level2（2.0%）
python3 start_stock_monitor_v2.py -s 300418 --level2 2.0 --feishu-on --notify-start

# 测试 3：Level1（3.5%）
python3 start_stock_monitor_v2.py -s 03759.HK --level1 3.5 --feishu-on --notify-start

# 测试 4：多股票
python3 start_stock_monitor_v2.py -s 300759 03759.HK 300418 --level3 0.1 --feishu-on --notify-start
```

### 日志检查命令

```bash
# 查看运行日志
tail -f logs/stock_monitor_v2*.log
```

---

## ⚠️ 注意事项

1. **实时行情依赖**：预警触发依赖真实的股票行情波动，无法在测试时人工强制触发
2. **等待时间**：需要等待市场交易时间，股票价格波动
3. **预警去重**：同一级别的预警在一个窗口内只触发一次
4. **飞书通知**：确保飞书群聊机器人已添加且权限正确
