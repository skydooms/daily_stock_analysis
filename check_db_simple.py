#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.storage import DatabaseManager
from sqlalchemy import text

db_manager = DatabaseManager.get_instance()

print("检查数据库中的所有监控配置...")
print("=" * 80)

# 直接查询数据库
with db_manager.get_session() as session:
    # 使用原生SQL查询
    result = session.execute(
        text("SELECT id, stock_code, user_id, is_active, created_at FROM stock_monitor_config")
    ).fetchall()

    print(f"数据库中共有 {len(result)} 条监控配置：")
    for row in result:
        print(f"  ID: {row[0]}, 股票代码: {row[1]}, 用户ID: {row[2]}, 活跃: {row[3]}, 创建时间: {row[4]}")

print("\n" + "=" * 80)
print("尝试直接删除 300759 的配置...")

# 直接删除
with db_manager.get_session() as session:
    result = session.execute(
        text("DELETE FROM stock_monitor_config WHERE stock_code = '300759' AND user_id = 'monitor_user_001'")
    )
    session.commit()
    print(f"删除了 {result.rowcount} 条配置")

print("\n检查删除后的状态...")
with db_manager.get_session() as session:
    result = session.execute(
        text("SELECT id, stock_code, user_id, is_active FROM stock_monitor_config")
    ).fetchall()
    print(f"数据库中现在有 {len(result)} 条监控配置：")
    for row in result:
        print(f"  ID: {row[0]}, 股票代码: {row[1]}, 用户ID: {row[2]}, 活跃: {row[3]}")

