#!/usr/bin/env python3
"""
Random Number Sender to Feishu via OpenClaw Gateway
Sends a random number (0-10) to Feishu bot every 5-10 seconds
"""

import random
import time
import json
import sys
from datetime import datetime
import urllib.request
import urllib.parse

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

def send_to_feishu_direct(message: str) -> bool:
    """
    Send message to Feishu using direct API call
    Uses Feishu app credentials from OpenClaw config
    """
    try:
        # Feishu App credentials (from OpenClaw config)
        APP_ID = "cli_a924f365e2f89cc0"
        APP_SECRET = "Fq1fQ3kyEoa6zneJHbtsuA3kQKiybVyt"
        
        # Get tenant access token
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        
        # 飞书 API 要求使用 JSON 格式
        token_data = json.dumps({
            "app_id": APP_ID,
            "app_secret": APP_SECRET
        }).encode('utf-8')
        
        print(f"\n🔑 Requesting access token...")
        print(f"   URL: {token_url}")
        
        token_request = urllib.request.Request(
            token_url,
            data=token_data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(token_request, timeout=10) as response:
            token_response = json.loads(response.read().decode('utf-8'))
        
        print(f"   Response: {token_response}")
        
        if token_response.get("code") != 0:
            print(f"Failed to get token: {token_response}")
            return False
        
        access_token = token_response["tenant_access_token"]
        print(f"✅ Access token obtained: {access_token[:20]}...")
        
        # Send message
        send_url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        # 飞书 API 格式：content 必须是 JSON 字符串
        # 例如: "{\"text\":\"test content\"}"
        content_json = json.dumps({"text": message}, ensure_ascii=False)
        
        payload = {
            "receive_id": FEISHU_RECEIVE_ID,
            "msg_type": "text",
            "content": content_json
        }
        
        # 使用 query 参数传递 receive_id_type
        params = urllib.parse.urlencode({"receive_id_type": FEISHU_RECEIVE_ID_TYPE})
        
        # 打印调试信息
        print(f"\n📤 Sending request to Feishu API:")
        print(f"   URL: {send_url}?{params}")
        print(f"   Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        send_request = urllib.request.Request(
            f"{send_url}?{params}",
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(send_request, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        if result.get("code") == 0:
            print(f"✅ Message sent successfully: {message}")
            return True
        else:
            print(f"❌ Send error: {result}")
            print(f"   Error code: {result.get('code')}")
            print(f"   Error msg: {result.get('msg')}")
            return False
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"Response body: {error_body}")
        return False
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def main():
    """Main loop: send random number every 5-10 seconds"""
    print("🚀 Starting Random Number Sender to Feishu...")
    print(f"Target: {FEISHU_RECEIVE_ID_TYPE}={FEISHU_RECEIVE_ID}")
    print("Press Ctrl+C to stop\n")
    
    try:
        count = 0
        while True:
            # Generate random interval (5-10 seconds)
            interval = random.uniform(5, 10)
            
            # Generate random number
            random_number = generate_random_number()
            
            # Format message
            message = format_message(random_number)
            
            # Send to Feishu
            success = send_to_feishu_direct(message)
            
            count += 1
            if success:
                print(f"✅ Message #{count} sent successfully! Next in {interval:.1f}s\n")
            else:
                print(f"❌ Message #{count} failed! Next in {interval:.1f}s\n")
            
            # Wait for random interval
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n\n👋 Stopped by user. Total messages sent: {count}")

if __name__ == "__main__":
    main()
