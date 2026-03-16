# 在 OpenClaw 中运行 Python 脚本并发送结果到飞书

## 任务概述

创建一个 OpenClaw Skill，用于运行 Python 脚本（随机等待 1-5 秒，返回 0-10 之间的整数，包含时间戳），并将结果发送到飞书机器人。

---

## 背景说明

**OpenClaw Skill**：是 OpenClaw 的"小程序"或"插件"，每个技能给 OpenClaw 增加特殊能力。

**飞书 Channel**：已配置完成，可以通过飞书机器人发送和接收消息。

---

## 实施步骤

### 步骤 1：创建 Python 脚本

在项目目录中创建 Python 脚本 `random_number_generator.py`：

```python
import random
import time
import json
import sys
from datetime import datetime

def main():
    # 随机等待 1-5 秒
    wait_time = random.uniform(1, 5)
    time.sleep(wait_time)
    
    # 生成 0-10 之间的随机整数
    random_number = random.randint(0, 10)
    
    # 获取当前时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 构建结果
    result = {
        "random_number": random_number,
        "wait_time": round(wait_time, 2),
        "timestamp": current_time
    }
    
    # 输出 JSON 格式结果
    print(json.dumps(result, ensure_ascii=False))
    
    return result

if __name__ == "__main__":
    main()
```

**文件位置**：`d:\project\daily_stock_analysis\random_number_generator.py`

---

### 步骤 2：创建 OpenClaw Skill

创建 Skill 目录结构和文件：

**目录结构**：
```
C:\Users\Administrator\.openclaw\skills\random-number-generator\
├── SKILL.md
├── index.ts
└── package.json
```

**2.1 创建 SKILL.md**

```markdown
---
name: random-number-generator
description: |
  Generate a random number between 0-10 with a random delay of 1-5 seconds.
  Returns the number, wait time, and timestamp.
---

# Random Number Generator

Generates a random integer between 0 and 10 with a random delay of 1-5 seconds.

## Usage

Trigger this skill by mentioning "随机数", "random number", or "生成随机数" in Feishu.

## Example

User: "生成一个随机数"
Bot: Runs the Python script and returns:
```
{
  "random_number": 7,
  "wait_time": 3.45,
  "timestamp": "2026-03-09 15:30:45"
}
```

## Output Format

- `random_number`: Integer between 0-10
- `wait_time`: Actual wait time in seconds (1-5)
- `timestamp`: Execution time in format YYYY-MM-DD HH:MM:SS
```

**文件位置**：`C:\Users\Administrator\.openclaw\skills\random-number-generator\SKILL.md`

---

**2.2 创建 package.json**

```json
{
  "name": "random-number-generator",
  "version": "1.0.0",
  "description": "Generate random numbers with Python script",
  "main": "index.ts",
  "type": "module",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "keywords": [
    "random",
    "number",
    "generator"
  ],
  "author": "",
  "license": "MIT"
}
```

**文件位置**：`C:\Users\Administrator\.openclaw\skills\random-number-generator\package.json`

---

**2.3 创建 index.ts**

```typescript
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export default {
  name: 'random-number-generator',
  description: 'Generate a random number between 0-10 with a random delay of 1-5 seconds',
  
  async execute(context: any) {
    const pythonScriptPath = 'd:\\project\\daily_stock_analysis\\random_number_generator.py';
    
    try {
      // Execute Python script
      const { stdout, stderr } = await execAsync(`python "${pythonScriptPath}"`, {
        cwd: 'd:\\project\\daily_stock_analysis',
        timeout: 10000 // 10 second timeout
      });
      
      if (stderr) {
        console.error('Python script stderr:', stderr);
      }
      
      // Parse JSON output
      const result = JSON.parse(stdout.trim());
      
      // Format message for Feishu
      const message = `🎲 随机数生成结果\n\n` +
                    `随机数字: ${result.random_number}\n` +
                    `等待时间: ${result.wait_time} 秒\n` +
                    `执行时间: ${result.timestamp}`;
      
      return {
        success: true,
        message,
        data: result
      };
      
    } catch (error: any) {
      console.error('Error executing Python script:', error);
      return {
        success: false,
        message: `❌ 执行失败: ${error.message}`,
        error: error.message
      };
    }
  }
};
```

**文件位置**：`C:\Users\Administrator\.openclaw\skills\random-number-generator\index.ts`

---

### 步骤 3：安装 Skill 依赖

在 Skill 目录中安装 TypeScript 类型定义：

```bash
cd C:\Users\Administrator\.openclaw\skills\random-number-generator
npm install --save-dev @types/node
```

---

### 步骤 4：注册 Skill

在 OpenClaw 配置中注册 Skill：

```bash
openclaw skill install C:\Users\Administrator\.openclaw\skills\random-number-generator
```

或者手动添加到配置文件 `C:\Users\Administrator\.openclaw\openclaw.json`：

```json
{
  "skills": {
    "entries": {
      "random-number-generator": {
        "enabled": true,
        "path": "C:\\Users\\Administrator\\.openclaw\\skills\\random-number-generator"
      }
    }
  }
}
```

---

### 步骤 5：重启 OpenClaw Gateway

重启 Gateway 以加载新的 Skill：

```bash
openclaw gateway stop
timeout /t 3 /nobreak
openclaw gateway
```

---

### 步骤 6：测试 Skill

在飞书中测试：

1. 打开飞书，找到机器人
2. 发送消息："生成一个随机数" 或 "random number"
3. 等待机器人响应（1-5 秒）
4. 查看返回的结果

**预期输出**：
```
🎲 随机数生成结果

随机数字: 7
等待时间: 3.45 秒
执行时间: 2026-03-09 15:30:45
```

---

## 验证步骤

### 1. 验证 Python 脚本

```bash
cd d:\project\daily_stock_analysis
python random_number_generator.py
```

预期输出：
```json
{"random_number": 5, "wait_time": 2.34, "timestamp": "2026-03-09 15:30:45"}
```

### 2. 验证 Skill 加载

```bash
openclaw skills list
```

预期输出：
```
Installed skills:
- random-number-generator
```

### 3. 验证飞书连接

```bash
openclaw channels list
```

预期输出：
```
Chat channels:
- Feishu default: configured, enabled
```

---

## 故障排查

### 问题 1：Python 脚本未找到

**症状**：Skill 返回 "执行失败: spawn python ENOENT"

**解决方案**：
- 确保 Python 已安装并在 PATH 中
- 检查 Python 脚本路径是否正确
- 使用完整路径：`C:\Python311\python.exe` 或 `py.exe`

### 问题 2：Skill 未加载

**症状**：`openclaw skills list` 中没有显示 Skill

**解决方案**：
- 检查 Skill 目录结构是否正确
- 检查 `openclaw.json` 配置
- 重启 Gateway

### 问题 3：飞书机器人无响应

**症状**：在飞书中发送消息后无响应

**解决方案**：
- 检查 Gateway 是否运行：`openclaw health`
- 检查飞书 Channel 是否启用：`openclaw channels list`
- 查看日志：`openclaw logs`

---

## 预期结果

1. ✅ Python 脚本创建成功并能独立运行
2. ✅ OpenClaw Skill 创建并注册成功
3. ✅ Gateway 重启后 Skill 已加载
4. ✅ 在飞书中发送消息后，机器人返回随机数结果
5. ✅ 结果包含随机数字、等待时间和时间戳

---

## 注意事项

1. **Python 环境**：确保系统已安装 Python 3.8+ 并在 PATH 中
2. **Skill 路径**：使用绝对路径避免路径问题
3. **超时设置**：Python 脚本执行超时设置为 10 秒
4. **错误处理**：Skill 包含完整的错误处理和日志
5. **飞书权限**：确保飞书应用有发送消息的权限
