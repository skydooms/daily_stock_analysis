# -*- coding: utf-8 -*-
"""
Stock Real-time Monitor Script.

Usage:
    # Use default stocks
    python start_stock_monitor.py --notify-start

    # Specify stocks
    python start_stock_monitor.py -s 03759.HK ORCL BABA MU --notify-start

    # Simulation mode
    python start_stock_monitor.py -s 03759.HK ORCL --type simulation

    # Custom parameters
    python start_stock_monitor.py -s 03759.HK ORCL BABA MU \
        --interval 30 \
        --window 5 \
        --level1 3.0 \
        --level2 1.5 \
        --notify-start
"""

import argparse
import logging
import signal
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# China timezone (UTC+8)
TZ_CN = timezone(timedelta(hours=8))


def get_now_cn() -> datetime:
    """Get current time in China timezone (UTC+8)."""
    return datetime.now(TZ_CN)


def format_time_cn(dt: datetime) -> str:
    """Format datetime in China timezone."""
    if dt is None:
        return "N/A"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_CN)
    return dt.strftime("%Y-%m-%d %H:%M:%S CST")


def send_startup_notification(
    feishu_client,
    chat_id: str,
    stocks: list,
    monitor_type: str,
    interval: int,
    window: int,
    level1: float,
    level2: float,
    level3: float,
) -> bool:
    """Send startup notification to Feishu."""
    now = get_now_cn()
    stock_list = ", ".join(stocks)

    message = f"""🚀 **股票监控已启动**

**监控股票:** {stock_list}
**监控类型:** {"🔴 实时监控" if monitor_type == "realtime" else "🟡 模拟监控"}
**监控间隔:** {interval}秒
**时间窗口:** {window}分钟
**阈值设置:**
  - L1 (今日涨跌): {level1}%
  - L2 (今日涨跌): {level2}%
  - L3 (窗口涨跌): {level3}%
**启动时间:** {format_time_cn(now)}

_监控运行中，按 Ctrl+C 停止_
"""
    try:
        success = feishu_client.send_to_chat(chat_id, message)
        if success:
            logger.info(f"[通知] 启动通知已发送到飞书")
        return success
    except Exception as e:
        logger.error(f"[通知] 发送启动通知失败: {e}")
        return False


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="股票实时监控脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认股票列表
  python start_stock_monitor.py --notify-start

  # 指定股票列表
  python start_stock_monitor.py -s 03759.HK ORCL BABA MU --notify-start

  # 模拟监控模式
  python start_stock_monitor.py -s 03759.HK ORCL --type simulation

  # 自定义参数
  python start_stock_monitor.py -s 03759.HK ORCL BABA MU --interval 30 --window 5 --notify-start
        """,
    )
    parser.add_argument(
        "--stocks", "-s",
        nargs="+",
        help="股票代码列表，如: 03759.HK ORCL BABA MU",
    )
    parser.add_argument(
        "--type", "-t",
        choices=["realtime", "simulation"],
        default="realtime",
        help="监控类型 (default: realtime)",
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=60,
        help="监控间隔(秒) (default: 60)",
    )
    parser.add_argument(
        "--window", "-w",
        type=int,
        default=10,
        help="时间窗口(分钟) (default: 10)",
    )
    parser.add_argument(
        "--level1",
        type=float,
        default=3.5,
        help="一级阈值(%%) - 今日涨跌 (default: 3.5)",
    )
    parser.add_argument(
        "--level2",
        type=float,
        default=2.0,
        help="二级阈值(%%) - 今日涨跌 (default: 2.0)",
    )
    parser.add_argument(
        "--level3",
        type=float,
        default=0.2,
        help="三级阈值(%%) - 窗口涨跌 (default: 0.2)",
    )
    parser.add_argument(
        "--chat-id",
        type=str,
        default="oc_c4f728163782081095ba208e2cd0ae3e",
        help="飞书 chat_id",
    )
    parser.add_argument(
        "--notify-start",
        action="store_true",
        help="启动时发送通知",
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Default stocks if not specified
    default_stocks = [
        "03759.HK",  # 康龙化成 (港股)
        "BABA",      # 阿里巴巴 (美股)
        "ORCL",      # 甲骨文 (美股)
        "MU",        # 美光科技 (美股)
    ]
    stocks = args.stocks if args.stocks else default_stocks

    from src.services.stock_monitor_service import get_monitor_service
    from src.config import get_config

    config = get_config()
    service = get_monitor_service()

    # Check Feishu configuration
    feishu_app_id = getattr(config, "feishu_app_id", None)
    feishu_app_secret = getattr(config, "feishu_app_secret", None)

    # Use the user-provided Feishu config if not in settings
    if not feishu_app_id or not feishu_app_secret:
        feishu_app_id = "cli_a924f365e2f89cc0"
        feishu_app_secret = "Fq1fQ3kyEoa6zneJHbtsuA3kQKiybVyt"
        logger.info("Using user-provided Feishu config")

    # Initialize Feishu client
    feishu_client = None
    if feishu_app_id and feishu_app_secret:
        from bot.platforms.feishu_stream import FeishuReplyClient

        feishu_client = FeishuReplyClient(feishu_app_id, feishu_app_secret)
        service.set_feishu_client(feishu_client)
        logger.info("Feishu client initialized")

    test_user_id = "monitor_user_001"
    chat_id = args.chat_id

    logger.info("=" * 60)
    logger.info("Stock Real-time Monitor")
    logger.info("=" * 60)
    logger.info(f"Stocks: {', '.join(stocks)}")
    logger.info(f"Type: {args.type}")
    logger.info(f"Interval: {args.interval}s")
    logger.info(f"Window: {args.window}min")
    logger.info(f"Thresholds: L1={args.level1}%, L2={args.level2}%, L3={args.level3}%")
    logger.info("=" * 60)

    # Add monitors
    for stock_code in stocks:
        logger.info(f"\n--- Adding monitor for {stock_code} ---")
        success, msg = service.add_monitor(
            stock_code=stock_code,
            user_id=test_user_id,
            chat_id=chat_id,
            monitor_type=args.type,
            level1_threshold=args.level1,
            level2_threshold=args.level2,
            level3_threshold=args.level3,
            window_minutes=args.window,
        )
        logger.info(f"Result: success={success}, message={msg}")

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
    success, msg = service.start_monitoring(interval_seconds=args.interval)
    logger.info(f"Result: success={success}, message={msg}")

    if not success:
        logger.error(f"Failed to start monitoring: {msg}")
        return 1

    # Get engine status
    logger.info("\n--- Engine status ---")
    status = service.get_engine_status()
    logger.info(f"Status: {status}")

    # Send startup notification
    if args.notify_start and feishu_client:
        send_startup_notification(
            feishu_client=feishu_client,
            chat_id=chat_id,
            stocks=stocks,
            monitor_type=args.type,
            interval=args.interval,
            window=args.window,
            level1=args.level1,
            level2=args.level2,
            level3=args.level3,
        )

    logger.info("\n" + "=" * 60)
    logger.info("Monitoring started! Press Ctrl+C to stop.")
    logger.info("=" * 60)

    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("\n--- Stopping monitoring ---")
        service.stop_monitoring()
        logger.info("Monitoring stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n--- Stopping monitoring ---")
        service.stop_monitoring()
        logger.info("Monitoring stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
