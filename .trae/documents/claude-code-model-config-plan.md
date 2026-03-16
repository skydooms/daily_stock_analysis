# Claude Code 模型配置计划

## 任务理解

用户要求：

1. 开启 claude code，查看默认的调用模型
2. 设置 glm-5 模型为默认模型

## 当前项目默认模型配置分析

### 模型优先级（当前配置）

项目支持三种 AI 模型，按优先级排序：

| 优先级 | 模型类型             | 默认模型名称                       | 配置项              |
| --- | ---------------- | ---------------------------- | ---------------- |
| 1   | Gemini           | `gemini-3-flash-preview`     | GEMINI\_MODEL    |
| 2   | Anthropic Claude | `claude-3-5-sonnet-20241022` | ANTHROPIC\_MODEL |
| 3   | OpenAI 兼容        | `gpt-4o-mini`                | OPENAI\_MODEL    |

### 配置来源

配置文件位置：`src/config.py`（第 64-84 行）

```python
# === AI 分析配置 ===
gemini_api_key: Optional[str] = None
gemini_model: str = "gemini-3-flash-preview"  # 主模型
gemini_model_fallback: str = "gemini-2.5-flash"  # 备选模型

# Anthropic Claude API（备选）
anthropic_api_key: Optional[str] = None
anthropic_model: str = "claude-3-5-sonnet-20241022"

# OpenAI 兼容 API（备选）
openai_api_key: Optional[str] = None
openai_base_url: Optional[str] = None
openai_model: str = "gpt-4o-mini"
```

### 模型选择逻辑

参见 `src/analyzer.py` 中的 `GeminiAnalyzer.__init__()` 方法：

1. 首先检查 Gemini API Key 是否有效
2. 如果 Gemini 不可用，尝试 Anthropic Claude
3. 如果 Anthropic 也不可用，尝试 OpenAI 兼容 API

## 设置 glm-5 为默认模型的方案

### 方案说明

GLM-5 是智谱 AI 的大语言模型，可以通过 OpenAI 兼容 API 方式调用。

### 配置步骤

#### 步骤 1：修改 `src/config.py`

将 OpenAI 兼容模型的默认值改为 glm-5：

```python
# 修改前
openai_model: str = "gpt-4o-mini"

# 修改后
openai_model: str = "glm-5"
```

#### 步骤 2：配置环境变量

在 `.env` 文件中添加：

```env
# GLM-5 配置（通过智谱 API）
OPENAI_API_KEY=your_zhipu_api_key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
OPENAI_MODEL=glm-5
```

#### 步骤 3：调整模型优先级（可选）

如果希望 glm-5 成为首选模型，有两种方式：

**方式 A：不配置 Gemini 和 Anthropic API Key**

* 系统会自动回退到 OpenAI 兼容 API（即 glm-5）

**方式 B：修改** **`src/analyzer.py`** **的初始化逻辑**

* 调整模型优先级顺序，使 OpenAI 兼容 API 优先

## 实施步骤

### 步骤 1：修改默认模型配置

编辑 `src/config.py`，将 `openai_model` 默认值改为 `glm-5`

### 步骤 2：更新文档

更新 `docs/FEATURES.md` 中的模型支持说明

### 步骤 3：验证配置

运行语法检查确保代码正确

## 文件变更清单

| 文件                 | 变更类型 | 说明                          |
| ------------------ | ---- | --------------------------- |
| `src/config.py`    | 修改   | 将 openai\_model 默认值改为 glm-5 |
| `docs/FEATURES.md` | 修改   | 更新模型支持说明                    |

## 预期结果

配置完成后，当 Gemini 和 Anthropic API Key 未配置时，系统将默认使用 glm-5 模型进行 AI 分析。
