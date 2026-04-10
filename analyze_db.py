#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path
from datetime import datetime, date

db_path = Path(__file__).parent / "data" / "stock_analysis.db"

print("=" * 80)
print(f"stock_analysis.db 数据库分析报告")
print(f"数据库路径: {db_path}")
print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 列出所有表
print("\n1. 数据库中的所有表:")
print("-" * 80)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()
for i, (table_name,) in enumerate(tables, 1):
    print(f"  {i}. {table_name}")

# 2. 每个表的详细结构和数据统计
print("\n" + "=" * 80)
print("2. 各表详细信息:")
print("=" * 80)

for (table_name,) in tables:
    print(f"\n--- 表: {table_name} ---")
    print("-" * 80)
    
    # 表结构
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print("  字段结构:")
    for col in columns:
        col_id, name, col_type, notnull, default, pk = col
        pk_mark = " [PK]" if pk else ""
        null_mark = " NOT NULL" if notnull else ""
        default_mark = f" DEFAULT={default}" if default else ""
        print(f"    {name}: {col_type}{pk_mark}{null_mark}{default_mark}")
    
    # 数据行数
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]
    print(f"\n  数据行数: {row_count}")
    
    # 如果数据少，显示前几条
    if row_count > 0 and row_count <= 10:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        rows = cursor.fetchall()
        print("\n  前5条数据:")
        for row in rows:
            print(f"    {row}")
    elif row_count > 10:
        # 只显示第一条数据
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        first_row = cursor.fetchone()
        print("\n  第一条数据:")
        print(f"    {first_row}")

# 3. 特别关注几个核心表的详细数据
print("\n" + "=" * 80)
print("3. 核心表详细分析:")
print("=" * 80)

# stock_daily 表
if "stock_daily" in [t[0] for t in tables]:
    print("\n--- stock_daily 表（股票日线数据）---")
    cursor.execute("SELECT code, COUNT(*) as cnt FROM stock_daily GROUP BY code ORDER BY cnt DESC")
    stock_counts = cursor.fetchall()
    print(f"\n  包含 {len(stock_counts)} 只股票的数据:")
    for code, cnt in stock_counts[:10]:
        cursor.execute("SELECT MIN(date), MAX(date) FROM stock_daily WHERE code = ?", (code,))
        min_date, max_date = cursor.fetchone()
        print(f"    {code}: {cnt} 条数据 ({min_date} 至 {max_date})")
    if len(stock_counts) > 10:
        print(f"    ... 还有 {len(stock_counts) - 10} 只股票")

# news_intel 表
if "news_intel" in [t[0] for t in tables]:
    print("\n--- news_intel 表（新闻情报）---")
    cursor.execute("SELECT code, COUNT(*) as cnt FROM news_intel GROUP BY code ORDER BY cnt DESC")
    news_counts = cursor.fetchall()
    print(f"\n  包含 {len(news_counts)} 只股票的新闻:")
    for code, cnt in news_counts[:10]:
        print(f"    {code}: {cnt} 条新闻")
    if len(news_counts) > 10:
        print(f"    ... 还有 {len(news_counts) - 10} 只股票")
    cursor.execute("SELECT MIN(fetched_at), MAX(fetched_at) FROM news_intel")
    min_fetch, max_fetch = cursor.fetchone()
    print(f"\n  新闻时间范围: {min_fetch} 至 {max_fetch}")

# portfolio_* 相关表
portfolio_tables = [t[0] for t in tables if t[0].startswith('portfolio_')]
if portfolio_tables:
    print("\n--- 持仓管理相关表 ---")
    for table in portfolio_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = cursor.fetchone()[0]
        print(f"  {table}: {cnt} 条记录")

# analysis_history 表
if "analysis_history" in [t[0] for t in tables]:
    print("\n--- analysis_history 表（分析历史）---")
    cursor.execute("SELECT code, COUNT(*) as cnt FROM analysis_history GROUP BY code ORDER BY cnt DESC")
    analysis_counts = cursor.fetchall()
    print(f"\n  包含 {len(analysis_counts)} 只股票的分析记录:")
    for code, cnt in analysis_counts[:10]:
        print(f"    {code}: {cnt} 次分析")
    if len(analysis_counts) > 10:
        print(f"    ... 还有 {len(analysis_counts) - 10} 只股票")
    cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM analysis_history")
    min_created, max_created = cursor.fetchone()
    print(f"\n  分析时间范围: {min_created} 至 {max_created}")

# stock_monitor_* 相关表
monitor_tables = [t[0] for t in tables if t[0].startswith('stock_monitor_')]
if monitor_tables:
    print("\n--- 股票监控相关表 ---")
    for table in monitor_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = cursor.fetchone()[0]
        print(f"  {table}: {cnt} 条记录")

conn.close()

print("\n" + "=" * 80)
print("数据库分析完成！")
print("=" * 80)

