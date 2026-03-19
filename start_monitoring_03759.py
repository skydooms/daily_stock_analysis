# -*- coding: utf-8 -*-
"""
Start monitoring for 03759.HK (康龙化成).
"""

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def start_monitoring():
    """Start monitoring for 03759.HK."""
    from src.services.stock_monitor_service import get_monitor_service
    from src.config import get_config

    config = get_config()
    service = get_monitor_service()

    # Check Feishu configuration
    feishu_app_id = getattr(config, 'feishu_app_id', None)
    feishu_app_secret = getattr(config, 'feishu_app_secret', None)

    # Use the user-provided Feishu config if not in settings
    if not feishu_app_id or not feishu_app_secret:
        feishu_app_id = "cli_a924f365e2f89cc0"
        feishu_app_secret = "Fq1fQ3kyEoa6zneJHbtsuA3kQKiybVyt"
        logger.info("Using user-provided Feishu config")

    # Initialize Feishu client
    if feishu_app_id and feishu_app_secret:
        from bot.platforms.feishu_stream import FeishuReplyClient
        client = FeishuReplyClient(feishu_app_id, feishu_app_secret)
        service.set_feishu_client(client)
        logger.info("Feishu client initialized")

    # Test chat ID from earlier tests
    test_chat_id = "oc_c4f728163782081095ba208e2cd0ae3e"
    test_user_id = "monitor_user_001"

    logger.info("=" * 60)
    logger.info("Starting monitoring for 03759.HK (康龙化成)")
    logger.info("=" * 60)

    # Add monitor
    logger.info("\n--- Adding monitor for 03759.HK ---")
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

    if not success:
        logger.error(f"Failed to add monitor: {msg}")
        return False

    # List monitors
    logger.info("\n--- Current monitors ---")
    monitors = service.list_monitors(test_user_id)
    for m in monitors:
        logger.info(
            f"  - {m.stock_name} ({m.config.stock_code}): "
            f"type={m.config.monitor_type}, window={m.config.window_minutes}min, "
            f"L1={m.config.level1_threshold}%, L2={m.config.level2_threshold}%, L3={m.config.level3_threshold}%"
        )

    # Start monitoring engine
    logger.info("\n--- Starting monitoring engine ---")
    success, msg = service.start_monitoring(interval_seconds=60)
    logger.info(f"Result: success={success}, message={msg}")

    if not success:
        logger.error(f"Failed to start monitoring: {msg}")
        return False

    # Get engine status
    logger.info("\n--- Engine status ---")
    status = service.get_engine_status()
    logger.info(f"Status: {status}")

    logger.info("\n" + "=" * 60)
    logger.info("Monitoring started! Press Ctrl+C to stop.")
    logger.info("=" * 60)

    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n--- Stopping monitoring ---")
        service.stop_monitoring()
        logger.info("Monitoring stopped.")

    return True


if __name__ == "__main__":
    start_monitoring()

