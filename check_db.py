#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.storage import DatabaseManager
from src.repositories.stock_monitor_repo import StockMonitorRepository

db_manager = DatabaseManager.get_instance()
repo = StockMonitorRepository(db_manager)

print("检查数据库中的所有监控配置...")
print("=" * 80)

# 查询所有配置（包括非活跃的）
with db_manager.get_session() as session:
    from src.monitor.models import StockMonitorConfig
    all_configs = session.execute(
        StockMonitorConfig.__table__.select()
    ).fetchall()

    print(f"数据库中共有 {len(all_configs)} 条监控配置：")
    for cfg in all_configs:
        print(f"  ID: {cfg.id}, 股票代码: {cfg.stock_code}, 用户ID: {cfg.user_id}, 活跃: {cfg.is_active}, 创建时间: {cfg.created_at}")

print("\n" + "=" * 80)
print("尝试直接删除 300759 的配置...")

# 直接删除 300759 的记录
count = repo.remove_config_by_stock("300759", "monitor_user_001")
print(f"删除了 {count} 条配置")

print("\n检查删除后的状态...")
with db_manager.get_session() as session:
    all_configs = session.execute(
        StockMonitorConfig.__table__.select()
    ).fetchall()
    print(f"数据库中现在有 {len(all_configs)} 条监控配置：")
    for cfg in all_configs:
        print(f"  ID: {cfg.id}, 股票代码: {cfg.stock_code}, 用户ID: {cfg.user_id}, 活跃: {cfg.is_active}")

