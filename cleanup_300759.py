#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "data" / "stock_analysis.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("检查 stock_monitor_configs 表:")
cursor.execute("SELECT id, stock_code, user_id FROM stock_monitor_configs")
configs = cursor.fetchall()
print(f"  共 {len(configs)} 条记录:")
for cfg in configs:
    print(f"    {cfg}")

print("\n" + "=" * 80)
print("检查 stock_monitor_states 表:")
cursor.execute("SELECT id, config_id, stock_code FROM stock_monitor_states")
states = cursor.fetchall()
print(f"  共 {len(states)} 条记录:")
for state in states:
    print(f"    {state}")

print("\n" + "=" * 80)
print("尝试删除 300759 相关的所有记录...")

# 先从 configs 表删除
cursor.execute("DELETE FROM stock_monitor_configs WHERE stock_code = '300759' AND user_id = 'monitor_user_001'")
config_deleted = cursor.rowcount
print(f"  从 configs 表删除了 {config_deleted} 条记录")

# 再从 states 表删除（通过 stock_code）
cursor.execute("DELETE FROM stock_monitor_states WHERE stock_code = '300759'")
state_deleted = cursor.rowcount
print(f"  从 states 表删除了 {state_deleted} 条记录")

conn.commit()

print("\n" + "=" * 80)
print("删除后的状态:")
cursor.execute("SELECT id, stock_code, user_id FROM stock_monitor_configs")
configs = cursor.fetchall()
print(f"  configs 表现在有 {len(configs)} 条记录")

cursor.execute("SELECT id, config_id, stock_code FROM stock_monitor_states")
states = cursor.fetchall()
print(f"  states 表现在有 {len(states)} 条记录")

conn.close()

