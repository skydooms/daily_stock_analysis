# -*- coding: utf-8 -*-
"""
Test script for stock monitor notification.

Tests:
1. Add realtime monitor for HK stock 康龙化成 (03759.HK)
2. Add realtime monitor for US stock Oracle (ORCL)
3. Simulate price change > 2% to trigger notification
4. Send Feishu notification
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cleanup_test_data():
    """Cleanup any existing test data."""
    from src.storage import DatabaseManager
    from src.monitor.models import StockMonitorConfig, StockMonitorState, StockMonitorAlert
    from sqlalchemy import delete

    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        # Delete all test data
        session.execute(
            delete(StockMonitorAlert).where(
                StockMonitorAlert.config_id.in_(
                    session.query(StockMonitorConfig.id)
                    .where(StockMonitorConfig.user_id.like("test_user_%"))
                    .subquery()
                )
            )
        )
        session.execute(
            delete(StockMonitorState).where(
                StockMonitorState.config_id.in_(
                    session.query(StockMonitorConfig.id)
                    .where(StockMonitorConfig.user_id.like("test_user_%"))
                    .subquery()
                )
            )
        )
        result = session.execute(
            delete(StockMonitorConfig).where(StockMonitorConfig.user_id.like("test_user_%"))
        )
        session.commit()
        logger.info(f"Cleaned up {result.rowcount} test config(s)")


def test_monitor_notification():
    """Test monitor notification with simulated price change."""
    from src.monitor.engine import get_monitor_engine
    from src.services.stock_monitor_service import get_monitor_service
    from src.config import get_config

    config = get_config()
    service = get_monitor_service()
    engine = get_monitor_engine()

    import time
    test_user_id = f"test_user_{int(time.time())}"
    test_chat_id = "oc_c4f728163782081095ba208e2cd0ae3e"

    logger.info("=" * 60)
    logger.info("Stock Monitor Notification Test")
    logger.info("=" * 60)

    # Cleanup old test data
    logger.info("\n--- Cleaning up old test data ---")
    cleanup_test_data()

    # 检查飞书配置
    logger.info("\n--- 检查飞书配置 ---")
    feishu_app_id = getattr(config, 'feishu_app_id', None)
    feishu_app_secret = getattr(config, 'feishu_app_secret', None)

    # 如果配置文件中没有，使用用户提供的配置
    if not feishu_app_id or not feishu_app_secret:
        feishu_app_id = "cli_a924f365e2f89cc0"
        feishu_app_secret = "Fq1fQ3kyEoa6zneJHbtsuA3kQKiybVyt"
        logger.info("使用用户提供的飞书配置")

    logger.info(f"FEISHU_APP_ID: {feishu_app_id[:10] + '***' if feishu_app_id else 'Not set'}")
    logger.info(f"FEISHU_APP_SECRET: {'***' + feishu_app_secret[-4:] if feishu_app_secret else 'Not set'}")

    # 初始化飞书客户端
    if feishu_app_id and feishu_app_secret:
        from bot.platforms.feishu_stream import FeishuReplyClient
        client = FeishuReplyClient(feishu_app_id, feishu_app_secret)
        service.set_feishu_client(client)
        logger.info("飞书客户端初始化成功")
    else:
        logger.warning("飞书配置缺失，将只打印日志不发送通知")

    logger.info("\n--- Test 1: Add Realtime Monitor for HK Stock 康龙化成 (03759.HK) ---")
    success, msg = service.add_monitor(
        stock_code="03759.HK",
        user_id=test_user_id,
        chat_id=test_chat_id,
        monitor_type="realtime",
        level1_threshold=3.5,
        level2_threshold=2.0,
        level3_threshold=0.5,
        window_minutes=10,
    )
    logger.info(f"Result: success={success}, message={msg}")

    logger.info("\n--- Test 2: Add Realtime Monitor for US Stock Oracle (ORCL) ---")
    success, msg = service.add_monitor(
        stock_code="ORCL",
        user_id=test_user_id,
        chat_id=test_chat_id,
        monitor_type="realtime",
        level1_threshold=3.5,
        level2_threshold=2.0,
        level3_threshold=0.5,
        window_minutes=10,
    )
    logger.info(f"Result: success={success}, message={msg}")

    logger.info("\n--- Test 3: List All Monitors ---")
    monitors = service.list_monitors(test_user_id)
    logger.info(f"Found {len(monitors)} monitors:")
    for m in monitors:
        logger.info(
            f"  - {m.stock_name} ({m.config.stock_code}): type={m.config.monitor_type}"
        )

    logger.info("\n--- Test 4: Run First Check Cycle (Initialize baseline) ---")
    results = engine.check_all_monitors()
    for r in results:
        logger.info(
            f"  - {r.stock_name}({r.stock_code}): "
            f"today_start_price={r.today_start_price}, window_baseline_price={r.window_baseline_price}"
        )

    logger.info("\n--- Test 5: Simulate Price Change > 0.5% (level 3) and > 2% (level 2) ---")
    # 直接修改数据库中的基准价格，模拟涨跌幅
    from src.repositories.stock_monitor_repo import StockMonitorRepository
    from src.monitor.models import get_now_cn
    repo = StockMonitorRepository()

    for monitor in monitors:
        config_obj = monitor.config
        state = repo.get_state(config_obj.id)
        if state and state.last_price:
            # 模拟今日起始价格为当前价格的 97%（模拟上涨3% - 触发level 1和level 2）
            simulated_today_start = state.last_price * 0.97
            # 模拟窗口基准价格为当前价格的 99%（模拟上涨1% - 触发level 3）
            simulated_window_baseline = state.last_price * 0.99
            logger.info(
                f"  Simulating {config_obj.stock_code}: "
                f"today_start={simulated_today_start:.2f} -> current={state.last_price:.2f} "
                f"(today_change={((state.last_price - simulated_today_start) / simulated_today_start * 100):.2f}%)"
            )
            logger.info(
                f"  window_baseline={simulated_window_baseline:.2f} -> current={state.last_price:.2f} "
                f"(window_change={((state.last_price - simulated_window_baseline) / simulated_window_baseline * 100):.2f}%)"
            )
            # 更新基准价格
            repo.update_state(
                config_obj.id,
                today_start_price=simulated_today_start,
                today_start_time=get_now_cn(),
                baseline_price=simulated_window_baseline,
                baseline_time=get_now_cn(),
                alert_level1_triggered=False,
                alert_level2_triggered=False,
                alert_level3_triggered=False,
            )

    logger.info("\n--- Test 6: Run Check Cycle (Should trigger alerts) ---")
    results = engine.check_all_monitors()
    for r in results:
        logger.info(
            f"  - {r.stock_name}({r.stock_code}): price={r.current_price}, "
            f"today_change={r.today_change_pct:.2f}%, window_change={r.window_change_pct:.2f}%, "
            f"L1={'TRIGGERED' if r.triggered_level1 else 'N'}, "
            f"L2={'TRIGGERED' if r.triggered_level2 else 'N'}, "
            f"L3={'TRIGGERED' if r.triggered_level3 else 'N'}, "
            f"alert_sent={r.alert_sent}"
        )

    logger.info("\n--- Test 7: Check Alert History ---")
    alerts = service.get_alert_history(test_user_id, hours=1)
    logger.info(f"Alerts in last 1h: {len(alerts)}")
    for a in alerts:
        logger.info(f"  - {a['stock_code']}: {a['alert_type']} {a['change_pct']:.2f}%")

    logger.info("\n--- Test 8: Cleanup - Remove Monitors ---")
    service.remove_monitor("03759.HK", test_user_id)
    service.remove_monitor("ORCL", test_user_id)
    logger.info("Monitors removed")

    logger.info("\n" + "=" * 60)
    logger.info("Test completed!")
    logger.info("=" * 60)

    return True


if __name__ == "__main__":
    test_monitor_notification()
