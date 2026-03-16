# daily_stock_analysis API 文档

## 一、API 概述

- **Base URL**: `http://127.0.0.1:8000/api/v1`
- **认证方式**: 无（当前版本）
- **数据格式**: JSON
- **API 文档**: `http://127.0.0.1:8000/docs` (Swagger UI)

---

## 二、股票分析 API

### 2.1 触发股票分析

**POST** `/analysis/analyze`

启动 AI 智能分析任务，支持同步和异步模式。

#### 请求参数

```json
{
  "stock_code": "AAPL",           // 股票代码（必填）
  "stock_codes": ["AAPL", "TSLA"], // 批量分析（可选）
  "async_mode": true,              // 异步模式（默认 false）
  "force_refresh": false,          // 强制刷新数据
  "report_type": "detailed"        // 报告类型：detailed/simple
}
```

#### 响应

**同步模式 (200)**:
```json
{
  "query_id": "abc123",
  "stock_code": "AAPL",
  "stock_name": "Apple Inc.",
  "report": {
    "meta": { ... },
    "summary": { ... },
    "strategy": { ... }
  },
  "created_at": "2026-02-26T10:00:00"
}
```

**异步模式 (202)**:
```json
{
  "task_id": "task_abc123",
  "status": "pending",
  "message": "分析任务已加入队列: AAPL"
}
```

**重复任务 (409)**:
```json
{
  "error": "duplicate_task",
  "message": "股票 AAPL 正在分析中",
  "stock_code": "AAPL",
  "existing_task_id": "task_xyz"
}
```

---

### 2.2 获取任务列表

**GET** `/analysis/tasks`

获取当前所有分析任务。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 筛选状态：pending, processing, completed, failed |
| limit | int | 否 | 返回数量限制（默认 20，最大 100）|

#### 响应

```json
{
  "total": 10,
  "pending": 2,
  "processing": 1,
  "tasks": [
    {
      "task_id": "task_abc123",
      "stock_code": "AAPL",
      "stock_name": "Apple Inc.",
      "status": "completed",
      "progress": 100,
      "message": "分析完成",
      "created_at": "2026-02-26T10:00:00",
      "completed_at": "2026-02-26T10:05:00"
    }
  ]
}
```

---

### 2.3 查询任务状态

**GET** `/analysis/status/{task_id}`

根据 task_id 查询单个任务的状态。

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务 ID |

#### 响应

```json
{
  "task_id": "task_abc123",
  "status": "completed",
  "progress": 100,
  "result": {
    "query_id": "abc123",
    "stock_code": "AAPL",
    "stock_name": "Apple Inc.",
    "report": { ... }
  },
  "error": null
}
```

---

### 2.4 任务状态 SSE 流

**GET** `/analysis/tasks/stream`

通过 Server-Sent Events 实时推送任务状态变化。

#### 事件类型

| 事件 | 说明 |
|------|------|
| connected | 连接成功 |
| task_created | 新任务创建 |
| task_started | 任务开始执行 |
| task_completed | 任务完成 |
| task_failed | 任务失败 |
| heartbeat | 心跳（每 30 秒）|

#### 响应格式

```
event: task_completed
data: {"task_id": "task_abc123", "status": "completed", ...}

```

---

## 三、股票数据 API

### 3.1 获取实时行情

**GET** `/stocks/{stock_code}/quote`

获取指定股票的最新行情数据。

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| stock_code | string | 股票代码（如 600519、00700、AAPL）|

#### 响应

```json
{
  "stock_code": "AAPL",
  "stock_name": "Apple Inc.",
  "current_price": 264.35,
  "change": 2.5,
  "change_percent": 0.96,
  "open": 262.0,
  "high": 265.0,
  "low": 261.5,
  "prev_close": 261.85,
  "volume": 50000000,
  "amount": 13200000000,
  "update_time": "2026-02-26T10:00:00"
}
```

---

### 3.2 获取历史行情

**GET** `/stocks/{stock_code}/history`

获取指定股票的历史 K 线数据。

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| stock_code | string | 股票代码 |

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| period | string | 否 | K 线周期：daily/weekly/monthly（默认 daily）|
| days | int | 否 | 获取天数（默认 30，最大 365）|

#### 响应

```json
{
  "stock_code": "AAPL",
  "stock_name": "Apple Inc.",
  "period": "daily",
  "data": [
    {
      "date": "2026-02-26",
      "open": 262.0,
      "high": 265.0,
      "low": 261.5,
      "close": 264.35,
      "volume": 50000000,
      "amount": 13200000000,
      "change_percent": 0.96
    }
  ]
}
```

---

### 3.3 从图片提取股票代码

**POST** `/stocks/extract-from-image`

上传截图/图片，通过 Vision LLM 提取股票代码。

#### 请求

- **Content-Type**: `multipart/form-data`
- **文件限制**: JPEG、PNG、WebP、GIF，最大 5MB

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 图片文件 |
| include_raw | bool | 否 | 是否包含原始 LLM 响应 |

#### 响应

```json
{
  "codes": ["AAPL", "TSLA", "NVDA"],
  "raw_text": "从图片中识别到以下股票代码..."
}
```

---

## 四、历史记录 API

### 4.1 获取分析历史

**GET** `/history/analysis`

获取历史分析记录。

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| stock_code | string | 否 | 股票代码筛选 |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |
| limit | int | 否 | 返回数量限制 |

#### 响应

```json
{
  "total": 100,
  "records": [
    {
      "query_id": "abc123",
      "stock_code": "AAPL",
      "stock_name": "Apple Inc.",
      "sentiment_score": 65,
      "operation_advice": "持有",
      "trend_prediction": "看多",
      "created_at": "2026-02-26T10:00:00"
    }
  ]
}
```

---

## 五、回测 API

### 5.1 获取回测结果

**GET** `/backtest/results`

获取历史回测结果。

#### 响应

```json
{
  "total": 50,
  "results": [
    {
      "stock_code": "AAPL",
      "total_predictions": 10,
      "correct_predictions": 7,
      "accuracy": 0.7,
      "avg_return": 0.05
    }
  ]
}
```

---

## 六、系统配置 API

### 6.1 获取系统配置

**GET** `/system/config`

获取当前系统配置。

#### 响应

```json
{
  "ai_model": "deepseek-chat",
  "stock_list": ["AAPL", "TSLA", "NVDA"],
  "notification_channels": ["serverchan3"],
  "proxy_enabled": true
}
```

---

## 七、健康检查 API

### 7.1 健康检查

**GET** `/health`

检查服务状态。

#### 响应

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600
}
```

---

## 八、错误响应格式

所有 API 错误响应遵循统一格式：

```json
{
  "error": "error_code",
  "message": "错误描述信息"
}
```

### 常见错误码

| HTTP 状态码 | 错误码 | 说明 |
|-------------|--------|------|
| 400 | validation_error | 请求参数错误 |
| 400 | unsupported_type | 不支持的文件类型 |
| 400 | file_too_large | 文件超过大小限制 |
| 404 | not_found | 资源不存在 |
| 409 | duplicate_task | 重复任务 |
| 422 | unsupported_period | 不支持的周期参数 |
| 500 | internal_error | 服务器内部错误 |
