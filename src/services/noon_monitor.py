# -*- coding: utf-8 -*-
"""
===================================
午间监测服务
===================================

职责：
1. 监测关注股票的技术指标（60分钟、120分钟）
2. 分析均线系统状态
3. 检测MACD、KDJ指标状态
4. 识别顶背离与底背离形态
5. 生成技术指标综合评分及操作建议
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.config import get_config
from src.services.technical_monitor import (
    TechnicalMonitor,
    TechnicalMonitorResult,
)

logger = logging.getLogger(__name__)


@dataclass
class NoonMonitorResult:
    """午间监测结果"""
    date: str
    time: str
    watch_list: List[str] = field(default_factory=list)
    results_60min: Dict[str, TechnicalMonitorResult] = field(default_factory=dict)
    results_120min: Dict[str, TechnicalMonitorResult] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    report_text: str = ""
    timestamp: Optional[datetime] = None


class NoonMonitorService:
    """午间监测服务"""
    
    def __init__(self):
        self.config = get_config()
        self.technical_monitor = TechnicalMonitor()
        self._data_provider = None
    
    @property
    def data_provider(self):
        """延迟加载数据提供者"""
        if self._data_provider is None:
            from data_provider.base import DataFetcherManager
            self._data_provider = DataFetcherManager()
        return self._data_provider
    
    def get_stock_name(self, code: str) -> str:
        """获取股票名称"""
        try:
            name = self.data_provider.get_stock_name(code)
            return name if name else ""
        except Exception:
            return ""
    
    def analyze_stock(
        self, 
        code: str, 
        intervals: List[int] = [60, 120]
    ) -> Dict[int, TechnicalMonitorResult]:
        """
        分析单只股票的多个时间周期
        
        Args:
            code: 股票代码
            intervals: 时间周期列表（分钟）
            
        Returns:
            {周期: 分析结果} 字典
        """
        results = {}
        
        for interval in intervals:
            try:
                result = self.technical_monitor.analyze(code, interval)
                results[interval] = result
            except Exception as e:
                logger.error(f"分析股票 {code} {interval}分钟数据失败: {e}")
        
        return results
    
    def analyze_watch_list(
        self,
        codes: Optional[List[str]] = None,
        intervals: List[int] = [60, 120],
    ) -> Dict[str, Dict[int, TechnicalMonitorResult]]:
        """
        分析关注股票列表
        
        Args:
            codes: 股票代码列表（可选，默认从配置获取）
            intervals: 时间周期列表
            
        Returns:
            {股票代码: {周期: 分析结果}} 字典
        """
        if codes is None:
            codes = self.config.watch_list
        
        all_results = {}
        
        for code in codes:
            logger.info(f"分析股票 {code}...")
            all_results[code] = self.analyze_stock(code, intervals)
        
        return all_results
    
    def generate_summary(
        self,
        results: Dict[str, Dict[int, TechnicalMonitorResult]]
    ) -> Dict[str, Any]:
        """
        生成分析摘要
        
        Args:
            results: 分析结果
            
        Returns:
            摘要数据
        """
        summary = {
            'total': len(results),
            'strong_buy': 0,
            'buy': 0,
            'hold': 0,
            'sell': 0,
            'strong_sell': 0,
            'top_divergence_count': 0,
            'bottom_divergence_count': 0,
            'high_risk': [],
        }
        
        for code, interval_results in results.items():
            for interval, result in interval_results.items():
                if result.advice == "强烈买入":
                    summary['strong_buy'] += 1
                elif result.advice == "买入":
                    summary['buy'] += 1
                elif result.advice in ["持有观望", "观望"]:
                    summary['hold'] += 1
                elif result.advice == "减仓":
                    summary['sell'] += 1
                elif result.advice == "卖出":
                    summary['strong_sell'] += 1
                
                if result.top_divergence and result.top_divergence.confirmed:
                    summary['top_divergence_count'] += 1
                    if result.top_divergence.risk_level == "高":
                        summary['high_risk'].append(code)
                
                if result.bottom_divergence and result.bottom_divergence.confirmed:
                    summary['bottom_divergence_count'] += 1
        
        return summary
    
    def run_noon_monitor(
        self,
        watch_list: Optional[List[str]] = None,
    ) -> NoonMonitorResult:
        """
        执行午间监测
        
        Args:
            watch_list: 关注股票列表（可选）
            
        Returns:
            午间监测结果
        """
        logger.info("开始执行午间监测...")
        
        now = datetime.now()
        result = NoonMonitorResult(
            date=now.strftime('%Y-%m-%d'),
            time=now.strftime('%H:%M'),
            timestamp=now,
        )
        
        if watch_list is None:
            watch_list = self.config.watch_list
        
        result.watch_list = watch_list
        
        all_results = self.analyze_watch_list(watch_list)
        
        for code, interval_results in all_results.items():
            if 60 in interval_results:
                result.results_60min[code] = interval_results[60]
            if 120 in interval_results:
                result.results_120min[code] = interval_results[120]
        
        result.summary = self.generate_summary(all_results)
        
        result.report_text = self.generate_report(result)
        
        logger.info("午间监测完成")
        return result
    
    def generate_report(self, result: NoonMonitorResult) -> str:
        """
        生成午间监测报告
        
        Args:
            result: 午间监测结果
            
        Returns:
            Markdown格式的报告文本
        """
        lines = []
        
        lines.append(f"# ☀️ 午间监测报告 - {result.date} {result.time}")
        lines.append("")
        
        summary = result.summary
        lines.append("## 📊 监测摘要")
        lines.append("")
        lines.append(f"共监测 {summary['total']} 只股票")
        lines.append("")
        lines.append(f"| 操作建议 | 数量 |")
        lines.append(f"|----------|------|")
        lines.append(f"| 💚 强烈买入 | {summary['strong_buy']} |")
        lines.append(f"| 🟢 买入 | {summary['buy']} |")
        lines.append(f"| 🟡 持有观望 | {summary['hold']} |")
        lines.append(f"| 🟠 减仓 | {summary['sell']} |")
        lines.append(f"| 🔴 卖出 | {summary['strong_sell']} |")
        lines.append("")
        
        if summary['top_divergence_count'] > 0:
            lines.append(f"⚠️ **检测到 {summary['top_divergence_count']} 个顶背离信号**")
            if summary['high_risk']:
                high_risk_with_names = []
                for code in summary['high_risk']:
                    name = self.get_stock_name(code)
                    if name:
                        high_risk_with_names.append(f"{code} ({name})")
                    else:
                        high_risk_with_names.append(code)
                lines.append(f"   高风险股票: {', '.join(high_risk_with_names)}")
            lines.append("")
        
        if summary['bottom_divergence_count'] > 0:
            lines.append(f"✅ **检测到 {summary['bottom_divergence_count']} 个底背离信号**")
            lines.append("")
        
        lines.append("## 📈 关注股票技术指标监测")
        lines.append("")
        
        for code in result.watch_list:
            name = self.get_stock_name(code)
            title = f"{code} ({name})" if name else code
            lines.append(f"### {title}")
            lines.append("")
            
            if code in result.results_60min:
                lines.append("#### 60分钟")
                lines.append("")
                r = result.results_60min[code]
                r.name = name
                lines.append(self._format_brief_result(r))
                lines.append("")
            
            if code in result.results_120min:
                lines.append("#### 120分钟")
                lines.append("")
                r = result.results_120min[code]
                r.name = name
                lines.append(self._format_brief_result(r))
                lines.append("")
        
        if result.timestamp:
            lines.append("---")
            lines.append(f"生成时间: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)
    
    def _format_brief_result(self, result: TechnicalMonitorResult) -> str:
        """格式化简要结果"""
        lines = []
        
        lines.append(f"- **当前价格**: {result.current_price:.2f}")
        lines.append(f"- **趋势**: {result.trend_status.value}")
        lines.append(f"- **MACD**: {result.indicators.macd_signal}")
        lines.append(f"- **KDJ**: {result.indicators.kdj_signal}")
        
        if result.top_divergence and result.top_divergence.confirmed:
            lines.append(f"- ⚠️ **顶背离**: 强度 {result.top_divergence.strength:.1f}, 风险 {result.top_divergence.risk_level}")
        
        if result.bottom_divergence and result.bottom_divergence.confirmed:
            lines.append(f"- ✅ **底背离**: 强度 {result.bottom_divergence.strength:.1f}")
        
        lines.append(f"- **综合评分**: {result.score}/100")
        lines.append(f"- **操作建议**: **{result.advice}**")
        
        return "\n".join(lines)


def run_noon_monitor(
    watch_list: Optional[List[str]] = None,
) -> NoonMonitorResult:
    """
    便捷函数：执行午间监测
    
    Args:
        watch_list: 关注股票列表
        
    Returns:
        午间监测结果
    """
    service = NoonMonitorService()
    return service.run_noon_monitor(watch_list)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    result = run_noon_monitor(['600519', '300750'])
    print(result.report_text)
