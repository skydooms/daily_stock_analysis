# -*- coding: utf-8 -*-
"""
===================================
价格区间分析服务
===================================

职责：
1. 计算持仓股票近N个月的价格区间数据
2. 计算各关键价格点至今的涨跌幅
3. 计算价格预警提示
4. 判断当前股价处于价格区间的位置
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd
import numpy as np

from src.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class PricePoint:
    """价格点"""
    price: float
    date: date
    change_to_now: float = 0.0


@dataclass
class PriceRangeResult:
    """价格区间分析结果"""
    code: str
    name: str = ""
    current_price: float = 0.0
    period_days: int = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    absolute_low: Optional[PricePoint] = None
    absolute_high: Optional[PricePoint] = None
    close_low: Optional[PricePoint] = None
    close_high: Optional[PricePoint] = None
    
    warning_prices: Dict[float, float] = field(default_factory=dict)
    position_in_range: str = ""
    position_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'current_price': self.current_price,
            'period_days': self.period_days,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'absolute_low': {
                'price': self.absolute_low.price,
                'date': self.absolute_low.date.isoformat(),
                'change_to_now': self.absolute_low.change_to_now,
            } if self.absolute_low else None,
            'absolute_high': {
                'price': self.absolute_high.price,
                'date': self.absolute_high.date.isoformat(),
                'change_to_now': self.absolute_high.change_to_now,
            } if self.absolute_high else None,
            'close_low': {
                'price': self.close_low.price,
                'date': self.close_low.date.isoformat(),
                'change_to_now': self.close_low.change_to_now,
            } if self.close_low else None,
            'close_high': {
                'price': self.close_high.price,
                'date': self.close_high.date.isoformat(),
                'change_to_now': self.close_high.change_to_now,
            } if self.close_high else None,
            'warning_prices': self.warning_prices,
            'position_in_range': self.position_in_range,
            'position_pct': self.position_pct,
        }


class PriceRangeAnalyzer:
    """价格区间分析器"""
    
    def __init__(self):
        self.config = get_config()
        self._fetcher = None
    
    @property
    def fetcher(self):
        """延迟加载数据获取器"""
        if self._fetcher is None:
            from data_provider.akshare_fetcher import AkshareFetcher
            self._fetcher = AkshareFetcher()
        return self._fetcher
    
    def get_stock_data(
        self, 
        code: str, 
        days: int = 90
    ) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据
        
        Args:
            code: 股票代码
            days: 天数
            
        Returns:
            DataFrame包含OHLCV数据，失败返回None
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 30)
            
            df = self.fetcher.get_daily_data(
                code,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
            )
            
            if df is None or df.empty:
                logger.warning(f"无法获取股票 {code} 的历史数据")
                return None
            
            if 'date' not in df.columns:
                if df.index.name == 'date' or df.index.name == 'datetime':
                    df = df.reset_index()
                    df = df.rename(columns={df.columns[0]: 'date'})
            
            df = df.sort_values('date').reset_index(drop=True)
            
            cutoff_date = datetime.now() - timedelta(days=days)
            df['date_dt'] = pd.to_datetime(df['date'])
            df = df[df['date_dt'] >= cutoff_date].reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"获取股票 {code} 历史数据失败: {e}")
            return None
    
    def analyze_price_range(
        self,
        code: str,
        days: int = 90,
        warning_levels: Optional[List[float]] = None,
    ) -> Optional[PriceRangeResult]:
        """
        分析价格区间
        
        Args:
            code: 股票代码
            days: 分析周期（天）
            warning_levels: 预警阈值列表（如 [20, 30, 40]）
            
        Returns:
            价格区间分析结果，失败返回None
        """
        if warning_levels is None:
            warning_levels = self.config.price_warning_levels
        
        df = self.get_stock_data(code, days)
        if df is None or df.empty or len(df) < 2:
            logger.warning(f"股票 {code} 数据不足，无法分析价格区间")
            return None
        
        result = PriceRangeResult(code=code)
        result.period_days = days
        
        if len(df) > 0:
            result.start_date = df['date_dt'].min().date()
            result.end_date = df['date_dt'].max().date()
        
        latest = df.iloc[-1]
        result.current_price = float(latest['close'])
        
        abs_low_idx = df['low'].idxmin()
        abs_low_row = df.loc[abs_low_idx]
        result.absolute_low = PricePoint(
            price=float(abs_low_row['low']),
            date=abs_low_row['date_dt'].date(),
        )
        
        abs_high_idx = df['high'].idxmax()
        abs_high_row = df.loc[abs_high_idx]
        result.absolute_high = PricePoint(
            price=float(abs_high_row['high']),
            date=abs_high_row['date_dt'].date(),
        )
        
        close_low_idx = df['close'].idxmin()
        close_low_row = df.loc[close_low_idx]
        result.close_low = PricePoint(
            price=float(close_low_row['close']),
            date=close_low_row['date_dt'].date(),
        )
        
        close_high_idx = df['close'].idxmax()
        close_high_row = df.loc[close_high_idx]
        result.close_high = PricePoint(
            price=float(close_high_row['close']),
            date=close_high_row['date_dt'].date(),
        )
        
        for point in [result.absolute_low, result.absolute_high, 
                      result.close_low, result.close_high]:
            if point and point.price > 0:
                point.change_to_now = round(
                    (result.current_price / point.price - 1) * 100, 2
                )
        
        if result.close_low and result.close_low.price > 0:
            for level in warning_levels:
                warning_price = result.close_low.price * (1 + level / 100)
                result.warning_prices[level] = round(warning_price, 2)
        
        if result.close_low and result.close_high:
            low = result.close_low.price
            high = result.close_high.price
            current = result.current_price
            
            if high > low:
                result.position_pct = round(
                    (current - low) / (high - low) * 100, 2
                )
                
                if result.position_pct < 20:
                    result.position_in_range = "低位区间（接近最低点）"
                elif result.position_pct < 40:
                    result.position_in_range = "中低区间"
                elif result.position_pct < 60:
                    result.position_in_range = "中间区间"
                elif result.position_pct < 80:
                    result.position_in_range = "中高区间"
                else:
                    result.position_in_range = "高位区间（接近最高点）"
        
        return result
    
    def analyze_multiple_periods(
        self,
        code: str,
        periods: Optional[List[int]] = None,
    ) -> Dict[int, Optional[PriceRangeResult]]:
        """
        分析多个周期的价格区间
        
        Args:
            code: 股票代码
            periods: 周期列表（天），如 [30, 90]
            
        Returns:
            {周期: 分析结果} 字典
        """
        if periods is None:
            periods = self.config.price_range_periods
        
        results = {}
        for period in periods:
            results[period] = self.analyze_price_range(code, period)
        
        return results
    
    def format_price_range_report(
        self, 
        result: PriceRangeResult
    ) -> str:
        """
        格式化价格区间报告
        
        Args:
            result: 价格区间分析结果
            
        Returns:
            Markdown格式的报告文本
        """
        lines = []
        
        title = result.code
        if result.name:
            title = f"{result.code} ({result.name})"
        lines.append(f"### {title}")
        lines.append("")
        lines.append(f"#### 近{result.period_days}天价格区间")
        
        if result.start_date and result.end_date:
            days_diff = (result.end_date - result.start_date).days
            lines.append(f"*{result.start_date} 至今，共 {days_diff} 天*")
        
        lines.append("")
        lines.append("| 指标 | 价格 | 日期 | 至今涨跌幅 |")
        lines.append("|------|------|------|------------|")
        
        if result.absolute_low:
            lines.append(
                f"| 绝对最低点 | {result.absolute_low.price:.2f} | "
                f"{result.absolute_low.date} | {result.absolute_low.change_to_now:+.2f}% |"
            )
        
        if result.absolute_high:
            lines.append(
                f"| 绝对最高点 | {result.absolute_high.price:.2f} | "
                f"{result.absolute_high.date} | {result.absolute_high.change_to_now:+.2f}% |"
            )
        
        if result.close_low:
            lines.append(
                f"| 收盘最低点 | {result.close_low.price:.2f} | "
                f"{result.close_low.date} | {result.close_low.change_to_now:+.2f}% |"
            )
        
        if result.close_high:
            lines.append(
                f"| 收盘最高点 | {result.close_high.price:.2f} | "
                f"{result.close_high.date} | {result.close_high.change_to_now:+.2f}% |"
            )
        
        lines.append("")
        lines.append("#### 价格预警")
        lines.append("")
        lines.append(f"- 当前价格: **{result.current_price:.2f}**")
        
        if result.warning_prices:
            for level, price in sorted(result.warning_prices.items()):
                lines.append(f"- ⚠️ 较最低点上涨{level}%: {price:.2f}")
        
        lines.append(f"- 📍 当前位置: {result.position_in_range} ({result.position_pct:.1f}%)")
        lines.append("")
        
        return "\n".join(lines)
    
    def format_multi_period_report(
        self,
        code: str,
        results: Dict[int, Optional[PriceRangeResult]],
        name: str = "",
    ) -> str:
        """
        格式化多周期价格区间报告
        
        Args:
            code: 股票代码
            results: 多周期分析结果
            name: 股票名称
            
        Returns:
            Markdown格式的报告文本
        """
        lines = []
        
        title = f"{code} ({name})" if name else code
        lines.append(f"## 💰 {title} 价格区间分析")
        lines.append("")
        
        for period, result in sorted(results.items()):
            if result:
                lines.append(self.format_price_range_report(result))
        
        return "\n".join(lines)


def get_price_range_analyzer() -> PriceRangeAnalyzer:
    """获取价格区间分析器实例"""
    return PriceRangeAnalyzer()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    analyzer = PriceRangeAnalyzer()
    results = analyzer.analyze_multiple_periods("600519", [30, 90])
    
    for period, result in results.items():
        if result:
            print(f"\n=== {period}天价格区间 ===")
            print(analyzer.format_price_range_report(result))
