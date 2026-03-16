# 安装 OpenClaw 并切换为 DeepSeek 模型

## 任务概述

1. 安装 OpenClaw（通过 npm 全局安装）
2. 配置项目使用 DeepSeek 模型进行 AI 分析

## 背景说明

* **OpenClaw**：是一个独立的开源应用程序（非 PyPI Python 库），需要通过 npm 安装。它依赖 Node.js 和 Python 3.8+ 环境。

* **DeepSeek 模型**：项目已支持 DeepSeek，通过 OpenAI 兼容 API 配置。

***

## 实施步骤

### 步骤 1：安装 OpenClaw

通过 npm 全局安装 OpenClaw：

```bash
npm install -g openclaw
```

**验证安装**：

```bash
openclaw --version
```

### 步骤 2：检查当前 .env 配置

读取项目根目录的 `.env` 文件，检查当前的 AI 模型配置。

### 步骤 3：配置 DeepSeek 模型

在 `.env` 文件中配置以下环境变量（如果已存在则修改，不存在则添加）：

```bash
# DeepSeek 模型配置（OpenAI 兼容 API）
OPENAI_API_KEY=sk-5fe54fd1d48e4618ae85927a12ab8dad
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
OPENAI_TEMPERATURE=0.7
```

**注意事项**：

* `OPENAI_API_KEY`：需要用户从 DeepSeek 官网获取 API Key

* `OPENAI_BASE_URL`：固定为 `https://api.deepseek.com/v1`

* `OPENAI_MODEL`：推荐使用 `deepseek-chat`（聊天模型）或 `deepseek-coder`（代码模型）

* 如果不需要其他 AI 模型，可以注释掉 `GEMINI_API_KEY` 和 `ANTHROPIC_API_KEY`

### 步骤 4：验证配置

运行配置验证脚本，确保配置正确：

```bash
python src/config.py
```

### 步骤 5：测试运行（可选）

如果用户已配置 DeepSeek API Key，可以运行一次测试：

```bash
python main.py
```

***

## 配置优先级说明

根据项目代码（`src/config.py`），AI 模型的优先级为：

1. **Gemini**（优先级最高）
2. **Anthropic Claude**
3. **OpenAI 兼容 API**（包括 DeepSeek）

如果需要优先使用 DeepSeek，建议：

* 注释掉 `GEMINI_API_KEY` 和 `ANTHROPIC_API_KEY`

* 只保留 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL`

***

## 预期结果

1. OpenClaw 成功安装并可通过命令行调用
2. `.env` 文件已配置 DeepSeek 模型参数
3. 项目将使用 DeepSeek 模型进行 AI 股票分析

***

## 注意事项

1. **API Key**：用户需要自行从 [DeepSeek 官网](https://platform.deepseek.com/) 获取 API Key
2. **网络环境**：DeepSeek API 在国内可直接访问，无需代理
3. **OpenClaw 用途**：OpenClaw 主要用于 AI 辅助开发和测试，与股票分析系统的 AI 分析功能是独立的
4. **模型切换**：修改 `.env` 文件后，下次运行 `python main.py` 时自动生效，无需重启服务

***

## 回滚方案

如果需要切换回其他模型，只需修改 `.env` 文件：

* 切换回 Gemini：取消注释 `GEMINI_API_KEY`

* 切换回 Claude：取消注释 `ANTHROPIC_API_KEY`

