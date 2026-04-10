# -*- coding: utf-8 -*-
"""
===================================
晚间监测服务
===================================

职责：
1. 关注股票技术指标监测（收盘后完整数据）
2. 持仓股票技术指标深度分析
3. 支撑位/压力位识别
4. 背离确认与风险等级评估
5. 成交量验证
6. 生成持仓股票技术面风险评级与持仓策略建议
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

import pandas as pd
import numpy as np

from src.config import get_config
from src.services.technical_monitor import (
    TechnicalMonitor,
    TechnicalMonitorResult,
    DivergenceResult,
)

logger = logging.getLogger(__name__)


@dataclass
class SupportResistance:
    """支撑压力位"""
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    strong_support: Optional[float] = None
    strong_resistance: Optional[float] = None


@dataclass
class VolumeAnalysis:
    """成交量分析"""
    volume_ratio: float = 1.0
    volume_trend: str = "正常"
    volume_price_relation: str = "量价配合"
    validity: str = "有效"


@dataclass
class DeepAnalysisResult:
    """深度分析结果"""
    code: str
    name: str = ""
    current_price: float = 0.0
    
    technical_result: Optional[TechnicalMonitorResult] = None
    
    support_resistance: Optional[SupportResistance] = None
    volume_analysis: Optional[VolumeAnalysis] = None
    
    divergence_confirmed: bool = False
    divergence_risk_level: str = "低"
    
    risk_rating: str = "中"
    strategy_advice: str = "持有观望"
    
    timestamp: Optional[datetime] = None


@dataclass
class EveningMonitorResult:
    """晚间监测结果"""
    date: str
    time: str
    watch_list: List[str] = field(default_factory=list)
    portfolio_list: List[str] = field(default_factory=list)
    
    watch_results: Dict[str, TechnicalMonitorResult] = field(default_factory=dict)
    deep_analysis_results: Dict[str, DeepAnalysisResult] = field(default_factory=dict)
    
    summary: Dict[str, Any] = field(default_factory=dict)
    report_text: str = ""
    timestamp: Optional[datetime] = None


class EveningMonitorService:
    """晚间监测服务"""
    
    def __init__(self):
        self.config = get_config()
        self.technical_monitor = TechnicalMonitor()
        self._fetcher = None
        self._data_provider = None
    
    @property
    def fetcher(self):
        """延迟加载数据获取器"""
        if self._fetcher is None:
            from data_provider.akshare_fetcher import AkshareFetcher
            self._fetcher = AkshareFetcher()
        return self._fetcher
    
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
    
    def get_daily_data(self, code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """获取日线数据"""
        try:
            from datetime import timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 30)
            
            df = self.fetcher.get_daily_data(
                code,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
            )
            
            if df is None or df.empty:
                return None
            
            if 'date' not in df.columns:
                if df.index.name == 'date' or df.index.name == 'datetime':
                    df = df.reset_index()
                    df = df.rename(columns={df.columns[0]: 'date'})
            
            df = df.sort_values('date').reset_index(drop=True)
            return df
            
        except Exception as e:
            logger.error(f"获取股票 {code} 日线数据失败: {e}")
            return None
    
    def analyze_support_resistance(
        self, 
        df: pd.DataFrame,
        current_price: float,
    ) -> SupportResistance:
        """
        分析支撑压力位
        
        Args:
            df: 日线数据
            current_price: 当前价格
            
        Returns:
            支撑压力位分析结果
        """
        result = SupportResistance()
        
        if df is None or len(df) < 20:
            return result
        
        recent = df.tail(60)
        
        for i in range(len(recent) - 1):
            low = recent.iloc[i]['low']
            high = recent.iloc[i]['high']
            
            if low < current_price:
                result.support_levels.append(float(low))
            if high > current_price:
                result.resistance_levels.append(float(high))
        
        if result.support_levels:
            result.support_levels = sorted(list(set(result.support_levels)), reverse=True)[:5]
            result.strong_support = result.support_levels[0] if result.support_levels else None
        
        if result.resistance_levels:
            result.resistance_levels = sorted(list(set(result.resistance_levels)))[:5]
            result.strong_resistance = result.resistance_levels[0] if result.resistance_levels else None
        
        return result
    
    def analyze_volume(
        self, 
        df: pd.DataFrame,
    ) -> VolumeAnalysis:
        """
        分析成交量
        
        Args:
            df: 日线数据
            
        Returns:
            成交量分析结果
        """
        result = VolumeAnalysis()
        
        if df is None or len(df) < 10:
            return result
        
        recent = df.tail(10)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        avg_volume = recent['volume'].mean()
        current_volume = latest['volume']
        
        if avg_volume > 0:
            result.volume_ratio = float(current_volume / avg_volume)
        
        if result.volume_ratio > 1.5:
            result.volume_trend = "放量"
        elif result.volume_ratio < 0.7:
            result.volume_trend = "缩量"
        else:
            result.volume_trend = "正常"
        
        price_change = (latest['close'] - prev['close']) / prev['close'] * 100
        
        if price_change > 0 and result.volume_ratio > 1.2:
            result.volume_price_relation = "放量上涨"
            result.validity = "有效"
        elif price_change < 0 and result.volume_ratio > 1.2:
            result.volume_price_relation = "放量下跌"
            result.validity = "需警惕"
        elif price_change > 0 and result.volume_ratio < 0.8:
            result.volume_price_relation = "缩量上涨"
            result.validity = "动能不足"
        elif price_change < 0 and result.volume_ratio < 0.8:
            result.volume_price_relation = "缩量下跌"
            result.validity = "抛压减轻"
        else:
            result.volume_price_relation = "量价配合"
            result.validity = "有效"
        
        return result
    
    def confirm_divergence(
        self,
        divergence: Optional[DivergenceResult],
        df: pd.DataFrame,
    ) -> tuple:
        """
        确认背离信号
        
        Args:
            divergence: 背离检测结果
            df: 日线数据
            
        Returns:
            (是否确认, 风险等级)
        """
        if divergence is None or not divergence.confirmed:
            return False, "低"
        
        if df is None or len(df) < 5:
            return False, "低"
        
        latest = df.iloc[-1]
        
        if divergence.divergence_type.value == "顶背离":
            if latest['close'] < df.iloc[-3]['close']:
                return True, "高"
            elif latest['close'] < df.iloc[-2]['close']:
                return True, "中"
            else:
                return False, "低"
        
        elif divergence.divergence_type.value == "底背离":
            if latest['close'] > df.iloc[-3]['close']:
                return True, "低"
            elif latest['close'] > df.iloc[-2]['close']:
                return True, "低"
            else:
                return False, "低"
        
        return False, "低"
    
    def assess_risk(
        self,
        technical_result: TechnicalMonitorResult,
        support_resistance: SupportResistance,
        volume_analysis: VolumeAnalysis,
        divergence_confirmed: bool,
        divergence_risk: str,
    ) -> str:
        """
        评估技术面风险等级
        
        Args:
            technical_result: 技术分析结果
            support_resistance: 支撑压力位
            volume_analysis: 成交量分析
            divergence_confirmed: 背离是否确认
            divergence_risk: 背离风险等级
            
        Returns:
            风险等级（高/中/低）
        """
        risk_score = 0
        
        if technical_result.score < 30:
            risk_score += 3
        elif technical_result.score < 50:
            risk_score += 2
        elif technical_result.score < 70:
            risk_score += 1
        
        if divergence_confirmed and divergence_risk == "高":
            risk_score += 3
        elif divergence_confirmed and divergence_risk == "中":
            risk_score += 2
        
        if volume_analysis.validity == "需警惕":
            risk_score += 2
        elif volume_analysis.validity == "动能不足":
            risk_score += 1
        
        if technical_result.top_divergence and technical_result.top_divergence.confirmed:
            risk_score += 1
        
        if risk_score >= 5:
            return "高"
        elif risk_score >= 2:
            return "中"
        else:
            return "低"
    
    def generate_strategy_advice(
        self,
        risk_rating: str,
        technical_result: TechnicalMonitorResult,
        support_resistance: SupportResistance,
        has_position: bool = True,
    ) -> str:
        """
        生成持仓策略建议
        
        Args:
            risk_rating: 风险等级
            technical_result: 技术分析结果
            support_resistance: 支撑压力位
            has_position: 是否持有仓位
            
        Returns:
            策略建议
        """
        if risk_rating == "高":
            if has_position:
                return "建议减仓或止损，控制风险"
            else:
                return "暂不建议介入，等待风险释放"
        
        elif risk_rating == "中":
            if technical_result.score >= 60:
                if has_position:
                    return "可继续持有，关注支撑位"
                else:
                    return "可轻仓试探，设好止损"
            else:
                if has_position:
                    return "建议观望，若破支撑位考虑减仓"
                else:
                    return "暂观望，等待更明确信号"
        
        else:
            if technical_result.score >= 70:
                if has_position:
                    return "趋势良好，可继续持有或适当加仓"
                else:
                    return "可考虑建仓，关注支撑位"
            else:
                if has_position:
                    return "风险较低，可继续持有"
                else:
                    return "可关注，等待买入时机"
    
    def deep_analyze(
        self, 
        code: str,
        has_position: bool = True,
    ) -> DeepAnalysisResult:
        """
        执行深度技术分析
        
        Args:
            code: 股票代码
            has_position: 是否持有仓位
            
        Returns:
            深度分析结果
        """
        result = DeepAnalysisResult(
            code=code,
            timestamp=datetime.now(),
        )
        
        technical_result = self.technical_monitor.analyze(code, interval=60)
        result.technical_result = technical_result
        result.current_price = technical_result.current_price
        
        daily_df = self.get_daily_data(code, days=60)
        
        result.support_resistance = self.analyze_support_resistance(
            daily_df, result.current_price
        )
        
        result.volume_analysis = self.analyze_volume(daily_df)
        
        if technical_result.top_divergence:
            confirmed, risk = self.confirm_divergence(
                technical_result.top_divergence, daily_df
            )
            result.divergence_confirmed = confirmed
            result.divergence_risk_level = risk
        elif technical_result.bottom_divergence:
            confirmed, risk = self.confirm_divergence(
                technical_result.bottom_divergence, daily_df
            )
            result.divergence_confirmed = confirmed
            result.divergence_risk_level = risk
        
        result.risk_rating = self.assess_risk(
            technical_result,
            result.support_resistance,
            result.volume_analysis,
            result.divergence_confirmed,
            result.divergence_risk_level,
        )
        
        result.strategy_advice = self.generate_strategy_advice(
            result.risk_rating,
            technical_result,
            result.support_resistance,
            has_position,
        )
        
        return result
    
    def run_evening_monitor(
        self,
        watch_list: Optional[List[str]] = None,
        portfolio_list: Optional[List[str]] = None,
    ) -> EveningMonitorResult:
        """
        执行晚间监测
        
        Args:
            watch_list: 关注股票列表
            portfolio_list: 持仓股票列表
            
        Returns:
            晚间监测结果
        """
        logger.info("开始执行晚间监测...")
        
        now = datetime.now()
        result = EveningMonitorResult(
            date=now.strftime('%Y-%m-%d'),
            time=now.strftime('%H:%M'),
            timestamp=now,
        )
        
        if watch_list is None:
            watch_list = self.config.watch_list
        if portfolio_list is None:
            portfolio_list = self.config.stock_list
        
        result.watch_list = watch_list
        result.portfolio_list = portfolio_list
        
        for code in watch_list:
            try:
                technical_result = self.technical_monitor.analyze(code, interval=60)
                result.watch_results[code] = technical_result
            except Exception as e:
                logger.error(f"分析关注股票 {code} 失败: {e}")
        
        for code in portfolio_list:
            try:
                deep_result = self.deep_analyze(code, has_position=True)
                result.deep_analysis_results[code] = deep_result
            except Exception as e:
                logger.error(f"深度分析持仓股票 {code} 失败: {e}")
        
        result.summary = self._generate_summary(result)
        result.report_text = self.generate_report(result)
        
        logger.info("晚间监测完成")
        return result
    
    def _generate_summary(self, result: EveningMonitorResult) -> Dict[str, Any]:
        """生成摘要"""
        summary = {
            'watch_count': len(result.watch_results),
            'portfolio_count': len(result.deep_analysis_results),
            'high_risk_count': 0,
            'medium_risk_count': 0,
            'low_risk_count': 0,
            'high_risk_stocks': [],
        }
        
        for code, deep_result in result.deep_analysis_results.items():
            if deep_result.risk_rating == "高":
                summary['high_risk_count'] += 1
                summary['high_risk_stocks'].append(code)
            elif deep_result.risk_rating == "中":
                summary['medium_risk_count'] += 1
            else:
                summary['low_risk_count'] += 1
        
        return summary
    
    def generate_report(self, result: EveningMonitorResult) -> str:
        """生成晚间监测报告"""
        lines = []
        
        lines.append(f"# 🌙 晚间监测报告 - {result.date} {result.time}")
        lines.append("")
        
        summary = result.summary
        lines.append("## 📊 监测摘要")
        lines.append("")
        lines.append(f"- 关注股票: {summary['watch_count']} 只")
        lines.append(f"- 持仓股票: {summary['portfolio_count']} 只")
        lines.append("")
        lines.append("### 持仓风险分布")
        lines.append("")
        lines.append(f"| 风险等级 | 数量 |")
        lines.append(f"|----------|------|")
        lines.append(f"| 🔴 高风险 | {summary['high_risk_count']} |")
        lines.append(f"| 🟡 中风险 | {summary['medium_risk_count']} |")
        lines.append(f"| 🟢 低风险 | {summary['low_risk_count']} |")
        lines.append("")
        
        if summary['high_risk_stocks']:
            high_risk_with_names = []
            for code in summary['high_risk_stocks']:
                name = self.get_stock_name(code)
                if name:
                    high_risk_with_names.append(f"{code} ({name})")
                else:
                    high_risk_with_names.append(code)
            lines.append(f"⚠️ **高风险股票**: {', '.join(high_risk_with_names)}")
            lines.append("")
        
        if result.watch_results:
            lines.append("## 📈 关注股票技术指标监测")
            lines.append("")
            
            for code, tech_result in result.watch_results.items():
                name = self.get_stock_name(code)
                tech_result.name = name
                lines.append(self.technical_monitor.format_report(tech_result))
                lines.append("")
        
        if result.deep_analysis_results:
            lines.append("## 🔬 持仓股票深度技术分析")
            lines.append("")
            
            for code, deep_result in result.deep_analysis_results.items():
                name = self.get_stock_name(code)
                deep_result.name = name
                lines.append(self._format_deep_analysis(deep_result))
                lines.append("")
        
        if result.timestamp:
            lines.append("---")
            lines.append(f"生成时间: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)
    
    def _format_deep_analysis(self, result: DeepAnalysisResult) -> str:
        """格式化深度分析结果"""
        lines = []
        
        title = result.code
        if result.name:
            title = f"{result.code} ({result.name})"
        lines.append(f"### {title}")
        lines.append("")
        lines.append(f"**当前价格**: {result.current_price:.2f}")
        lines.append("")
        
        if result.technical_result:
            lines.append("#### 技术指标")
            lines.append("")
            lines.append(f"- 趋势: {result.technical_result.trend_status.value}")
            lines.append(f"- MACD: {result.technical_result.indicators.macd_signal}")
            lines.append(f"- KDJ: {result.technical_result.indicators.kdj_signal}")
            lines.append(f"- 综合评分: {result.technical_result.score}/100")
            lines.append("")
        
        if result.support_resistance:
            lines.append("#### 支撑压力位")
            lines.append("")
            if result.support_resistance.strong_support:
                lines.append(f"- **强支撑**: {result.support_resistance.strong_support:.2f}")
            if result.support_resistance.strong_resistance:
                lines.append(f"- **强压力**: {result.support_resistance.strong_resistance:.2f}")
            lines.append("")
        
        if result.volume_analysis:
            lines.append("#### 成交量验证")
            lines.append("")
            lines.append(f"- 量比: {result.volume_analysis.volume_ratio:.2f}")
            lines.append(f"- 量价关系: {result.volume_analysis.volume_price_relation}")
            lines.append(f"- 有效性: {result.volume_analysis.validity}")
            lines.append("")
        
        if result.divergence_confirmed:
            lines.append("#### ⚠️ 背离信号确认")
            lines.append("")
            lines.append(f"- 风险等级: {result.divergence_risk_level}")
            lines.append("")
        
        lines.append("#### 风险评级与持仓策略")
        lines.append("")
        risk_emoji = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(result.risk_rating, "⚪")
        lines.append(f"- 技术面风险评级: **{risk_emoji} {result.risk_rating}**")
        lines.append(f"- 持仓策略建议: **{result.strategy_advice}**")
        
        return "\n".join(lines)


def run_evening_monitor(
    watch_list: Optional[List[str]] = None,
    portfolio_list: Optional[List[str]] = None,
) -> EveningMonitorResult:
    """
    便捷函数：执行晚间监测
    
    Args:
        watch_list: 关注股票列表
        portfolio_list: 持仓股票列表
        
    Returns:
        晚间监测结果
    """
    service = EveningMonitorService()
    return service.run_evening_monitor(watch_list, portfolio_list)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    result = run_evening_monitor(
        watch_list=['600519', '300750'],
        portfolio_list=['600519'],
    )
    print(result.report_text)
