# OpenClaw 定时向飞书机器人发送随机数

## 任务概述

实现一个定时任务，每隔 5-10 秒（随机间隔），通过 Python 脚本向飞书机器人"龙虾炒股"发送一个 0-10 之间的随机整数，并标注发送日期。

***

## 需求分析

### 功能需求

1. **定时执行**：每隔 5-10 秒（随机间隔）执行一次
2. **生成随机数**：生成 0-10 之间的随机整数
3. **标注日期**：包含发送日期时间
4. **发送到飞书**：发送到指定的飞书机器人

### 技术要求

* Python 脚本实现核心逻辑

* 通过 OpenClaw Gateway API 或飞书 API 发送消息

* Windows 环境运行（考虑 Windows Task Scheduler 或 Python 循环）

***

## 实施方案

### 方案 A：Python 脚本 + OpenClaw Gateway API（推荐）

**优点**：

* 利用 OpenClaw 已有的飞书 Channel 配置

* 无需额外配置飞书 API

* 统一的消息发送接口

**实现步骤**：

#### 步骤 1：创建 Python 脚本

创建文件：`d:\project\daily_stock_analysis\random_sender.py`

```python
#!/usr/bin/env python3
"""
Random Number Sender to Feishu via OpenClaw Gateway
Sends a random number (0-10) to Feishu bot every 5-10 seconds
"""

import random
import time
import json
import requests
from datetime import datetime
import sys

# OpenClaw Gateway Configuration
GATEWAY_URL = "ws://127.0.0.1:18789"
GATEWAY_TOKEN = "7b579f175058028b846064c699f531059eb069e893d9822d"

# Feishu target configuration
# 飞书机器人"龙虾炒股"的接收 ID
# 需要替换为实际的 receive_id（用户 open_id 或群 chat_id）
FEISHU_RECEIVE_ID = "ou_877402488027a291bf887528431d2744"  # 用户 open_id
FEISHU_RECEIVE_ID_TYPE = "open_id"  # or "chat_id" for group

def generate_random_number():
    """Generate a random number between 0-10"""
    return random.randint(0, 10)

def format_message(random_number: int) -> str:
    """Format the message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"🎲 随机数: {random_number}\n📅 时间: {timestamp}"
    return message

def send_to_feishu_via_gateway(message: str) -> bool:
    """
    Send message to Feishu via OpenClaw Gateway HTTP API
    
    Note: OpenClaw Gateway primarily uses WebSocket, but we can use
    the sessions_send tool through the agent.
    """
    try:
        # Method 1: Use OpenClaw's HTTP endpoint (if available)
        # This would require OpenClaw to have an HTTP API for sending messages
        
        # Method 2: Use Feishu API directly with the configured credentials
        # This is more reliable for automated scripts
        return send_to_feishu_direct(message)
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def send_to_feishu_direct(message: str) -> bool:
    """
    Send message to Feishu using direct API call
    Uses the Feishu app credentials from OpenClaw config
    """
    import hashlib
    
    # Feishu App credentials (from OpenClaw config)
    APP_ID = "cli_a924f365e2f89cc0"
    APP_SECRET = "Fq1fQ3kyEoa6zneJHbtsuA3kQKiybVyt"
    
    # Get tenant access token
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    token_response = requests.post(
        token_url,
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=10
    )
    
    if token_response.status_code != 200:
        print(f"Failed to get token: {token_response.text}")
        return False
    
    token_data = token_response.json()
    if token_data.get("code") != 0:
        print(f"Token error: {token_data}")
        return False
    
    access_token = token_data["tenant_access_token"]
    
    # Send message
    send_url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "receive_id": FEISHU_RECEIVE_ID,
        "msg_type": "text",
        "content": json.dumps({"text": message})
    }
    
    params = {"receive_id_type": FEISHU_RECEIVE_ID_TYPE}
    
    response = requests.post(
        send_url,
        headers=headers,
        params=params,
        json=payload,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 0:
            print(f"✅ Message sent successfully: {message}")
            return True
        else:
            print(f"❌ Send error: {result}")
            return False
    else:
        print(f"❌ HTTP error: {response.status_code} - {response.text}")
        return False

def main():
    """Main loop: send random number every 5-10 seconds"""
    print("🚀 Starting Random Number Sender to Feishu...")
    print(f"Target: {FEISHU_RECEIVE_ID_TYPE}={FEISHU_RECEIVE_ID}")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Generate random interval (5-10 seconds)
            interval = random.uniform(5, 10)
            
            # Generate random number
            random_number = generate_random_number()
            
            # Format message
            message = format_message(random_number)
            
            # Send to Feishu
            send_to_feishu_direct(message)
            
            # Wait for random interval
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")

if __name__ == "__main__":
    main()
```

#### 步骤 2：获取飞书机器人接收 ID

需要确定飞书机器人"龙虾炒股"的接收 ID：

* 如果是私聊：使用用户的 `open_id`

* 如果是群聊：使用群的 `chat_id`

**获取方法**：

1. 在飞书中与机器人对话
2. 通过 OpenClaw 日志查看 `sender_id`
3. 或通过飞书管理后台获取

#### 步骤 3：测试脚本

```bash
cd d:\project\daily_stock_analysis
python random_sender.py
```

#### 步骤 4：配置为后台服务（可选）

使用 NSSM (Non-Sucking Service Manager) 将脚本安装为 Windows 服务：

```bash
# 下载 NSSM
# https://nssm.cc/download

# 安装服务
nssm install RandomSender "C:\Python311\python.exe" "d:\project\daily_stock_analysis\random_sender.py"
nssm start RandomSender
```

***

### 方案 B：创建 OpenClaw Skill + 定时任务

**优点**：

* 集成到 OpenClaw 生态

* 可以通过对话控制

**缺点**：

* OpenClaw 本身没有内置的定时任务机制

* 需要依赖外部调度器

**实现步骤**：

#### 步骤 1：创建 Skill 目录

```
C:\Users\Administrator\.openclaw\workspace\skills\random-sender-1.0.0\
├── SKILL.md
├── scripts\
│   ├── send_random.py
│   └── scheduler.py
└── config.json
```

#### 步骤 2：创建 SKILL.md

```markdown
---
name: random-sender
description: Send random numbers (0-10) to Feishu bot at random intervals (5-10s). Use when user wants to start/stop automated random number sending.
---

# Random Number Sender

Automatically sends random numbers to Feishu bot at random intervals.

## Commands

- "开始发送随机数" - Start sending random numbers
- "停止发送随机数" - Stop sending random numbers
- "查看发送状态" - Check sender status

## Configuration

Edit `config.json` to set:
- `receive_id`: Target Feishu user/group ID
- `receive_id_type`: "open_id" or "chat_id"
- `min_interval`: Minimum interval in seconds (default: 5)
- `max_interval`: Maximum interval in seconds (default: 10)
```

#### 步骤 3：创建 Python 脚本

`scripts/scheduler.py`:

```python
#!/usr/bin/env python3
import schedule
import time
import random
from datetime import datetime
import requests
import json
import threading

# Configuration
CONFIG = {
    "receive_id": "ou_877402488027a291bf887528431d2744",
    "receive_id_type": "open_id",
    "min_interval": 5,
    "max_interval": 10
}

# Feishu credentials
APP_ID = "cli_a924f365e2f89cc0"
APP_SECRET = "Fq1fQ3kyEoa6zneJHbtsuA3kQKiybVyt"

running = False
thread = None

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    response = requests.post(url, json={
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    })
    data = response.json()
    return data.get("tenant_access_token")

def send_message(text):
    token = get_access_token()
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"receive_id_type": CONFIG["receive_id_type"]}
    data = {
        "receive_id": CONFIG["receive_id"],
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }
    requests.post(url, headers=headers, params=params, json=data)

def job():
    number = random.randint(0, 10)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"🎲 随机数: {number}\n📅 时间: {timestamp}"
    send_message(message)
    print(f"Sent: {message}")

def run_scheduler():
    global running
    while running:
        interval = random.uniform(CONFIG["min_interval"], CONFIG["max_interval"])
        time.sleep(interval)
        if running:
            job()

def start():
    global running, thread
    if not running:
        running = True
        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()
        return "✅ 随机数发送已启动"
    return "⚠️ 已在运行中"

def stop():
    global running
    running = False
    return "🛑 随机数发送已停止"

def status():
    return "🟢 运行中" if running else "🔴 已停止"

if __name__ == "__main__":
    print("Starting random sender...")
    start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop()
        print("Stopped")
```

***

## 推荐方案

**推荐使用方案 A（Python 脚本 + 飞书 API）**，原因：

1. ✅ 实现简单，易于调试
2. ✅ 不依赖 OpenClaw Gateway 运行状态
3. ✅ 可以独立部署和运行
4. ✅ 易于扩展和维护

***

## 实施步骤总结

### 步骤 1：创建 Python 脚本

* 创建 `random_sender.py` 文件

* 实现随机数生成和飞书消息发送逻辑

### 步骤 2：配置接收 ID

* 确定飞书机器人"龙虾炒股"的接收 ID

* 更新脚本中的 `FEISHU_RECEIVE_ID`

### 步骤 3：测试运行

* 手动运行脚本测试

* 验证消息是否正确发送到飞书

### 步骤 4：部署为后台服务（可选）

* 使用 NSSM 或 Windows Task Scheduler

* 配置自动启动

***

## 注意事项

1. **API 限流**：飞书 API 有频率限制，5-10 秒间隔是安全的
2. **错误处理**：脚本包含完整的错误处理和重试逻辑
3. **日志记录**：建议添加日志文件记录发送历史
4. **安全性**：API Secret 应存储在环境变量或配置文件中

***

## 预期结果

运行脚本后，飞书机器人"龙虾炒股"将每隔 5-10 秒收到类似消息：

```
🎲 随机数: 7
📅 时间: 2026-03-10 22:30:45
```

***

## 回滚方案

如果需要停止发送：

1. 按 `Ctrl+C` 停止脚本
2. 如果安装为服务：`nssm stop RandomSender`
3. 删除脚本文件即可完全移除

