#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "data" / "stock_analysis.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("查看 stock_monitor_configs 表结构:")
cursor.execute("PRAGMA table_info(stock_monitor_configs)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col}")

print("\n" + "=" * 80)
print("查看索引:")
cursor.execute("PRAGMA index_list(stock_monitor_configs)")
indexes = cursor.fetchall()
for idx in indexes:
    print(f"  {idx}")

print("\n" + "=" * 80)
print("尝试查询大写的 300759:")
cursor.execute("SELECT id, stock_code, user_id FROM stock_monitor_configs WHERE stock_code = '300759'")
rows = cursor.fetchall()
print(f"  找到 {len(rows)} 条记录")
for row in rows:
    print(f"  {row}")

print("\n查询所有股票代码:")
cursor.execute("SELECT DISTINCT stock_code FROM stock_monitor_configs")
all_codes = cursor.fetchall()
print(f"  所有股票代码: {[c[0] for c in all_codes]}")

conn.close()

