# daily_stock_analysis 项目架构文档

## 一、项目概述

daily_stock_analysis 是一个基于 AI 大模型的 A股/港股/美股智能分析系统。

### 核心功能
- 多维度股票分析（技术面 + 筹码分布 + 舆情情报 + 实时行情）
- AI 决策仪表盘生成
- 多渠道消息推送
- 定时任务调度
- Web API 和 Web UI

---

## 二、目录结构

```
d:\project\daily_stock_analysis\
├── api/                          # FastAPI Web API 模块
│   ├── middlewares/              # 中间件
│   │   ├── __init__.py
│   │   └── error_handler.py      # 全局错误处理中间件
│   ├── v1/                       # API v1 版本
│   │   ├── endpoints/            # API 端点
│   │   │   ├── analysis.py       # 股票分析 API
│   │   │   ├── backtest.py       # 回测 API
│   │   │   ├── health.py         # 健康检查 API
│   │   │   ├── history.py        # 历史记录 API
│   │   │   ├── stocks.py         # 股票数据 API
│   │   │   └── system_config.py  # 系统配置 API
│   │   ├── schemas/              # Pydantic 数据模型
│   │   │   ├── analysis.py       # 分析请求/响应模型
│   │   │   ├── backtest.py       # 回测请求/响应模型
│   │   │   ├── common.py         # 通用模型
│   │   │   ├── history.py        # 历史记录模型
│   │   │   ├── stocks.py         # 股票数据模型
│   │   │   └── system_config.py  # 系统配置模型
│   │   └── router.py             # API 路由聚合
│   ├── app.py                    # FastAPI 应用实例
│   └── deps.py                   # 依赖注入
│
├── apps/                         # 前端应用
│   ├── dsa-desktop/              # Electron 桌面应用
│   └── dsa-web/                  # React Web 应用
│
├── bot/                          # 机器人模块
│   ├── commands/                 # 命令处理
│   │   ├── analyze.py            # 分析命令
│   │   ├── batch.py              # 批量分析命令
│   │   ├── help.py               # 帮助命令
│   │   ├── market.py             # 市场概览命令
│   │   └── status.py             # 状态命令
│   ├── platforms/                # 平台适配
│   │   ├── dingtalk.py           # 钉钉平台
│   │   ├── dingtalk_stream.py    # 钉钉流式消息
│   │   ├── discord.py            # Discord 平台
│   │   └── feishu_stream.py      # 飞书流式消息
│   ├── dispatcher.py             # 命令分发器
│   ├── handler.py                # 消息处理器
│   └── models.py                 # 机器人数据模型
│
├── data_provider/                # 数据源模块
│   ├── base.py                   # 数据源基类
│   ├── akshare_fetcher.py        # AkShare 数据源（A股）
│   ├── baostock_fetcher.py       # Baostock 数据源（A股）
│   ├── efinance_fetcher.py       # EFinance 数据源（A股/港股）
│   ├── pytdx_fetcher.py          # PyTDX 数据源（A股实时）
│   ├── tushare_fetcher.py        # Tushare 数据源（A股）
│   ├── yfinance_fetcher.py       # YFinance 数据源（美股/港股）
│   ├── realtime_types.py         # 实时数据类型定义
│   └── us_index_mapping.py       # 美股指数映射
│
├── src/                          # 核心模块
│   ├── core/                     # 核心逻辑
│   │   ├── backtest_engine.py    # 回测引擎
│   │   ├── config_manager.py     # 配置管理器
│   │   ├── config_registry.py    # 配置注册表
│   │   ├── market_review.py      # 大盘复盘
│   │   └── pipeline.py           # 分析流水线
│   ├── repositories/             # 数据仓库层
│   │   ├── analysis_repo.py      # 分析记录仓库
│   │   ├── backtest_repo.py      # 回测记录仓库
│   │   └── stock_repo.py         # 股票数据仓库
│   ├── services/                 # 业务服务层
│   │   ├── analysis_service.py   # 分析服务
│   │   ├── backtest_service.py   # 回测服务
│   │   ├── history_service.py    # 历史服务
│   │   ├── image_stock_extractor.py  # 图片股票提取
│   │   ├── stock_service.py      # 股票服务
│   │   ├── system_config_service.py  # 系统配置服务
│   │   ├── task_queue.py         # 任务队列
│   │   └── task_service.py       # 任务服务
│   ├── analyzer.py               # AI 分析器
│   ├── config.py                 # 配置加载
│   ├── enums.py                  # 枚举定义
│   ├── feishu_doc.py             # 飞书文档
│   ├── formatters.py             # 格式化工具
│   ├── logging_config.py         # 日志配置
│   ├── market_analyzer.py        # 市场分析器
│   ├── md2img.py                 # Markdown 转图片
│   ├── notification.py           # 通知推送
│   ├── scheduler.py              # 定时调度
│   ├── search_service.py         # 搜索服务
│   ├── stock_analyzer.py         # 股票分析器
│   └── storage.py                # 数据存储
│
├── tests/                        # 测试文件
├── patch/                        # 补丁模块
├── .github/                      # GitHub 配置
├── main.py                       # 主入口
├── webui.py                      # Web UI 入口
├── server.py                     # 服务器入口
├── test_env.py                   # 环境测试
└── requirements.txt              # 依赖列表
```

---

## 三、核心模块说明

### 3.1 数据源模块 (data_provider/)

| 文件 | 功能 | 支持市场 |
|------|------|----------|
| base.py | 数据源基类，定义统一接口 | - |
| akshare_fetcher.py | AkShare 数据获取 | A股 |
| baostock_fetcher.py | Baostock 数据获取 | A股 |
| efinance_fetcher.py | EFinance 数据获取 | A股/港股 |
| pytdx_fetcher.py | PyTDX 实时数据 | A股 |
| tushare_fetcher.py | Tushare 数据获取 | A股 |
| yfinance_fetcher.py | YFinance 数据获取 | 美股/港股 |

### 3.2 核心模块 (src/core/)

| 文件 | 功能 |
|------|------|
| pipeline.py | 分析流水线，协调数据获取、分析、推送 |
| backtest_engine.py | 回测引擎，验证历史分析准确率 |
| config_manager.py | 配置管理，动态加载和更新配置 |
| market_review.py | 大盘复盘，生成市场概览报告 |

### 3.3 服务层 (src/services/)

| 文件 | 功能 |
|------|------|
| analysis_service.py | 分析服务，封装分析逻辑 |
| stock_service.py | 股票服务，股票数据管理 |
| backtest_service.py | 回测服务，回测任务管理 |
| history_service.py | 历史服务，历史记录查询 |
| task_service.py | 任务服务，异步任务管理 |

### 3.4 通知模块 (src/notification.py)

支持的通知渠道：
- 企业微信 (WECHAT)
- 飞书 (FEISHU)
- Telegram (TELEGRAM)
- 邮件 (EMAIL)
- Pushover (PUSHOVER)
- PushPlus (PUSHPLUS)
- Server酱3 (SERVERCHAN3)
- Discord (DISCORD)
- 自定义 Webhook (CUSTOM)

---

## 四、数据流

```
用户请求 → main.py
    ↓
pipeline.py (分析流水线)
    ↓
data_provider/ (获取股票数据)
    ↓
analyzer.py (AI 分析)
    ↓
notification.py (推送结果)
    ↓
用户接收结果
```

---

## 五、配置文件

配置文件 `.env` 包含以下主要配置项：

| 配置项 | 说明 |
|--------|------|
| OPENAI_API_KEY | AI 模型 API Key |
| OPENAI_BASE_URL | AI 模型 API 地址 |
| OPENAI_MODEL | AI 模型名称 |
| STOCK_LIST | 监控股票列表 |
| SERVERCHAN3_SENDKEY | Server酱3 推送 Key |
| USE_PROXY | 是否使用代理 |
| PROXY_HOST | 代理地址 |
| PROXY_PORT | 代理端口 |

---

## 六、依赖关系

```
main.py
  ├── src/core/pipeline.py
  │     ├── data_provider/base.py
  │     ├── src/analyzer.py
  │     └── src/notification.py
  ├── src/storage.py
  └── src/scheduler.py

api/app.py
  ├── api/v1/router.py
  │     └── api/v1/endpoints/*.py
  └── api/middlewares/error_handler.py
```
