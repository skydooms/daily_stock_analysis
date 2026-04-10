# -*- coding: utf-8 -*-
"""
股票监控启动脚本

功能：
- 启动并管理股票市场监控服务
- 支持命令行参数配置监控参数
- 监控唯一性保障（重复添加时提示用户选择）
- 完善的日志系统（控制台+文件，按日期轮转）
- 优雅的错误处理和资源清理

使用示例：
    python start_stock_monitor.py -s 600519,300759 -w 15 --interval 30
    python start_stock_monitor.py --list
    python start_stock_monitor.py -s 600519 --remove
    python start_stock_monitor.py -s 600519 --force
"""

import argparse
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.logging_config import setup_logging

# 默认配置
DEFAULT_USER_ID = "monitor_user_001"
DEFAULT_CHAT_ID = "oc_c4f728163782081095ba208e2cd0ae3e"
DEFAULT_FEISHU_APP_ID = "cli_a924f365e2f89cc0"
DEFAULT_FEISHU_APP_SECRET = "Fq1fQ3kyEoa6zneJHbtsuA3kQKiybVyt"

# China timezone (UTC+8)
TZ_CN = timezone(timedelta(hours=8))

logger = logging.getLogger(__name__)


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


def setup_argument_parser() -> argparse.ArgumentParser:
    """
    设置命令行参数解析器

    Returns:
        argparse.ArgumentParser: 配置好的参数解析器
    """
    parser = argparse.ArgumentParser(
        prog="start_stock_monitor",
        description="股票监控服务启动脚本 - 支持实时监控股票价格波动并发送飞书通知",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例用法:
  # 添加监控（单个股票）
  python start_stock_monitor.py -s 600519 -t realtime -w 10

  # 添加监控（多个股票，逗号分隔）
  python start_stock_monitor.py -s 600519,300759,03759.HK -w 15 --interval 30

  # 添加监控（空格分隔多个股票）
  python start_stock_monitor.py -s 03759.HK ORCL BABA MU --notify-start

  # 列出当前所有监控
  python start_stock_monitor.py --list

  # 移除指定股票监控
  python start_stock_monitor.py -s 600519 --remove

  # 强制替换已存在的监控（跳过确认）
  python start_stock_monitor.py -s 600519 --force

监控类型说明:
  realtime    - 实时监控，触发三级预警通知
  simulation  - 模拟监控，仅记录不发送通知

预警级别说明:
  一级预警 (L1): 今日涨跌幅超过 threshold-level1（默认3.5%）
  二级预警 (L2): 今日涨跌幅超过 threshold-level2（默认2.0%）
  三级预警 (L3): 时间窗口内涨跌幅超过 threshold-level3（默认0.5%）
        """,
    )

    # 股票代码参数（支持逗号分隔和空格分隔）
    parser.add_argument(
        "-s", "--stock-code", "--stocks",
        nargs="*",
        help="股票代码（支持多个，逗号分隔或空格分隔，如: 600519,300759 或 600519 300759）",
    )

    # 监控类型参数
    parser.add_argument(
        "-t", "--type", "--monitor-type",
        type=str,
        choices=["realtime", "simulation"],
        default="realtime",
        help="监控类型: realtime（实时监控）或 simulation（模拟监控），默认: realtime",
    )

    # 时间窗口参数
    parser.add_argument(
        "-w", "--window",
        type=int,
        default=10,
        help="监控时间窗口（分钟），用于三级预警计算，范围: 1-120，默认: 10",
    )

    # 检查间隔参数
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=60,
        help="监控检查间隔（秒），默认: 60",
    )

    # 预警阈值参数
    parser.add_argument(
        "--level1", "--threshold-level1",
        type=float,
        default=3.5,
        help="一级预警阈值（百分比），今日涨跌幅超过此值触发一级预警，默认: 3.5",
    )
    parser.add_argument(
        "--level2", "--threshold-level2",
        type=float,
        default=2.0,
        help="二级预警阈值（百分比），今日涨跌幅超过此值触发二级预警，默认: 2.0",
    )
    parser.add_argument(
        "--level3", "--threshold-level3",
        type=float,
        default=0.5,
        help="三级预警阈值（百分比），窗口内涨跌幅超过此值触发三级预警，默认: 0.5",
    )

    # 飞书配置参数（可选，覆盖默认值）
    parser.add_argument(
        "--chat-id",
        type=str,
        default=DEFAULT_CHAT_ID,
        help=f"飞书聊天ID，用于发送预警通知，默认: {DEFAULT_CHAT_ID}",
    )
    parser.add_argument(
        "--feishu-app-id",
        type=str,
        default=DEFAULT_FEISHU_APP_ID,
        help="飞书应用ID（可选，覆盖默认值）",
    )
    parser.add_argument(
        "--feishu-app-secret",
        type=str,
        default=DEFAULT_FEISHU_APP_SECRET,
        help="飞书应用密钥（可选，覆盖默认值）",
    )

    # 操作模式参数
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出当前所有监控配置",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="移除指定股票的监控（需配合 -s 参数指定股票代码）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制替换已存在的监控（跳过交互确认）",
    )
    parser.add_argument(
        "--notify-start",
        action="store_true",
        help="启动时发送飞书通知",
    )

    return parser


def validate_stock_code(stock_code: str) -> Tuple[bool, str]:
    """
    验证股票代码格式是否有效

    Args:
        stock_code: 股票代码字符串

    Returns:
        Tuple[bool, str]: (是否有效, 错误消息或规范化后的代码)
    """
    stock_code = stock_code.strip().upper()

    # A股格式: 6位数字 (如 600519, 300759)
    if len(stock_code) == 6 and stock_code.isdigit():
        return True, stock_code

    # 港股格式: 5位数字 + .HK (如 03759.HK)
    if stock_code.endswith(".HK"):
        hk_code = stock_code[:-3]
        if len(hk_code) in [4, 5] and hk_code.isdigit():
            return True, stock_code

    # 美股格式: 字母 (如 AAPL, ORCL)
    if stock_code.isalpha() and len(stock_code) <= 5:
        return True, stock_code

    return False, f"无效的股票代码格式: {stock_code}"


def parse_stock_codes(stock_args: Optional[List[str]]) -> List[str]:
    """
    解析股票代码参数（支持逗号分隔和空格分隔）

    Args:
        stock_args: 股票代码参数列表

    Returns:
        List[str]: 规范化后的股票代码列表
    """
    if not stock_args:
        return []

    stock_codes = []
    for arg in stock_args:
        # 处理逗号分隔的情况
        if "," in arg:
            for code in arg.split(","):
                valid, result = validate_stock_code(code)
                if valid:
                    stock_codes.append(result)
                else:
                    logger.warning(f"跳过无效股票代码: {code}")
        else:
            valid, result = validate_stock_code(arg)
            if valid:
                stock_codes.append(result)
            else:
                logger.warning(f"跳过无效股票代码: {arg}")

    return stock_codes


def validate_arguments(args: argparse.Namespace) -> Tuple[bool, List[str]]:
    """
    验证命令行参数的有效性

    Args:
        args: 解析后的参数对象

    Returns:
        Tuple[bool, List[str]]: (是否有效, 错误消息列表)
    """
    errors = []

    # 如果只是列出监控，无需验证其他参数
    if args.list:
        return True, []

    # 必须指定股票代码（除非是 --list 操作）
    if not args.stock_code:
        errors.append("必须指定股票代码 (-s/--stock-code)")

    # 验证阈值范围
    for level_name, threshold in [
        ("level1", args.level1),
        ("level2", args.level2),
        ("level3", args.level3),
    ]:
        if not (0 < threshold < 20):
            errors.append(f"阈值 {level_name} 必须在 0-20 范围内，当前值: {threshold}")

    # 验证时间窗口
    if not (1 <= args.window <= 120):
        errors.append(f"时间窗口必须在 1-120 分钟范围内，当前值: {args.window}")

    # 验证检查间隔
    if args.interval < 10:
        errors.append(f"检查间隔不能小于 10 秒，当前值: {args.interval}")

    return len(errors) == 0, errors


def get_monitor_service_with_feishu(
    feishu_app_id: str,
    feishu_app_secret: str,
) -> Tuple[Optional[object], bool, str]:
    """
    获取监控服务并初始化飞书客户端

    Args:
        feishu_app_id: 飞书应用ID
        feishu_app_secret: 飞书应用密钥

    Returns:
        Tuple[service, success, message]: (服务实例, 是否成功, 消息)
    """
    try:
        from src.services.stock_monitor_service import get_monitor_service
        from bot.platforms.feishu_stream import FeishuReplyClient

        service = get_monitor_service()

        # 初始化飞书客户端
        if feishu_app_id and feishu_app_secret:
            client = FeishuReplyClient(feishu_app_id, feishu_app_secret)
            service.set_feishu_client(client)
            logger.info("飞书客户端初始化成功")

        return service, True, "服务初始化成功"
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        return None, False, f"服务初始化失败: {e}"


def check_existing_monitor(
    service: object,
    stock_code: str,
    user_id: str,
) -> Optional[object]:
    """
    检查股票是否已在监控列表中

    Args:
        service: 监控服务实例
        stock_code: 股票代码
        user_id: 用户ID

    Returns:
        MonitorInfo 或 None
    """
    try:
        return service.get_monitor_status(user_id, stock_code)
    except Exception as e:
        logger.warning(f"查询监控状态失败: {e}")
        return None


def display_existing_monitor_info(monitor_info: object) -> None:
    """
    显示已存在监控的详细信息

    Args:
        monitor_info: MonitorInfo 对象
    """
    print("\n" + "=" * 60)
    print("检测到该股票已在监控列表中：")
    print("=" * 60)

    config = monitor_info.config
    print(f"  股票名称: {monitor_info.stock_name}")
    print(f"  股票代码: {config.stock_code}")
    print(f"  监控类型: {config.monitor_type}")
    print(f"  时间窗口: {config.window_minutes} 分钟")
    print(f"  一级阈值: {config.level1_threshold}%")
    print(f"  二级阈值: {config.level2_threshold}%")
    print(f"  三级阈值: {config.level3_threshold}%")

    if monitor_info.current_price:
        print(f"  当前价格: ¥{monitor_info.current_price:.2f}")
    if monitor_info.change_pct is not None:
        print(f"  涨跌幅:   {monitor_info.change_pct:+.2f}%")

    if config.created_at:
        print(f"  创建时间: {format_time_cn(config.created_at)}")

    print("=" * 60)


def prompt_user_action() -> str:
    """
    提示用户选择操作

    Returns:
        用户选择 ('1' 或 '2')
    """
    print("\n请选择操作：")
    print("  [1] 终止旧监控并启动新监控")
    print("  [2] 保留现有监控，取消本次操作")
    print()

    while True:
        try:
            choice = input("请输入选择 (1/2): ").strip()
            if choice in ["1", "2"]:
                return choice
            print("无效输入，请输入 1 或 2")
        except (EOFError, KeyboardInterrupt):
            print("\n取消操作")
            return "2"


def handle_duplicate_monitor(
    service: object,
    stock_code: str,
    user_id: str,
    force: bool,
    new_params: Dict,
) -> Tuple[bool, str]:
    """
    处理重复监控的情况

    Args:
        service: 监控服务实例
        stock_code: 股票代码
        user_id: 用户ID
        force: 是否强制替换
        new_params: 新监控参数

    Returns:
        Tuple[bool, str]: (是否继续添加, 消息)
    """
    existing = check_existing_monitor(service, stock_code, user_id)

    if not existing:
        # 没有重复监控，可以直接添加
        return True, "无重复监控"

    # 显示已存在监控信息
    display_existing_monitor_info(existing)

    if force:
        # 强制模式，直接移除旧监控
        logger.info(f"[强制模式] 移除旧监控: {stock_code}")
        success, msg = service.remove_monitor(stock_code, user_id)
        if success:
            logger.info(f"旧监控已移除: {msg}")
            return True, f"已移除旧监控，准备添加新监控"
        else:
            return False, f"移除旧监控失败: {msg}"

    # 非强制模式，提示用户选择
    choice = prompt_user_action()

    if choice == "1":
        # 用户选择终止旧监控
        logger.info(f"[用户选择] 移除旧监控: {stock_code}")
        success, msg = service.remove_monitor(stock_code, user_id)
        if success:
            logger.info(f"旧监控已移除: {msg}")
            return True, f"已移除旧监控，准备添加新监控"
        else:
            return False, f"移除旧监控失败: {msg}"
    else:
        # 用户选择保留现有监控
        return False, "用户选择保留现有监控"


def send_startup_notification(
    service: object,
    feishu_client: object,
    chat_id: str,
    stocks: List[str],
    monitor_type: str,
    interval: int,
    window: int,
    level1: float,
    level2: float,
    level3: float,
) -> bool:
    """
    发送启动通知到飞书

    Args:
        service: 监控服务实例
        feishu_client: 飞书客户端
        chat_id: 飞书聊天ID
        stocks: 股票代码列表
        monitor_type: 监控类型
        interval: 检查间隔
        window: 时间窗口
        level1-3: 预警阈值

    Returns:
        bool: 是否发送成功
    """
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
**进程ID:** {os.getpid()}

_监控运行中，按 Ctrl+C 停止_
"""
    try:
        success = feishu_client.send_to_chat(chat_id, message)
        if success:
            logger.info("[通知] 启动通知已发送到飞书")
        return success
    except Exception as e:
        logger.error(f"[通知] 发送启动通知失败: {e}")
        return False


def add_monitors(
    service: object,
    stock_codes: List[str],
    args: argparse.Namespace,
    user_id: str,
) -> List[Tuple[str, bool, str]]:
    """
    批量添加股票监控

    Args:
        service: 监控服务实例
        stock_codes: 股票代码列表
        args: 命令行参数
        user_id: 用户ID

    Returns:
        List[Tuple[str, bool, str]]: 每个股票的添加结果列表
    """
    results = []

    for stock_code in stock_codes:
        # 检查并处理重复监控
        can_add, msg = handle_duplicate_monitor(
            service,
            stock_code,
            user_id,
            args.force,
            {
                "monitor_type": args.type,
                "window_minutes": args.window,
                "threshold_level1": args.level1,
                "threshold_level2": args.level2,
                "threshold_level3": args.level3,
            },
        )

        if not can_add:
            results.append((stock_code, False, msg))
            continue

        # 添加新监控
        logger.info(f"添加监控: {stock_code}")
        success, add_msg = service.add_monitor(
            stock_code=stock_code,
            user_id=user_id,
            chat_id=args.chat_id,
            monitor_type=args.type,
            level1_threshold=args.level1,
            level2_threshold=args.level2,
            level3_threshold=args.level3,
            window_minutes=args.window,
        )

        results.append((stock_code, success, add_msg))
        if success:
            logger.info(f"监控添加成功: {stock_code} - {add_msg}")
        else:
            logger.error(f"监控添加失败: {stock_code} - {add_msg}")

    return results


def remove_monitors(
    service: object,
    stock_codes: List[str],
    user_id: str,
) -> List[Tuple[str, bool, str]]:
    """
    批量移除股票监控

    Args:
        service: 监控服务实例
        stock_codes: 股票代码列表
        user_id: 用户ID

    Returns:
        List[Tuple[str, bool, str]]: 每个股票的移除结果列表
    """
    results = []

    for stock_code in stock_codes:
        logger.info(f"移除监控: {stock_code}")

        success, msg = service.remove_monitor(stock_code, user_id)
        results.append((stock_code, success, msg))

        if success:
            logger.info(f"监控移除成功: {stock_code} - {msg}")
        else:
            logger.warning(f"监控移除失败: {stock_code} - {msg}")

    return results


def list_monitors(service: object, user_id: str) -> None:
    """
    列出当前所有监控配置

    Args:
        service: 监控服务实例
        user_id: 用户ID
    """
    print("\n" + "=" * 60)
    print("当前监控列表")
    print("=" * 60)

    try:
        monitors = service.list_monitors(user_id)

        if not monitors:
            print("暂无监控配置")
            return

        for i, m in enumerate(monitors, 1):
            type_icon = "🔴" if m.config.monitor_type == "realtime" else "🟡"
            status = "运行中" if m.config.is_active else "已暂停"

            price_str = f"¥{m.current_price:.2f}" if m.current_price else "--"
            change_str = f"{m.change_pct:+.2f}%" if m.change_pct is not None else "--"

            print(f"\n{i}. {type_icon} {m.stock_name} ({m.config.stock_code})")
            print(f"   价格: {price_str} | 涨跌: {change_str}")
            print(f"   类型: {m.config.monitor_type} | 窗口: {m.config.window_minutes}分钟 | 状态: {status}")
            print(f"   一级阈值: {m.config.level1_threshold}% | 二级阈值: {m.config.level2_threshold}% | 三级阈值: {m.config.level3_threshold}%")
            if m.config.created_at:
                print(f"   创建时间: {format_time_cn(m.config.created_at)}")

        print("\n" + "=" * 60)
        print(f"共 {len(monitors)} 个监控")
        print("=" * 60)

    except Exception as e:
        logger.error(f"列出监控失败: {e}")
        print(f"\n列出监控失败: {e}")


def start_monitoring_loop(
    service: object,
    args: argparse.Namespace,
    feishu_client: Optional[object],
    stock_codes: List[str],
    user_id: str,
) -> None:
    """
    启动监控循环并保持运行

    Args:
        service: 监控服务实例
        args: 命令行参数
        feishu_client: 飞书客户端
        stock_codes: 股票代码列表
        user_id: 用户ID
    """
    print("\n" + "=" * 60)
    print("启动监控引擎")
    print("=" * 60)

    logger.info(f"监控参数: 类型={args.type}, 窗口={args.window}分钟, 间隔={args.interval}秒")
    logger.info(f"阈值配置: L1={args.level1}%, L2={args.level2}%, L3={args.level3}%")

    try:
        success, msg = service.start_monitoring(interval_seconds=args.interval)
        if not success:
            logger.error(f"启动监控引擎失败: {msg}")
            print(f"\n启动监控引擎失败: {msg}")
            return

        logger.info(f"监控引擎已启动: {msg}")
        print(f"\n{msg}")

        # 获取引擎状态
        status = service.get_engine_status()
        logger.info(f"引擎状态: {status}")

        # 发送启动通知
        if args.notify_start and feishu_client:
            send_startup_notification(
                service=service,
                feishu_client=feishu_client,
                chat_id=args.chat_id,
                stocks=stock_codes,
                monitor_type=args.type,
                interval=args.interval,
                window=args.window,
                level1=args.level1,
                level2=args.level2,
                level3=args.level3,
            )

        print("\n" + "=" * 60)
        print(f"监控服务已启动！进程ID: {os.getpid()}")
        print("按 Ctrl+C 停止监控")
        print("=" * 60)

        # 保持运行
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n用户请求停止监控")
        print("\n\n正在停止监控服务...")
    finally:
        cleanup_on_exit(service)


def cleanup_on_exit(service: object) -> None:
    """
    退出时清理资源

    Args:
        service: 监控服务实例
    """
    try:
        logger.info("停止监控引擎")
        success, msg = service.stop_monitoring()
        if success:
            logger.info(f"监控引擎已停止: {msg}")
            print(f"\n{msg}")
        else:
            logger.warning(f"停止监控引擎失败: {msg}")
    except Exception as e:
        logger.error(f"清理资源时出错: {e}")


def main() -> int:
    """
    主函数入口

    Returns:
        int: 退出代码 (0=成功, 1=失败)
    """
    # 初始化日志系统
    setup_logging(
        log_prefix="stock_monitor",
        log_dir="./logs",
        console_level=logging.INFO,
        debug=False,
    )

    # 记录启动信息
    pid = os.getpid()
    now = get_now_cn()
    logger.info("=" * 60)
    logger.info(f"股票监控服务启动 | 进程ID: {pid} | 时间: {format_time_cn(now)}")
    logger.info("=" * 60)

    # 解析命令行参数
    parser = setup_argument_parser()
    args = parser.parse_args()

    # 记录参数配置
    logger.info(f"命令行参数: {vars(args)}")

    # 验证参数
    valid, errors = validate_arguments(args)
    if not valid:
        for error in errors:
            logger.error(f"参数错误: {error}")
            print(f"错误: {error}")
        return 1

    # 初始化监控服务
    service, success, msg = get_monitor_service_with_feishu(
        args.feishu_app_id,
        args.feishu_app_secret,
    )
    if not success:
        print(f"\n错误: {msg}")
        return 1

    user_id = DEFAULT_USER_ID

    # 获取飞书客户端（用于发送启动通知）
    feishu_client = None
    if args.feishu_app_id and args.feishu_app_secret:
        from bot.platforms.feishu_stream import FeishuReplyClient
        feishu_client = FeishuReplyClient(args.feishu_app_id, args.feishu_app_secret)

    try:
        # --list 操作：列出当前监控
        if args.list:
            list_monitors(service, user_id)
            return 0

        # 解析股票代码
        stock_codes = parse_stock_codes(args.stock_code)

        # 默认股票列表（如果没有指定）
        default_stocks = [
            "03759.HK",  # 康龙化成 (港股)
            "BABA",      # 阿里巴巴 (美股)
            "ORCL",      # 甲骨文 (美股)
            "MU",        # 美光科技 (美股)
        ]

        if not stock_codes:
            if args.remove:
                print("错误: 必须指定要移除的股票代码")
                return 1
            # 使用默认股票列表
            stock_codes = default_stocks
            logger.info(f"使用默认股票列表: {stock_codes}")

        # --remove 操作：移除监控
        if args.remove:
            results = remove_monitors(service, stock_codes, user_id)
            print("\n移除结果：")
            for code, success, msg in results:
                status = "✓" if success else "✗"
                print(f"  {status} {code}: {msg}")
            return 0

        # 默认操作：添加监控并启动
        results = add_monitors(service, stock_codes, args, user_id)

        # 显示添加结果
        print("\n添加结果：")
        success_count = 0
        for code, success, msg in results:
            status = "✓" if success else "✗"
            print(f"  {status} {code}: {msg}")
            if success:
                success_count += 1

        # 如果没有成功添加任何监控，退出
        if success_count == 0:
            logger.warning("没有成功添加任何监控")
            return 1

        # 启动监控循环
        start_monitoring_loop(service, args, feishu_client, stock_codes, user_id)

    except Exception as e:
        logger.error(f"运行时错误: {e}", exc_info=True)
        print(f"\n错误: {e}")
        cleanup_on_exit(service)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())