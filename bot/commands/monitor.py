# -*- coding: utf-8 -*-
"""
===================================
监控命令
===================================

管理持仓股票实时监控功能。

子命令:
- add <股票代码> [窗口分钟]: 添加监控
- remove <股票代码>: 移除监控
- list: 列出监控列表
- start: 启动监控引擎
- stop: 停止监控引擎
- status: 查看监控状态
- simulate <股票代码>: 添加模拟监控
- alerts: 查看告警历史
"""

import logging
from typing import List

from bot.commands.base import BotCommand
from bot.models import BotMessage, BotResponse

logger = logging.getLogger(__name__)


class MonitorCommand(BotCommand):
    """
    监控命令

    管理持仓股票实时监控功能。
    """

    @property
    def name(self) -> str:
        return "monitor"

    @property
    def aliases(self) -> List[str]:
        return ["m", "监控", "mon"]

    @property
    def description(self) -> str:
        return "持仓股票实时监控"

    @property
    def usage(self) -> str:
        return (
            "/monitor <子命令> [参数]\n"
            "子命令:\n"
            "  add <股票代码> [窗口] - 添加实时监控\n"
            "  remove <股票代码> - 移除监控\n"
            "  list - 列出监控列表\n"
            "  start - 启动监控引擎\n"
            "  stop - 停止监控引擎\n"
            "  status - 查看监控状态\n"
            "  simulate <股票代码> - 添加模拟监控\n"
            "  alerts [股票代码] - 查看告警历史"
        )

    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """执行监控命令"""
        if not args:
            return self._show_help()

        subcommand = args[0].lower()
        sub_args = args[1:] if len(args) > 1 else []

        handlers = {
            "add": self._handle_add,
            "remove": self._handle_remove,
            "rm": self._handle_remove,
            "list": self._handle_list,
            "ls": self._handle_list,
            "start": self._handle_start,
            "stop": self._handle_stop,
            "status": self._handle_status,
            "simulate": self._handle_simulate,
            "sim": self._handle_simulate,
            "alerts": self._handle_alerts,
            "help": self._show_help,
        }

        handler = handlers.get(subcommand)
        if not handler:
            return BotResponse.text_response(f"未知子命令: {subcommand}\n{self.usage}")

        return handler(message, sub_args)

    def _show_help(self, message: BotMessage = None, args: List[str] = None) -> BotResponse:
        """显示帮助信息"""
        help_text = """📊 **持仓股票实时监控**

**功能说明：**
- 监控持仓股票的实时价格变动
- 10分钟内涨跌幅超过±1%时记录
- 涨跌幅超过±2%时发送通知

**子命令：**
`/monitor add <股票代码> [窗口]`
  添加实时监控，默认窗口10分钟

`/monitor remove <股票代码>`
  移除指定股票的监控

`/monitor list`
  列出当前所有监控

`/monitor start`
  启动监控引擎

`/monitor stop`
  停止监控引擎

`/monitor status`
  查看监控引擎状态

`/monitor simulate <股票代码>`
  添加模拟监控（不发送通知）

`/monitor alerts [股票代码]`
  查看最近24小时告警历史

**示例：**
`/monitor add 600519` - 添加茅台实时监控
`/monitor add 00700.HK 15` - 添加腾讯，窗口15分钟
`/monitor simulate 600519` - 添加模拟监控
`/monitor list` - 查看监控列表
"""
        return BotResponse.markdown_response(help_text)

    def _handle_add(self, message: BotMessage, args: List[str]) -> BotResponse:
        """处理 add 子命令"""
        if not args:
            return BotResponse.text_response("请提供股票代码\n用法: /monitor add <股票代码> [窗口分钟]")

        stock_code = args[0].upper()
        window_minutes = 10

        if len(args) > 1:
            try:
                window_minutes = int(args[1])
                if window_minutes < 1 or window_minutes > 60:
                    return BotResponse.text_response("窗口时间应在 1-60 分钟之间")
            except ValueError:
                return BotResponse.text_response("窗口时间应为数字")

        from src.services.stock_monitor_service import get_monitor_service

        service = get_monitor_service()
        success, msg = service.add_monitor(
            stock_code=stock_code,
            user_id=message.user_id,
            chat_id=message.chat_id,
            monitor_type="realtime",
            window_minutes=window_minutes,
        )

        if success:
            return BotResponse.markdown_response(f"✅ {msg}\n\n监控类型: 🔴 实时监控\n窗口时间: {window_minutes}分钟")
        else:
            return BotResponse.text_response(f"❌ {msg}")

    def _handle_remove(self, message: BotMessage, args: List[str]) -> BotResponse:
        """处理 remove 子命令"""
        if not args:
            return BotResponse.text_response("请提供股票代码\n用法: /monitor remove <股票代码>")

        stock_code = args[0].upper()

        from src.services.stock_monitor_service import get_monitor_service

        service = get_monitor_service()
        success, msg = service.remove_monitor(stock_code, message.user_id)

        if success:
            return BotResponse.markdown_response(f"✅ {msg}")
        else:
            return BotResponse.text_response(f"❌ {msg}")

    def _handle_list(self, message: BotMessage, args: List[str]) -> BotResponse:
        """处理 list 子命令"""
        from src.services.stock_monitor_service import get_monitor_service

        service = get_monitor_service()
        monitors = service.list_monitors(message.user_id)
        text = service.format_monitor_list(monitors)

        return BotResponse.markdown_response(text)

    def _handle_start(self, message: BotMessage, args: List[str]) -> BotResponse:
        """处理 start 子命令"""
        from src.services.stock_monitor_service import get_monitor_service

        service = get_monitor_service()
        success, msg = service.start_monitoring()

        if success:
            return BotResponse.markdown_response(f"✅ {msg}")
        else:
            return BotResponse.text_response(f"❌ {msg}")

    def _handle_stop(self, message: BotMessage, args: List[str]) -> BotResponse:
        """处理 stop 子命令"""
        from src.services.stock_monitor_service import get_monitor_service

        service = get_monitor_service()
        success, msg = service.stop_monitoring()

        if success:
            return BotResponse.markdown_response(f"✅ {msg}")
        else:
            return BotResponse.text_response(f"❌ {msg}")

    def _handle_status(self, message: BotMessage, args: List[str]) -> BotResponse:
        """处理 status 子命令"""
        from src.services.stock_monitor_service import get_monitor_service

        service = get_monitor_service()
        status = service.get_engine_status()

        running_icon = "🟢" if status["running"] else "🔴"
        running_text = "运行中" if status["running"] else "已停止"

        lines = [
            "📊 **监控引擎状态**",
            "",
            f"**状态:** {running_icon} {running_text}",
            f"**活跃监控数:** {status['active_monitors']}",
            "",
            "**监控类型分布:**",
            f"• 🔴 实时监控: {status['monitor_type_breakdown']['realtime']}",
            f"• 🟡 模拟监控: {status['monitor_type_breakdown']['simulation']}",
            "",
            "**最近24小时告警:**",
            f"• 总计: {status['alerts_24h']['total_alerts']}",
            f"• 1%阈值: {status['alerts_24h']['threshold_1pct_count']}",
            f"• 2%阈值: {status['alerts_24h']['threshold_2pct_count']}",
            f"• 涉及股票: {status['alerts_24h']['unique_stocks']} 只",
        ]

        return BotResponse.markdown_response("\n".join(lines))

    def _handle_simulate(self, message: BotMessage, args: List[str]) -> BotResponse:
        """处理 simulate 子命令"""
        if not args:
            return BotResponse.text_response("请提供股票代码\n用法: /monitor simulate <股票代码>")

        stock_code = args[0].upper()
        window_minutes = 10

        if len(args) > 1:
            try:
                window_minutes = int(args[1])
                if window_minutes < 1 or window_minutes > 60:
                    return BotResponse.text_response("窗口时间应在 1-60 分钟之间")
            except ValueError:
                return BotResponse.text_response("窗口时间应为数字")

        from src.services.stock_monitor_service import get_monitor_service

        service = get_monitor_service()
        success, msg = service.add_monitor(
            stock_code=stock_code,
            user_id=message.user_id,
            chat_id=message.chat_id,
            monitor_type="simulation",
            window_minutes=window_minutes,
        )

        if success:
            return BotResponse.markdown_response(
                f"✅ {msg}\n\n监控类型: 🟡 模拟监控（不发送通知）\n窗口时间: {window_minutes}分钟"
            )
        else:
            return BotResponse.text_response(f"❌ {msg}")

    def _handle_alerts(self, message: BotMessage, args: List[str]) -> BotResponse:
        """处理 alerts 子命令"""
        stock_code = args[0].upper() if args else None

        from src.services.stock_monitor_service import get_monitor_service

        service = get_monitor_service()
        alerts = service.get_alert_history(message.user_id, stock_code)

        if not alerts:
            return BotResponse.markdown_response("📭 最近24小时无告警记录")

        lines = ["📋 **告警历史（最近24小时）\n"]

        for alert in alerts[:20]:
            type_icon = "⚠️" if alert["alert_type"] == "threshold_2pct" else "📊"
            direction = "上涨" if alert["change_pct"] > 0 else "下跌"
            time_str = alert["alert_time"].split("T")[1][:8] if "T" in alert["alert_time"] else alert["alert_time"]

            lines.append(
                f"{type_icon} **{alert['stock_code']}** {direction} {abs(alert['change_pct']):.2f}%\n"
                f"   价格: ¥{alert['price']:.2f} | 时间: {time_str}\n"
            )

        if len(alerts) > 20:
            lines.append(f"\n_... 共 {len(alerts)} 条记录_")

        return BotResponse.markdown_response("\n".join(lines))
