# -*- coding: utf-8 -*-
"""
Test script for stock monitor functionality.

Tests:
1. Add simulation monitor for HK stock 康龙化成 (03759.HK)
2. Add realtime monitor for US stock Oracle (ORCL)
3. List monitors
4. Check stock quotes
5. Run monitoring cycle
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


def test_monitor():
    """Run monitor tests."""
    from src.monitor.engine import get_monitor_engine
    from src.services.stock_monitor_service import get_monitor_service

    service = get_monitor_service()
    engine = get_monitor_engine()

    test_user_id = "test_user_001"
    test_chat_id = "test_chat_001"

    logger.info("=" * 60)
    logger.info("Stock Monitor Test")
    logger.info("=" * 60)

    logger.info("\n--- Test 1: Add Simulation Monitor for HK Stock 康龙化成 (03759.HK) ---")
    success, msg = service.add_monitor(
        stock_code="03759.HK",
        user_id=test_user_id,
        chat_id=test_chat_id,
        monitor_type="simulation",
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
        level1_threshold=4.0,
        level2_threshold=2.5,
        level3_threshold=0.8,
        window_minutes=10,
    )
    logger.info(f"Result: success={success}, message={msg}")

    logger.info("\n--- Test 3: List All Monitors ---")
    monitors = service.list_monitors(test_user_id)
    logger.info(f"Found {len(monitors)} monitors:")
    for m in monitors:
        logger.info(
            f"  - {m.stock_name} ({m.config.stock_code}): type={m.config.monitor_type}, "
            f"window={m.config.window_minutes}min"
        )

    logger.info("\n--- Test 4: Check Single Stock Quote (康龙化成) ---")
    from data_provider.base import DataFetcherManager

    fetcher = DataFetcherManager()
    quote = fetcher.get_realtime_quote("03759.HK")
    if quote:
        logger.info(
            f"Quote for 03759.HK: name={quote.name}, price={quote.price}, change_pct={quote.change_pct}"
        )
    else:
        logger.warning("No quote data for 03759.HK")

    logger.info("\n--- Test 5: Check Single Stock Quote (Oracle) ---")
    quote = fetcher.get_realtime_quote("ORCL")
    if quote:
        logger.info(
            f"Quote for ORCL: name={quote.name}, price={quote.price}, change_pct={quote.change_pct}"
        )
    else:
        logger.warning("No quote data for ORCL")

    logger.info("\n--- Test 6: Get Engine Status ---")
    status = service.get_engine_status()
    logger.info(f"Engine status: {status}")

    logger.info("\n--- Test 7: Run Single Check Cycle ---")
    results = engine.check_all_monitors()
    logger.info(f"Check results: {len(results)} stocks checked")
    for r in results:
        today_change_str = f"{r.today_change_pct:.2f}%" if r.today_change_pct is not None else "N/A"
        window_change_str = f"{r.window_change_pct:.2f}%" if r.window_change_pct is not None else "N/A"
        logger.info(
            f"  - {r.stock_name}({r.stock_code}): price={r.current_price}, "
            f"today_change={today_change_str}, window_change={window_change_str}, "
            f"L1={'Y' if r.triggered_level1 else 'N'}, "
            f"L2={'Y' if r.triggered_level2 else 'N'}, "
            f"L3={'Y' if r.triggered_level3 else 'N'}"
        )

    logger.info("\n--- Test 8: Cleanup - Remove Monitors ---")
    success1, msg1 = service.remove_monitor("03759.HK", test_user_id)
    success2, msg2 = service.remove_monitor("ORCL", test_user_id)
    logger.info(f"Removed 03759.HK: {success1}, {msg1}")
    logger.info(f"Removed ORCL: {success2}, {msg2}")

    logger.info("\n" + "=" * 60)
    logger.info("All tests completed!")
    logger.info("=" * 60)

    return True


if __name__ == "__main__":
    test_monitor()
