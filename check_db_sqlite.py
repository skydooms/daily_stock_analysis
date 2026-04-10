#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "data" / "stock_analysis.db"

print(f"数据库路径: {db_path}")
print("=" * 80)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 列出所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("\n" + "=" * 80)
if "stock_monitor_configs" in [t[0] for t in tables]:
    print("查询 stock_monitor_configs 表的数据...")
    cursor.execute("SELECT id, stock_code, user_id, is_active, created_at FROM stock_monitor_configs")
    rows = cursor.fetchall()
    print(f"共有 {len(rows)} 条记录:")
    for row in rows:
        print(f"  ID: {row[0]}, 股票代码: {row[1]}, 用户ID: {row[2]}, 活跃: {row[3]}, 创建时间: {row[4]}")
    
    print("\n" + "=" * 80)
    print("尝试删除 300759 的记录...")
    cursor.execute("DELETE FROM stock_monitor_configs WHERE stock_code = '300759' AND user_id = 'monitor_user_001'")
    conn.commit()
    print(f"删除了 {cursor.rowcount} 条记录")
    
    print("\n检查删除后的数据...")
    cursor.execute("SELECT id, stock_code, user_id, is_active FROM stock_monitor_configs")
    rows = cursor.fetchall()
    print(f"现在共有 {len(rows)} 条记录:")
    for row in rows:
        print(f"  ID: {row[0]}, 股票代码: {row[1]}, 用户ID: {row[2]}, 活跃: {row[3]}")
else:
    print("stock_monitor_configs 表不存在")

conn.close()

