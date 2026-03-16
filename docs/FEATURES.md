# daily_stock_analysis 功能说明文档

## 一、核心功能概述

### 1.1 功能列表

| 功能模块 | 说明 |
|----------|------|
| 股票分析 | AI 驱动的多维度股票分析 |
| 决策仪表盘 | 一句话核心结论 + 买卖点位 |
| 大盘复盘 | 每日市场概览和板块分析 |
| 消息推送 | 多渠道通知推送 |
| 回测验证 | 历史分析准确率评估 |
| Web API | RESTful API 接口 |
| Web UI | React 前端界面 |

---

## 二、股票分析功能

### 2.1 实现原理

股票分析采用流水线架构，流程如下：

```
1. 数据获取
   ├── 历史行情（OHLCV）
   ├── 实时行情
   ├── 筹码分布
   └── 新闻资讯

2. 数据处理
   ├── 技术指标计算（MA、MACD、RSI等）
   ├── 均线形态识别
   └── 量价分析

3. AI 分析
   ├── 构建 Prompt
   ├── 调用 LLM API
   └── 解析响应 JSON

4. 结果输出
   ├── 决策仪表盘
   ├── 操作建议
   └── 风险提示
```

### 2.2 使用方法

**命令行方式：**
```bash
cd d:\project\daily_stock_analysis
.\venv\Scripts\python.exe main.py
```

**API 方式：**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{"stock_code": "AAPL", "async_mode": false}'
```

### 2.3 配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| STOCK_LIST | 监控股票列表 | - |
| MAX_WORKERS | 并发工作线程数 | 3 |
| ANALYSIS_DELAY | 分析间隔（秒）| 0 |

---

## 三、AI 分析功能

### 3.1 实现原理

AI 分析使用大语言模型（LLM）进行股票分析：

1. **Prompt 构建**：将股票数据格式化为 Markdown 表格
2. **LLM 调用**：支持 DeepSeek、Gemini、OpenAI 等
3. **响应解析**：解析 JSON 格式的分析结果

### 3.2 支持的 AI 模型

| 模型 | 配置方式 | 说明 |
|------|----------|------|
| GLM-5 | OPENAI_API_KEY + OPENAI_BASE_URL | 默认模型，智谱 AI |
| DeepSeek | OPENAI_API_KEY + OPENAI_BASE_URL | 推荐，性价比高 |
| Gemini | GEMINI_API_KEY | 免费，有配额限制 |
| OpenAI | OPENAI_API_KEY | 官方 API |
| Claude | ANTHROPIC_API_KEY | 高质量分析 |

### 3.3 分析输出

```json
{
  "stock_name": "Apple Inc.",
  "sentiment_score": 65,
  "trend_prediction": "看多",
  "operation_advice": "持有",
  "decision_type": "hold",
  "confidence_level": "中",
  "dashboard": {
    "core_conclusion": {
      "one_sentence": "短期震荡，中期看多，建议持有。"
    },
    "strategy": {
      "ideal_buy": "260.00",
      "stop_loss": "255.00",
      "take_profit": "280.00"
    }
  }
}
```

---

## 四、数据源功能

### 4.1 支持的数据源

| 数据源 | 市场 | 数据类型 | 配置优先级 |
|--------|------|----------|------------|
| YFinance | 美股/港股 | 历史+实时 | YFINANCE_PRIORITY |
| AkShare | A股 | 历史+实时 | AKSHARE_PRIORITY |
| EFinance | A股/港股 | 历史+实时 | EFINANCE_PRIORITY |
| Tushare | A股 | 历史 | TUSHARE_PRIORITY |
| Baostock | A股 | 历史 | BAOSTOCK_PRIORITY |
| PyTDX | A股 | 实时 | PYTDX_PRIORITY |

### 4.2 数据获取流程

```python
# data_provider/base.py
class BaseFetcher:
    def get_history_data(self, stock_code, start_date, end_date):
        """获取历史数据"""
        pass
    
    def get_realtime_quote(self, stock_code):
        """获取实时行情"""
        pass
    
    def get_chip_distribution(self, stock_code):
        """获取筹码分布"""
        pass
```

### 4.3 代理配置

对于需要代理访问的数据源（如 YFinance）：

```env
USE_PROXY=true
PROXY_HOST=127.0.0.1
PROXY_PORT=1087
```

---

## 五、消息推送功能

### 5.1 支持的推送渠道

| 渠道 | 配置项 | 说明 |
|------|--------|------|
| Server酱3 | SERVERCHAN3_SENDKEY | 推送到微信 |
| PushPlus | PUSHPLUS_TOKEN | 推送到微信 |
| 企业微信 | WECHAT_WEBHOOK_URL | 群机器人 |
| 飞书 | FEISHU_WEBHOOK_URL | 群机器人 |
| Telegram | TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID | Bot 推送 |
| 邮件 | EMAIL_SENDER + EMAIL_PASSWORD | SMTP 邮件 |

### 5.2 推送流程

```
分析完成 → 生成报告 → 格式化 Markdown → 推送到各渠道
```

### 5.3 使用示例

```env
# Server酱3 推送配置
SERVERCHAN3_SENDKEY=sctp16841tewpfgttcdekty3qknsbgjm
```

---

## 六、回测功能

### 6.1 实现原理

回测功能用于验证历史分析的准确率：

1. 获取历史分析记录
2. 对比预测与实际走势
3. 计算胜率和收益率

### 6.2 回测指标

| 指标 | 说明 |
|------|------|
| 方向胜率 | 预测涨跌方向的准确率 |
| 止盈命中率 | 达到目标价的比率 |
| 止损命中率 | 触发止损的比率 |
| 平均收益 | 平均收益率 |

### 6.3 使用方法

```bash
# 运行回测
python main.py --backtest
```

---

## 七、定时任务功能

### 7.1 实现原理

使用 Python `schedule` 库实现定时任务：

```python
# src/scheduler.py
import schedule

def run_analysis():
    """执行分析任务"""
    pass

# 每个交易日 15:30 执行
schedule.every().day.at("15:30").do(run_analysis)
```

### 7.2 配置项

```env
SCHEDULE_ENABLED=true
SCHEDULE_TIME=15:30
```

---

## 八、Web API 功能

### 8.1 实现原理

使用 FastAPI 框架提供 RESTful API：

```python
# api/app.py
from fastapi import FastAPI

app = FastAPI(title="Stock Analysis API")

@app.post("/api/v1/analysis/analyze")
def analyze(request: AnalyzeRequest):
    """股票分析接口"""
    pass
```

### 8.2 启动方式

```bash
# 启动 Web 服务
python webui.py

# 访问 API 文档
# http://127.0.0.1:8000/docs
```

---

## 九、Web UI 功能

### 9.1 实现原理

前端使用 React + Vite 构建：

```
apps/dsa-web/
├── src/
│   ├── components/    # UI 组件
│   ├── pages/         # 页面
│   ├── services/      # API 服务
│   └── App.tsx        # 主应用
└── package.json
```

### 9.2 构建和运行

```bash
# 安装依赖
cd apps/dsa-web
npm install

# 构建
npm run build

# 启动服务
cd ../..
python webui.py
```

---

## 十、扩展功能

### 10.1 添加新数据源

1. 在 `data_provider/` 创建新的 fetcher 文件
2. 继承 `BaseFetcher` 类
3. 实现必要的方法
4. 在配置中添加优先级

### 10.2 添加新推送渠道

1. 在 `src/notification.py` 添加新的渠道类型
2. 实现发送方法
3. 在配置中添加相关配置项

### 10.3 添加新 AI 模型

1. 在 `src/analyzer.py` 添加模型支持
2. 配置 API Key 和 Base URL
3. 测试分析效果
