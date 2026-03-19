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


def test_monitor_notification():
    """Test monitor notification with simulated price change."""
    from src.monitor.engine import get_monitor_engine
    from src.services.stock_monitor_service import get_monitor_service
    from src.config import get_config

    config = get_config()
    service = get_monitor_service()
    engine = get_monitor_engine()

    test_user_id = "test_user_001"
    test_chat_id = "test_chat_001"

    logger.info("=" * 60)
    logger.info("Stock Monitor Notification Test")
    logger.info("=" * 60)

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
        window_minutes=10,
    )
    logger.info(f"Result: success={success}, message={msg}")

    logger.info("\n--- Test 2: Add Realtime Monitor for US Stock Oracle (ORCL) ---")
    success, msg = service.add_monitor(
        stock_code="ORCL",
        user_id=test_user_id,
        chat_id=test_chat_id,
        monitor_type="realtime",
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
            f"  - {r.stock_name}({r.stock_code}): baseline_price={r.baseline_price}"
        )

    logger.info("\n--- Test 5: Simulate Price Change > 2% ---")
    # 直接修改数据库中的基准价格，模拟涨跌幅超过2%
    from src.repositories.stock_monitor_repo import StockMonitorRepository
    repo = StockMonitorRepository()

    for monitor in monitors:
        config_obj = monitor.config
        state = repo.get_state(config_obj.id)
        if state and state.baseline_price:
            # 模拟基准价格为当前价格的 97%（模拟上涨3%）
            simulated_baseline = state.last_price * 0.97 if state.last_price else 100
            logger.info(
                f"  Simulating {config_obj.stock_code}: "
                f"baseline={simulated_baseline:.2f} -> current={state.last_price:.2f} "
                f"(change={((state.last_price - simulated_baseline) / simulated_baseline * 100):.2f}%)"
            )
            # 更新基准价格
            from datetime import datetime
            repo.update_state(
                config_obj.id,
                baseline_price=simulated_baseline,
                baseline_time=datetime.now(),
                alert_2pct_triggered=False,  # 重置触发标志
            )

    logger.info("\n--- Test 6: Run Check Cycle (Should trigger 2% alert) ---")
    results = engine.check_all_monitors()
    for r in results:
        logger.info(
            f"  - {r.stock_name}({r.stock_code}): price={r.current_price}, "
            f"change={r.change_pct:.2f}%, 2%={'TRIGGERED' if r.triggered_2pct else 'N'}, "
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
