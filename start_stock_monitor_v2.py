# -*- coding: utf-8 -*-
"""
股票监控启动脚本 - 重构版

功能：
- 内存存储监控列表（非持久化，仅应用生命周期存在）
- 启动时可指定初始监控股票
- 运行时动态管理（添加/删除/列表）
- 自动清理（停止时清空内存）
- 飞书通知开关控制
- 通知同时显示代码和名称
- 实时行情监控与预警

使用示例：
    python start_stock_monitor_v2.py -s 300759 03759.HK --feishu-on
    python start_stock_monitor_v2.py --list
    python start_stock_monitor_v2.py -s 300759 --add
    python start_stock_monitor_v2.py -s 03759.HK --remove
"""

import argparse
import logging
import os
import signal
import sys
import time
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.logging_config import setup_logging
from src.data.stock_mapping import STOCK_NAME_MAP, is_meaningful_stock_name

# 默认配置
DEFAULT_USER_ID = "monitor_user_001"
DEFAULT_CHAT_ID = "oc_c4f728163782081095ba208e2cd0ae3e"
DEFAULT_FEISHU_APP_ID = "cli_a924f365e2f89cc0"
DEFAULT_FEISHU_APP_SECRET = "Fq1fQ3kyEoa6zneJHbtsuA3kQKiybVyt"

# China timezone (UTC+8)
TZ_CN = timezone(timedelta(hours=8))

logger = logging.getLogger(__name__)


# =============================================================================
# 工具函数
# =============================================================================

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


def get_stock_name(stock_code: str) -> str:
    """获取股票名称（使用平台库接口）"""
    normalized_code = stock_code.strip().upper()
    
    # 处理港股格式：03759.HK -> 03759
    if normalized_code.endswith(".HK"):
        hk_code = normalized_code[:-3]
        # 尝试5位格式 (如 03759)
        if hk_code in STOCK_NAME_MAP:
            return STOCK_NAME_MAP[hk_code]
        # 尝试4位格式 (如 3759)
        if len(hk_code) == 5 and hk_code.startswith("0"):
            hk_code_4 = hk_code[1:]  # 去掉前导0
            if hk_code_4 in STOCK_NAME_MAP:
                return STOCK_NAME_MAP[hk_code_4]
    
    # 直接查找
    if normalized_code in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[normalized_code]
    
    # 尝试原始代码
    if stock_code in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[stock_code]
    
    # 返回代码作为名称
    return stock_code


def validate_stock_code(stock_code: str) -> Tuple[bool, str]:
    """验证股票代码格式是否有效"""
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
    """解析股票代码参数"""
    if not stock_args:
        return []

    stock_codes = []
    for arg in stock_args:
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


# =============================================================================
# 内存监控存储模块
# =============================================================================

class MonitorConfig:
    """监控配置"""
    def __init__(
        self,
        stock_code: str,
        stock_name: str,
        level1_threshold: float = 3.5,
        level2_threshold: float = 2.0,
        level3_threshold: float = 0.5,
        window_minutes: int = 10,
        chat_id: str = DEFAULT_CHAT_ID,
    ):
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.level1_threshold = level1_threshold
        self.level2_threshold = level2_threshold
        self.level3_threshold = level3_threshold
        self.window_minutes = window_minutes
        self.chat_id = chat_id
        self.created_at = get_now_cn()
        self.is_active = True


class MonitorState:
    """监控状态"""
    def __init__(self, config_id: str):
        self.config_id = config_id
        self.baseline_price: Optional[float] = None
        self.window_start_price: Optional[float] = None
        self.window_start_time: Optional[datetime] = None
        self.last_price: Optional[float] = None
        self.last_change_pct: Optional[float] = None
        self.alert_level1_triggered = bool = False
        self.alert_level2_triggered: bool = False
        self.alert_level3_triggered: bool = False
        self.last_check_time: Optional[datetime] = None


class InMemoryMonitorStore:
    """内存中的监控存储（替代数据库）"""

    def __init__(self):
        self._configs: Dict[str, MonitorConfig] = {}  # stock_code -> config
        self._states: Dict[str, MonitorState] = {}  # config_id -> state
        self._lock = threading.RLock()

    def add(self, config: MonitorConfig) -> bool:
        """添加监控"""
        with self._lock:
            self._configs[config.stock_code] = config
            self._states[config.stock_code] = MonitorState(config_id=config.stock_code)
            logger.info(f"[内存存储] 添加监控: {config.stock_code}")
            return True

    def remove(self, stock_code: str) -> bool:
        """移除监控"""
        with self._lock:
            if stock_code in self._configs:
                del self._configs[stock_code]
                if stock_code in self._states:
                    del self._states[stock_code]
                logger.info(f"[内存存储] 移除监控: {stock_code}")
                return True
            return False

    def get(self, stock_code: str) -> Optional[MonitorConfig]:
        """获取单个监控配置"""
        with self._lock:
            return self._configs.get(stock_code)

    def get_state(self, stock_code: str) -> Optional[MonitorState]:
        """获取监控状态"""
        with self._lock:
            return self._states.get(stock_code)

    def list_all(self) -> List[MonitorConfig]:
        """列出所有监控"""
        with self._lock:
            return list(self._configs.values())

    def exists(self, stock_code: str) -> bool:
        """检查是否存在"""
        with self._lock:
            return stock_code in self._configs

    def clear(self) -> None:
        """清空所有监控"""
        with self._lock:
            count = len(self._configs)
            self._configs.clear()
            self._states.clear()
            logger.info(f"[内存存储] 清空所有监控 ({count}个)")

    def count(self) -> int:
        """获取监控数量"""
        with self._lock:
            return len(self._configs)


# 全局单例
_monitor_store = InMemoryMonitorStore()


def get_monitor_store() -> InMemoryMonitorStore:
    return _monitor_store


# =============================================================================
# 飞书通知管理器（带开关）
# =============================================================================

class FeishuNotifier:
    """飞书通知管理器（支持开关控制）"""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        chat_id: str,
        enabled: bool = True,
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.chat_id = chat_id
        self._enabled = enabled
        self._client = None

        if app_id and app_secret:
            try:
                from bot.platforms.feishu_stream import FeishuReplyClient
                self._client = FeishuReplyClient(app_id, app_secret)
                logger.info("[飞书通知] 客户端初始化成功")
            except Exception as e:
                logger.warning(f"[飞书通知] 客户端初始化失败: {e}")

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        logger.info(f"[飞书通知] 开关: {'开启' if value else '关闭'}")

    def send(self, message: str, force: bool = False) -> bool:
        """发送通知"""
        if not self._enabled and not force:
            logger.debug("[飞书通知] 跳过（开关关闭）")
            return False

        if not self._client:
            logger.warning("[飞书通知] 客户端未初始化")
            return False

        try:
            success = self._client.send_to_chat(self.chat_id, message)
            if success:
                logger.info("[飞书通知] 发送成功")
            else:
                logger.warning("[飞书通知] 发送失败")
            return success
        except Exception as e:
            logger.error(f"[飞书通知] 发送异常: {e}")
            return False


# =============================================================================
# 行情获取模块
# =============================================================================

def get_realtime_quote(stock_code: str) -> Optional[Dict]:
    """获取实时行情"""
    try:
        from data_provider.base import DataFetcherManager
        fetcher = DataFetcherManager()
        quote = fetcher.get_realtime_quote(stock_code)
        if quote and quote.has_basic_data():
            return {
                "price": quote.price,
                "change_pct": quote.change_pct,
                "name": quote.name,
                "open": quote.open_price,
                "high": quote.high,
                "low": quote.low,
                "volume": quote.volume,
                "turnover_rate": quote.turnover_rate,
            }
    except Exception as e:
        logger.error(f"[行情获取] 获取 {stock_code} 行情失败: {e}")
        return None


# =============================================================================
# 监控引擎
# =============================================================================

class MonitorEngine:
    """监控引擎"""

    def __init__(
        self,
        store: InMemoryMonitorStore,
        notifier: Optional[FeishuNotifier],
        interval_seconds: int = 10,
    ):
        self.store = store
        self.notifier = notifier
        self.interval_seconds = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """启动监控"""
        if self._running:
            logger.warning("[监控引擎] 已在运行")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"[监控引擎] 已启动，检查间隔: {self.interval_seconds}秒")

    def stop(self) -> None:
        """停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[监控引擎] 已停止")

    def _monitor_loop(self) -> None:
        """监控循环"""
        logger.info("[监控引擎] 监控循环开始")
        
        while self._running:
            try:
                self._check_all_monitors()
            except Exception as e:
                logger.error(f"[监控引擎] 监控循环错误: {e}")
            
            time.sleep(self.interval_seconds)

    def _check_all_monitors(self) -> None:
        """检查所有监控"""
        configs = self.store.list_all()
        if not configs:
            logger.debug("[监控引擎] 没有监控配置")
            return

        logger.info(f"[监控引擎] 检查 {len(configs)} 个监控")
        
        for config in configs:
            try:
                self._check_single_monitor(config)
            except Exception as e:
                logger.error(f"[监控引擎] 检查 {config.stock_code} 失败: {e}")

    def _check_single_monitor(self, config: MonitorConfig) -> None:
        """检查单个监控"""
        stock_code = config.stock_code
        stock_name = config.stock_name
        
        # 获取实时行情
        quote = get_realtime_quote(stock_code)
        if not quote:
            logger.warning(f"[监控引擎] 无法获取 {stock_code} 行情")
            return
        
        current_price = quote["price"]
        today_change_pct = quote["change_pct"]
        
        # 获取状态
        state = self.store.get_state(stock_code)
        if not state:
            state = MonitorState(config_id=stock_code)
            state.baseline_price = current_price
            state.window_start_price = current_price
            state.window_start_time = get_now_cn()
            self.store._states[stock_code] = state
            logger.info(f"[监控引擎] 初始化 {stock_code} 基准价格: {current_price}")
        
        # 确保 window_start_price 不为 None
        if state.window_start_price is None:
            state.window_start_price = current_price
            state.window_start_time = get_now_cn()
            logger.info(f"[监控引擎] 补初始化 {stock_code} 窗口起始价格: {current_price}")
        
        # 更新状态
        state.last_price = current_price
        state.last_change_pct = today_change_pct
        state.last_check_time = get_now_cn()
        
        # 检查是否需要重置窗口
        now = get_now_cn()
        if state.window_start_time:
            window_elapsed = (now - state.window_start_time).total_seconds() / 60
            if window_elapsed >= config.window_minutes:
                # 重置窗口
                state.window_start_price = current_price
                state.window_start_time = now
                state.alert_level3_triggered = False
                logger.info(f"[监控引擎] 重置 {stock_code} 监控窗口")
        
        # 计算窗口涨跌幅
        window_change_pct = 0.0
        if state.window_start_price and state.window_start_price > 0:
            window_change_pct = ((current_price - state.window_start_price) / state.window_start_price) * 100
        
        ws_price_str = f"{state.window_start_price:.2f}" if state.window_start_price else "None"
        logger.info(
            f"[监控引擎] {stock_code}: 价格={current_price:.2f}, "
            f"窗口起始={ws_price_str}, "
            f"今日涨跌={today_change_pct:.2f}%, "
            f"窗口涨跌={window_change_pct:.4f}%"
        )
        
        # 检查预警
        self._check_alerts(config, state, current_price, today_change_pct, window_change_pct)
        
        # 更新状态
        self.store._states[stock_code] = state

    def _check_alerts(
        self,
        config: MonitorConfig,
        state: MonitorState,
        current_price: float,
        today_change_pct: float,
        window_change_pct: float,
    ) -> None:
        """检查预警条件"""
        abs_today = abs(today_change_pct) if today_change_pct is not None else 0
        abs_window = abs(window_change_pct) if window_change_pct is not None else 0
        
        logger.info(
            f"[监控引擎] 预警检查: |window|={abs_window:.6f}% >= {config.level3_threshold}%? "
            f"{abs_window >= config.level3_threshold}, "
            f"已触发? {state.alert_level3_triggered}"
        )
        
        # Level 1: 今日涨跌幅
        if abs_today >= config.level1_threshold and not state.alert_level1_triggered:
            self._send_alert(config, "level1", today_change_pct, current_price, "today")
            state.alert_level1_triggered = True
        
        # Level 2: 今日涨跌幅
        if abs_today >= config.level2_threshold and not state.alert_level2_triggered:
            self._send_alert(config, "level2", today_change_pct, current_price, "today")
            state.alert_level2_triggered = True
        
        # Level 3: 窗口涨跌幅
        if abs_window >= config.level3_threshold and not state.alert_level3_triggered:
            self._send_alert(config, "level3", window_change_pct, current_price, "window")
            state.alert_level3_triggered = True

    def _send_alert(
        self,
        config: MonitorConfig,
        level: str,
        change_pct: float,
        current_price: float,
        alert_type: str,
    ) -> None:
        """发送预警通知"""
        if not self.notifier:
            logger.warning("[监控引擎] 未配置通知器")
            return
        
        direction = "上涨" if change_pct > 0 else "下跌"
        abs_change = abs(change_pct)
        
        level_info = {
            "level1": ("🔴", "一级预警", f"今日涨跌幅超{config.level1_threshold}%"),
            "level2": ("🟠", "二级预警", f"今日涨跌幅超{config.level2_threshold}%"),
            "level3": ("🟡", "三级预警", f"{config.window_minutes}分钟内涨跌幅超{config.level3_threshold}%"),
        }
        
        icon, level_name, threshold_desc = level_info.get(level, ("⚠️", "预警", ""))
        
        title = f"{icon} {level_name} {config.stock_name}({config.stock_code}) {direction}"
        message = (
            f"**{config.stock_name}** ({config.stock_code})\n"
            f"**{direction} {abs_change:.2f}%**\n\n"
            f"预警级别: {icon} {level_name}\n"
            f"触发条件: {threshold_desc}\n"
            f"当前价格: ¥{current_price:.2f}\n"
            f"触发时间: {get_now_cn().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        
        if alert_type == "window":
            message += f"监控窗口: {config.window_minutes}分钟\n"
        
        logger.info(f"[监控引擎] 发送预警: {title}")
        self.notifier.send(f"{title}\n\n{message}", force=True)


# =============================================================================
# 参数解析
# =============================================================================

def setup_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="start_stock_monitor_v2",
        description="股票监控服务 - 内存存储版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例用法:
  # 启动监控（初始股票）
  python start_stock_monitor_v2.py -s 300759 03759.HK --feishu-on

  # 列出当前监控
  python start_stock_monitor_v2.py --list

  # 运行时添加股票
  python start_stock_monitor_v2.py -s 000858 --add

  # 运行时移除股票
  python start_stock_monitor_v2.py -s 03759.HK --remove

  # 切换飞书通知
  python start_stock_monitor_v2.py --feishu-off
  python start_stock_monitor_v2.py --feishu-on
""",
    )

    parser.add_argument(
        "-s", "--stock-code", "--stocks",
        nargs="*",
        help="股票代码（支持多个）",
    )

    parser.add_argument(
        "-w", "--window",
        type=int,
        default=10,
        help="监控时间窗口（分钟）",
    )

    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=10,
        help="监控检查间隔（秒）",
    )

    parser.add_argument(
        "--level1", "--threshold-level1",
        type=float,
        default=3.5,
        help="一级预警阈值",
    )
    parser.add_argument(
        "--level2", "--threshold-level2",
        type=float,
        default=2.0,
        help="二级预警阈值",
    )
    parser.add_argument(
        "--level3", "--threshold-level3",
        type=float,
        default=0.5,
        help="三级预警阈值",
    )

    parser.add_argument(
        "--chat-id",
        type=str,
        default=DEFAULT_CHAT_ID,
        help="飞书聊天ID",
    )
    parser.add_argument(
        "--feishu-app-id",
        type=str,
        default=DEFAULT_FEISHU_APP_ID,
        help="飞书应用ID",
    )
    parser.add_argument(
        "--feishu-app-secret",
        type=str,
        default=DEFAULT_FEISHU_APP_SECRET,
        help="飞书应用密钥",
    )

    # 飞书通知开关
    feishu_group = parser.add_mutually_exclusive_group()
    feishu_group.add_argument(
        "--feishu-on",
        action="store_true",
        help="开启飞书通知",
    )
    feishu_group.add_argument(
        "--feishu-off",
        action="store_true",
        help="关闭飞书通知",
    )

    # 操作模式
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出当前所有监控",
    )
    parser.add_argument(
        "--add",
        action="store_true",
        help="添加股票到监控列表",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="从监控列表移除股票",
    )
    parser.add_argument(
        "--notify-start",
        action="store_true",
        help="启动时发送飞书通知",
    )

    return parser


# =============================================================================
# 核心功能
# =============================================================================

def add_monitors_to_memory(
    store: InMemoryMonitorStore,
    stock_codes: List[str],
    args: argparse.Namespace,
    notifier: Optional[FeishuNotifier],
) -> List[Tuple[str, bool, str]]:
    """添加监控到内存"""
    results = []

    for stock_code in stock_codes:
        if store.exists(stock_code):
            results.append((stock_code, False, "已存在"))
            continue

        stock_name = get_stock_name(stock_code)
        
        config = MonitorConfig(
            stock_code=stock_code,
            stock_name=stock_name,
            level1_threshold=args.level1,
            level2_threshold=args.level2,
            level3_threshold=args.level3,
            window_minutes=args.window,
            chat_id=args.chat_id,
        )

        success = store.add(config)
        msg = "添加成功" if success else "添加失败"
        results.append((stock_code, success, msg))

        if success and notifier:
            notifier.send(f"✅ **添加监控**\n{stock_name} ({stock_code})")

    return results


def remove_monitors_from_memory(
    store: InMemoryMonitorStore,
    stock_codes: List[str],
    notifier: Optional[FeishuNotifier],
) -> List[Tuple[str, bool, str]]:
    """从内存移除监控"""
    results = []

    for stock_code in stock_codes:
        config = store.get(stock_code)
        name = config.stock_name if config else get_stock_name(stock_code)
        success = store.remove(stock_code)
        msg = "移除成功" if success else "不存在"
        results.append((stock_code, success, msg))

        if success and notifier:
            notifier.send(f"❌ **移除监控**\n{name} ({stock_code})")

    return results


def list_monitors_from_memory(store: InMemoryMonitorStore) -> None:
    """列出内存中的监控"""
    print("\n" + "=" * 60)
    print("当前监控列表（内存存储）")
    print("=" * 60)

    monitors = store.list_all()

    if not monitors:
        print("暂无监控")
        return

    for i, m in enumerate(monitors, 1):
        state = store.get_state(m.stock_code)
        print(f"\n{i}. {m.stock_name} ({m.stock_code})")
        print(f"   窗口: {m.window_minutes}分钟")
        print(f"   阈值: L1={m.level1_threshold}% L2={m.level2_threshold}% L3={m.level3_threshold}%")
        if state and state.last_price:
            print(f"   最新价格: ¥{state.last_price:.2f}")
            if state.last_change_pct is not None:
                print(f"   今日涨跌: {state.last_change_pct:+.2f}%")
        if m.created_at:
            print(f"   创建: {format_time_cn(m.created_at)}")

    print("\n" + "=" * 60)
    print(f"共 {len(monitors)} 个监控")
    print("=" * 60)


def send_startup_notification(
    notifier: FeishuNotifier,
    configs: List[MonitorConfig],
    args: argparse.Namespace,
) -> None:
    """发送启动通知"""
    now = get_now_cn()
    stock_list = ", ".join([f"{c.stock_name}({c.stock_code})" for c in configs])

    message = f"""🚀 **股票监控已启动**

**监控股票:** {stock_list}
**监控间隔:** {args.interval}秒
**时间窗口:** {args.window}分钟
**阈值设置:**
  - L1: {args.level1}%
  - L2: {args.level2}%
  - L3: {args.level3}%
**启动时间:** {format_time_cn(now)}
**进程ID:** {os.getpid()}

_监控运行中，按 Ctrl+C 停止_
"""
    notifier.send(message, force=True)


def cleanup_on_exit(store: InMemoryMonitorStore, notifier: Optional[FeishuNotifier]) -> None:
    """退出时清理（清空内存）"""
    logger.info("正在清理...")

    count = store.count()
    store.clear()

    if notifier and count > 0:
        notifier.send(f"🛑 **监控已停止**\n已清除 {count} 个监控", force=True)

    logger.info("清理完成")


def signal_handler(sig, frame):
    """信号处理"""
    logger.info(f"收到信号: {sig}")
    raise KeyboardInterrupt()


# =============================================================================
# 主函数
# =============================================================================

def main() -> int:
    setup_logging(
        log_prefix="stock_monitor_v2",
        log_dir="./logs",
        console_level=logging.INFO,
        debug=False,
    )

    pid = os.getpid()
    now = get_now_cn()
    logger.info("=" * 60)
    logger.info(f"股票监控服务启动 | 进程ID: {pid} | 时间: {format_time_cn(now)}")
    logger.info("=" * 60)

    parser = setup_argument_parser()
    args = parser.parse_args()
    logger.info(f"命令行参数: {vars(args)}")

    store = get_monitor_store()

    # 初始化飞书通知器
    feishu_enabled = not args.feishu_off  # 默认开启，除非指定 --feishu-off
    if args.feishu_on:
        feishu_enabled = True

    notifier = FeishuNotifier(
        app_id=args.feishu_app_id,
        app_secret=args.feishu_app_secret,
        chat_id=args.chat_id,
        enabled=feishu_enabled,
    )

    try:
        # --list: 列出监控
        if args.list:
            list_monitors_from_memory(store)
            return 0

        # --feishu-on/--feishu-off: 仅切换开关
        if args.feishu_on or args.feishu_off:
            if not args.add and not args.remove and not args.stock_code:
                print(f"飞书通知: {'开启' if feishu_enabled else '关闭'}")
                return 0

        # 解析股票代码
        stock_codes = parse_stock_codes(args.stock_code)

        # 默认测试股票
        if not stock_codes and not args.list and not args.add and not args.remove:
            stock_codes = ["300759", "03759.HK"]
            logger.info(f"使用默认测试股票: {stock_codes}")

        # --remove: 移除监控
        if args.remove:
            if not stock_codes:
                print("错误: 必须指定要移除的股票代码")
                return 1
            results = remove_monitors_from_memory(store, stock_codes, notifier)
            print("\n移除结果：")
            for code, success, msg in results:
                status = "✓" if success else "✗"
                config = store.get(code)
                name = config.stock_name if config else get_stock_name(code)
                print(f"  {status} {name}({code}): {msg}")
            return 0

        # --add: 添加监控
        if args.add:
            if not stock_codes:
                print("错误: 必须指定要添加的股票代码")
                return 1
            results = add_monitors_to_memory(store, stock_codes, args, notifier)
            print("\n添加结果：")
            for code, success, msg in results:
                status = "✓" if success else "✗"
                config = store.get(code)
                name = config.stock_name if config else get_stock_name(code)
                print(f"  {status} {name}({code}): {msg}")
            return 0

        # 默认操作：添加并启动监控
        if stock_codes:
            results = add_monitors_to_memory(store, stock_codes, args, notifier)
            print("\n添加结果：")
            success_count = 0
            for code, success, msg in results:
                status = "✓" if success else "✗"
                config = store.get(code)
                name = config.stock_name if config else get_stock_name(code)
                print(f"  {status} {name}({code}): {msg}")
                if success:
                    success_count += 1

        # 启动监控引擎
        engine = MonitorEngine(
            store=store,
            notifier=notifier,
            interval_seconds=args.interval,
        )

        # 发送启动通知
        if args.notify_start and success_count > 0:
            send_startup_notification(notifier, store.list_all(), args)

        # 注册信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        print("\n" + "=" * 60)
        print(f"监控服务已启动！进程ID: {os.getpid()}")
        print(f"检查间隔: {args.interval}秒")
        print(f"预警阈值: L1={args.level1}% L2={args.level2}% L3={args.level3}%")
        print("按 Ctrl+C 停止监控")
        print("=" * 60)

        # 启动监控
        engine.start()

        # 保持运行
        while engine._running:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n用户请求停止监控")
        print("\n\n正在停止监控服务...")
    except Exception as e:
        logger.error(f"运行时错误: {e}", exc_info=True)
        print(f"\n错误: {e}")
    finally:
        cleanup_on_exit(store, notifier)

    return 0


if __name__ == "__main__":
    sys.exit(main())
