#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "data" / "stock_analysis.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("彻底清理所有 300759 相关的记录...")
print("=" * 80)

# 先查询所有相关记录
print("查询所有 300759 相关记录:")
cursor.execute("SELECT * FROM stock_monitor_configs WHERE stock_code = '300759' OR stock_code = '300759'")
configs = cursor.fetchall()
print(f"  configs 表找到 {len(configs)} 条记录")

cursor.execute("SELECT * FROM stock_monitor_states WHERE stock_code = '300759'")
states = cursor.fetchall()
print(f"  states 表找到 {len(states)} 条记录")

cursor.execute("SELECT * FROM stock_monitor_alerts WHERE stock_code = '300759'")
alerts = cursor.fetchall()
print(f"  alerts 表找到 {len(alerts)} 条记录")

# 删除所有相关记录
print("\n删除中...")
cursor.execute("DELETE FROM stock_monitor_alerts WHERE stock_code = '300759'")
print(f"  删除了 {cursor.rowcount} 条 alerts 记录")

cursor.execute("DELETE FROM stock_monitor_states WHERE stock_code = '300759'")
print(f"  删除了 {cursor.rowcount} 条 states 记录")

cursor.execute("DELETE FROM stock_monitor_configs WHERE stock_code = '300759'")
print(f"  删除了 {cursor.rowcount} 条 configs 记录")

conn.commit()

print("\n" + "=" * 80)
print("清理后的状态:")
cursor.execute("SELECT id, stock_code, user_id FROM stock_monitor_configs")
configs = cursor.fetchall()
print(f"  configs 表现在有 {len(configs)} 条记录: {[c[1] for c in configs]}")

cursor.execute("SELECT id, config_id, stock_code FROM stock_monitor_states")
states = cursor.fetchall()
print(f"  states 表现在有 {len(states)} 条记录: {[s[2] for s in states]}")

conn.close()
print("\n清理完成！")

