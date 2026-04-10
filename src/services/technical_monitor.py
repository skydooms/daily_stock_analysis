# -*- coding: utf-8 -*-
"""
===================================
技术指标监测服务
===================================

职责：
1. 计算60/120分钟均线系统状态
2. 计算MACD指标状态
3. 计算KDJ指标状态
4. 检测顶背离与底背离形态
5. 生成技术指标综合评分及操作建议
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd
import numpy as np

from src.config import get_config
from src.data.stock_mapping import STOCK_NAME_MAP, is_meaningful_stock_name

logger = logging.getLogger(__name__)


class TrendStatus(Enum):
    """趋势状态"""
    STRONG_BULL = "强势多头"
    BULL = "多头排列"
    WEAK_BULL = "弱势多头"
    CONSOLIDATION = "盘整"
    WEAK_BEAR = "弱势空头"
    BEAR = "空头排列"
    STRONG_BEAR = "强势空头"


class MACDStatus(Enum):
    """MACD状态"""
    GOLDEN_CROSS_ZERO = "零轴上金叉"
    GOLDEN_CROSS = "金叉"
    BULLISH = "多头"
    NEUTRAL = "中性"
    CROSSING_UP = "上穿零轴"
    CROSSING_DOWN = "下穿零轴"
    BEARISH = "空头"
    DEATH_CROSS = "死叉"


class KDJStatus(Enum):
    """KDJ状态"""
    OVERBOUGHT = "超买"
    STRONG_BUY = "强势"
    NEUTRAL = "中性"
    WEAK = "弱势"
    OVERSOLD = "超卖"
    BLUNTING = "钝化"


class DivergenceType(Enum):
    """背离类型"""
    TOP = "顶背离"
    BOTTOM = "底背离"
    NONE = "无背离"


@dataclass
class DivergenceResult:
    """背离检测结果"""
    divergence_type: DivergenceType = DivergenceType.NONE
    strength: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    price_high1: float = 0.0
    price_high2: float = 0.0
    indicator_high1: float = 0.0
    indicator_high2: float = 0.0
    confirmed: bool = False
    risk_level: str = "低"


@dataclass
class TechnicalIndicators:
    """技术指标数据"""
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    
    macd_dif: float = 0.0
    macd_dea: float = 0.0
    macd_bar: float = 0.0
    macd_status: MACDStatus = MACDStatus.NEUTRAL
    macd_signal: str = ""
    
    kdj_k: float = 50.0
    kdj_d: float = 50.0
    kdj_j: float = 50.0
    kdj_status: KDJStatus = KDJStatus.NEUTRAL
    kdj_signal: str = ""
    
    rsi_6: float = 50.0
    rsi_12: float = 50.0
    rsi_24: float = 50.0


@dataclass
class TechnicalMonitorResult:
    """技术监测结果"""
    code: str
    name: str = ""
    current_price: float = 0.0
    interval: int = 60
    
    trend_status: TrendStatus = TrendStatus.CONSOLIDATION
    trend_signal: str = ""
    trend_strength: float = 50.0
    
    indicators: TechnicalIndicators = field(default_factory=TechnicalIndicators)
    
    top_divergence: Optional[DivergenceResult] = None
    bottom_divergence: Optional[DivergenceResult] = None
    
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    
    score: int = 50
    advice: str = "观望"
    reasons: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'current_price': self.current_price,
            'interval': self.interval,
            'trend_status': self.trend_status.value,
            'trend_signal': self.trend_signal,
            'trend_strength': self.trend_strength,
            'indicators': {
                'ma5': self.indicators.ma5,
                'ma10': self.indicators.ma10,
                'ma20': self.indicators.ma20,
                'ma60': self.indicators.ma60,
                'macd_dif': self.indicators.macd_dif,
                'macd_dea': self.indicators.macd_dea,
                'macd_bar': self.indicators.macd_bar,
                'macd_status': self.indicators.macd_status.value,
                'macd_signal': self.indicators.macd_signal,
                'kdj_k': self.indicators.kdj_k,
                'kdj_d': self.indicators.kdj_d,
                'kdj_j': self.indicators.kdj_j,
                'kdj_status': self.indicators.kdj_status.value,
                'kdj_signal': self.indicators.kdj_signal,
                'rsi_6': self.indicators.rsi_6,
                'rsi_12': self.indicators.rsi_12,
                'rsi_24': self.indicators.rsi_24,
            },
            'top_divergence': {
                'type': self.top_divergence.divergence_type.value,
                'strength': self.top_divergence.strength,
                'confirmed': self.top_divergence.confirmed,
                'risk_level': self.top_divergence.risk_level,
            } if self.top_divergence else None,
            'bottom_divergence': {
                'type': self.bottom_divergence.divergence_type.value,
                'strength': self.bottom_divergence.strength,
                'confirmed': self.bottom_divergence.confirmed,
                'risk_level': self.bottom_divergence.risk_level,
            } if self.bottom_divergence else None,
            'support_levels': self.support_levels,
            'resistance_levels': self.resistance_levels,
            'score': self.score,
            'advice': self.advice,
            'reasons': self.reasons,
            'risks': self.risks,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


class TechnicalMonitor:
    """技术指标监测器"""
    
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
    
    def get_stock_name(self, code: str) -> str:
        """获取股票名称"""
        normalized_code = code.strip().upper()
        
        if normalized_code.endswith(".HK"):
            hk_code = normalized_code[:-3]
            if hk_code in STOCK_NAME_MAP:
                return STOCK_NAME_MAP[hk_code]
            if len(hk_code) == 5 and hk_code.startswith("0"):
                hk_code_4 = hk_code[1:]
                if hk_code_4 in STOCK_NAME_MAP:
                    return STOCK_NAME_MAP[hk_code_4]
        
        if normalized_code.startswith("HK"):
            hk_code = normalized_code[2:]
            if hk_code in STOCK_NAME_MAP:
                return STOCK_NAME_MAP[hk_code]
            if len(hk_code) == 5 and hk_code.startswith("0"):
                hk_code_4 = hk_code[1:]
                if hk_code_4 in STOCK_NAME_MAP:
                    return STOCK_NAME_MAP[hk_code_4]
        
        if normalized_code in STOCK_NAME_MAP:
            return STOCK_NAME_MAP[normalized_code]
        
        if code in STOCK_NAME_MAP:
            return STOCK_NAME_MAP[code]
        
        return code
    
    def get_intraday_data(
        self, 
        code: str, 
        interval: int = 60
    ) -> Optional[pd.DataFrame]:
        """
        获取日线数据（用于技术分析）
        
        Args:
            code: 股票代码
            interval: 时间间隔（分钟，暂时忽略，使用日线数据）
            
        Returns:
            DataFrame，失败返回None
        """
        try:
            from datetime import datetime, timedelta
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=120)
            
            df = self.fetcher.get_daily_data(
                code,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
            )
            
            if df is None or df.empty:
                logger.warning(f"无法获取股票 {code} 的日线数据")
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
    
    def calculate_mas(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算均线"""
        df = df.copy()
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        if len(df) >= 60:
            df['MA60'] = df['close'].rolling(window=60).mean()
        else:
            df['MA60'] = df['MA20']
        return df
    
    def calculate_macd(
        self, 
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> pd.DataFrame:
        """计算MACD指标"""
        df = df.copy()
        
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        
        df['MACD_DIF'] = ema_fast - ema_slow
        df['MACD_DEA'] = df['MACD_DIF'].ewm(span=signal, adjust=False).mean()
        df['MACD_BAR'] = (df['MACD_DIF'] - df['MACD_DEA']) * 2
        
        return df
    
    def calculate_kdj(
        self,
        df: pd.DataFrame,
        n: int = 9,
        m1: int = 3,
        m2: int = 3,
    ) -> pd.DataFrame:
        """
        计算KDJ指标
        
        RSV = (Close - LowN) / (HighN - LowN) * 100
        K = SMA(RSV, M1)
        D = SMA(K, M2)
        J = 3K - 2D
        """
        df = df.copy()
        
        low_n = df['low'].rolling(window=n).min()
        high_n = df['high'].rolling(window=n).max()
        
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        rsv = rsv.fillna(50)
        
        df['KDJ_K'] = rsv.ewm(alpha=1/m1, adjust=False).mean()
        df['KDJ_D'] = df['KDJ_K'].ewm(alpha=1/m2, adjust=False).mean()
        df['KDJ_J'] = 3 * df['KDJ_K'] - 2 * df['KDJ_D']
        
        return df
    
    def calculate_rsi(
        self,
        df: pd.DataFrame,
        periods: List[int] = [6, 12, 24],
    ) -> pd.DataFrame:
        """计算RSI指标"""
        df = df.copy()
        
        for period in periods:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi = rsi.fillna(50)
            
            df[f'RSI_{period}'] = rsi
        
        return df
    
    def analyze_trend(self, df: pd.DataFrame, result: TechnicalMonitorResult) -> None:
        """分析趋势状态"""
        latest = df.iloc[-1]
        ma5, ma10, ma20 = latest['MA5'], latest['MA10'], latest['MA20']
        
        result.indicators.ma5 = float(ma5)
        result.indicators.ma10 = float(ma10)
        result.indicators.ma20 = float(ma20)
        result.indicators.ma60 = float(latest.get('MA60', ma20))
        
        if pd.isna(ma5) or pd.isna(ma10) or pd.isna(ma20):
            result.trend_status = TrendStatus.CONSOLIDATION
            result.trend_signal = "数据不足"
            return
        
        if ma5 > ma10 > ma20:
            result.trend_status = TrendStatus.BULL
            result.trend_signal = "多头排列 MA5>MA10>MA20"
            result.trend_strength = 75
        elif ma5 < ma10 < ma20:
            result.trend_status = TrendStatus.BEAR
            result.trend_signal = "空头排列 MA5<MA10<MA20"
            result.trend_strength = 25
        elif ma5 > ma10:
            result.trend_status = TrendStatus.WEAK_BULL
            result.trend_signal = "弱势多头 MA5>MA10"
            result.trend_strength = 55
        elif ma5 < ma10:
            result.trend_status = TrendStatus.WEAK_BEAR
            result.trend_signal = "弱势空头 MA5<MA10"
            result.trend_strength = 40
        else:
            result.trend_status = TrendStatus.CONSOLIDATION
            result.trend_signal = "均线缠绕，趋势不明"
            result.trend_strength = 50
    
    def analyze_macd(self, df: pd.DataFrame, result: TechnicalMonitorResult) -> None:
        """分析MACD指标"""
        if len(df) < 26:
            result.indicators.macd_signal = "数据不足"
            return
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        result.indicators.macd_dif = float(latest['MACD_DIF'])
        result.indicators.macd_dea = float(latest['MACD_DEA'])
        result.indicators.macd_bar = float(latest['MACD_BAR'])
        
        prev_diff = prev['MACD_DIF'] - prev['MACD_DEA']
        curr_diff = latest['MACD_DIF'] - latest['MACD_DEA']
        
        is_golden_cross = prev_diff <= 0 and curr_diff > 0
        is_death_cross = prev_diff >= 0 and curr_diff < 0
        is_crossing_up = prev['MACD_DIF'] <= 0 and latest['MACD_DIF'] > 0
        is_crossing_down = prev['MACD_DIF'] >= 0 and latest['MACD_DIF'] < 0
        
        if is_golden_cross and latest['MACD_DIF'] > 0:
            result.indicators.macd_status = MACDStatus.GOLDEN_CROSS_ZERO
            result.indicators.macd_signal = "⭐ 零轴上金叉，强烈买入信号！"
        elif is_crossing_up:
            result.indicators.macd_status = MACDStatus.CROSSING_UP
            result.indicators.macd_signal = "⚡ DIF上穿零轴，趋势转强"
        elif is_golden_cross:
            result.indicators.macd_status = MACDStatus.GOLDEN_CROSS
            result.indicators.macd_signal = "✅ 金叉，趋势向上"
        elif is_death_cross:
            result.indicators.macd_status = MACDStatus.DEATH_CROSS
            result.indicators.macd_signal = "❌ 死叉，趋势向下"
        elif is_crossing_down:
            result.indicators.macd_status = MACDStatus.CROSSING_DOWN
            result.indicators.macd_signal = "⚠️ DIF下穿零轴，趋势转弱"
        elif latest['MACD_DIF'] > 0 and latest['MACD_DEA'] > 0:
            result.indicators.macd_status = MACDStatus.BULLISH
            result.indicators.macd_signal = "✓ 多头排列，持续上涨"
        elif latest['MACD_DIF'] < 0 and latest['MACD_DEA'] < 0:
            result.indicators.macd_status = MACDStatus.BEARISH
            result.indicators.macd_signal = "⚠ 空头排列，持续下跌"
        else:
            result.indicators.macd_status = MACDStatus.BULLISH
            result.indicators.macd_signal = "MACD 中性区域"
    
    def analyze_kdj(self, df: pd.DataFrame, result: TechnicalMonitorResult) -> None:
        """分析KDJ指标"""
        if len(df) < 9:
            result.indicators.kdj_signal = "数据不足"
            return
        
        latest = df.iloc[-1]
        
        result.indicators.kdj_k = float(latest['KDJ_K'])
        result.indicators.kdj_d = float(latest['KDJ_D'])
        result.indicators.kdj_j = float(latest['KDJ_J'])
        
        k, d, j = result.indicators.kdj_k, result.indicators.kdj_d, result.indicators.kdj_j
        
        if j > 100 or j < 0:
            result.indicators.kdj_status = KDJStatus.BLUNTING
            result.indicators.kdj_signal = f"⚠️ KDJ钝化 (J={j:.1f})"
        elif k > 80 and d > 80:
            result.indicators.kdj_status = KDJStatus.OVERBOUGHT
            result.indicators.kdj_signal = f"⚠️ KDJ超买 (K={k:.1f}, D={d:.1f})"
        elif k < 20 and d < 20:
            result.indicators.kdj_status = KDJStatus.OVERSOLD
            result.indicators.kdj_signal = f"⭐ KDJ超卖 (K={k:.1f}, D={d:.1f})"
        elif k > 60:
            result.indicators.kdj_status = KDJStatus.STRONG_BUY
            result.indicators.kdj_signal = f"✅ KDJ强势 (K={k:.1f})"
        elif k < 40:
            result.indicators.kdj_status = KDJStatus.WEAK
            result.indicators.kdj_signal = f"⚡ KDJ弱势 (K={k:.1f})"
        else:
            result.indicators.kdj_status = KDJStatus.NEUTRAL
            result.indicators.kdj_signal = f"KDJ中性 (K={k:.1f})"
    
    def detect_divergence(
        self,
        df: pd.DataFrame,
        lookback: int = 20,
    ) -> Tuple[Optional[DivergenceResult], Optional[DivergenceResult]]:
        """
        检测顶背离和底背离
        
        Args:
            df: 包含价格和指标数据的DataFrame
            lookback: 回溯周期
            
        Returns:
            (顶背离结果, 底背离结果)
        """
        if len(df) < lookback:
            return None, None
        
        recent = df.tail(lookback).copy()
        
        top_divergence = self._detect_top_divergence(recent)
        bottom_divergence = self._detect_bottom_divergence(recent)
        
        return top_divergence, bottom_divergence
    
    def _detect_top_divergence(self, df: pd.DataFrame) -> Optional[DivergenceResult]:
        """检测顶背离"""
        try:
            peaks_idx = self._find_peaks(df['close'].values, distance=3)
            
            if len(peaks_idx) < 2:
                return None
            
            last_two_peaks = peaks_idx[-2:]
            
            price1 = df.iloc[last_two_peaks[0]]['close']
            price2 = df.iloc[last_two_peaks[1]]['close']
            
            if price2 <= price1:
                return None
            
            macd1 = abs(df.iloc[last_two_peaks[0]]['MACD_DIF'])
            macd2 = abs(df.iloc[last_two_peaks[1]]['MACD_DIF'])
            
            if macd2 >= macd1:
                return None
            
            strength = min(100, (price2 - price1) / price1 * 100 / (macd1 - macd2) / macd1 * 100)
            
            return DivergenceResult(
                divergence_type=DivergenceType.TOP,
                strength=round(strength, 2),
                start_date=df.iloc[last_two_peaks[0]]['date'],
                end_date=df.iloc[last_two_peaks[1]]['date'],
                price_high1=float(price1),
                price_high2=float(price2),
                indicator_high1=float(macd1),
                indicator_high2=float(macd2),
                confirmed=True,
                risk_level="高" if strength > 50 else "中",
            )
            
        except Exception as e:
            logger.debug(f"检测顶背离失败: {e}")
            return None
    
    def _detect_bottom_divergence(self, df: pd.DataFrame) -> Optional[DivergenceResult]:
        """检测底背离"""
        try:
            troughs_idx = self._find_troughs(df['close'].values, distance=3)
            
            if len(troughs_idx) < 2:
                return None
            
            last_two_troughs = troughs_idx[-2:]
            
            price1 = df.iloc[last_two_troughs[0]]['close']
            price2 = df.iloc[last_two_troughs[1]]['close']
            
            if price2 >= price1:
                return None
            
            macd1 = abs(df.iloc[last_two_troughs[0]]['MACD_DIF'])
            macd2 = abs(df.iloc[last_two_troughs[1]]['MACD_DIF'])
            
            if macd2 <= macd1:
                return None
            
            strength = min(100, (price1 - price2) / price1 * 100 / (macd2 - macd1) / macd1 * 100)
            
            return DivergenceResult(
                divergence_type=DivergenceType.BOTTOM,
                strength=round(strength, 2),
                start_date=df.iloc[last_two_troughs[0]]['date'],
                end_date=df.iloc[last_two_troughs[1]]['date'],
                price_high1=float(price1),
                price_high2=float(price2),
                indicator_high1=float(macd1),
                indicator_high2=float(macd2),
                confirmed=True,
                risk_level="低",
            )
            
        except Exception as e:
            logger.debug(f"检测底背离失败: {e}")
            return None
    
    def _find_peaks(self, arr: np.ndarray, distance: int = 3) -> np.ndarray:
        """寻找峰值点"""
        peaks = []
        for i in range(distance, len(arr) - distance):
            if arr[i] == max(arr[i-distance:i+distance+1]):
                peaks.append(i)
        return np.array(peaks)
    
    def _find_troughs(self, arr: np.ndarray, distance: int = 3) -> np.ndarray:
        """寻找谷值点"""
        troughs = []
        for i in range(distance, len(arr) - distance):
            if arr[i] == min(arr[i-distance:i+distance+1]):
                troughs.append(i)
        return np.array(troughs)
    
    def calculate_score(self, result: TechnicalMonitorResult) -> int:
        """
        计算综合评分
        
        评分维度：
        - 趋势（30分）
        - MACD（25分）
        - KDJ（25分）
        - 背离（20分）
        """
        score = 50
        
        trend_scores = {
            TrendStatus.STRONG_BULL: 30,
            TrendStatus.BULL: 25,
            TrendStatus.WEAK_BULL: 18,
            TrendStatus.CONSOLIDATION: 15,
            TrendStatus.WEAK_BEAR: 10,
            TrendStatus.BEAR: 5,
            TrendStatus.STRONG_BEAR: 0,
        }
        score = trend_scores.get(result.trend_status, 15)
        
        macd_scores = {
            MACDStatus.GOLDEN_CROSS_ZERO: 25,
            MACDStatus.GOLDEN_CROSS: 20,
            MACDStatus.CROSSING_UP: 18,
            MACDStatus.BULLISH: 15,
            MACDStatus.NEUTRAL: 12,
            MACDStatus.BEARISH: 8,
            MACDStatus.CROSSING_DOWN: 5,
            MACDStatus.DEATH_CROSS: 0,
        }
        score += macd_scores.get(result.indicators.macd_status, 12)
        
        kdj_scores = {
            KDJStatus.OVERSOLD: 25,
            KDJStatus.STRONG_BUY: 20,
            KDJStatus.NEUTRAL: 15,
            KDJStatus.WEAK: 10,
            KDJStatus.BLUNTING: 8,
            KDJStatus.OVERBOUGHT: 5,
        }
        score += kdj_scores.get(result.indicators.kdj_status, 15)
        
        if result.top_divergence and result.top_divergence.confirmed:
            score -= int(result.top_divergence.strength / 5)
        if result.bottom_divergence and result.bottom_divergence.confirmed:
            score += int(result.bottom_divergence.strength / 5)
        
        return max(0, min(100, score))
    
    def generate_advice(self, score: int) -> str:
        """生成操作建议"""
        if score >= 75:
            return "强烈买入"
        elif score >= 60:
            return "买入"
        elif score >= 45:
            return "持有观望"
        elif score >= 30:
            return "减仓"
        else:
            return "卖出"
    
    def analyze(
        self, 
        code: str, 
        interval: int = 60
    ) -> TechnicalMonitorResult:
        """
        执行技术分析
        
        Args:
            code: 股票代码
            interval: 时间间隔（分钟）
            
        Returns:
            技术监测结果
        """
        result = TechnicalMonitorResult(
            code=code,
            interval=interval,
            timestamp=datetime.now(),
        )
        result.name = self.get_stock_name(code)
        
        df = self.get_intraday_data(code, interval)
        if df is None or df.empty or len(df) < 20:
            result.advice = "数据不足"
            return result
        
        df = self.calculate_mas(df)
        df = self.calculate_macd(df)
        df = self.calculate_kdj(
            df, 
            n=self.config.kdj_n,
            m1=self.config.kdj_m1,
            m2=self.config.kdj_m2,
        )
        df = self.calculate_rsi(df)
        
        latest = df.iloc[-1]
        result.current_price = float(latest['close'])
        
        result.indicators.rsi_6 = float(latest.get('RSI_6', 50))
        result.indicators.rsi_12 = float(latest.get('RSI_12', 50))
        result.indicators.rsi_24 = float(latest.get('RSI_24', 50))
        
        self.analyze_trend(df, result)
        self.analyze_macd(df, result)
        self.analyze_kdj(df, result)
        
        top_div, bottom_div = self.detect_divergence(
            df, 
            lookback=self.config.divergence_lookback,
        )
        result.top_divergence = top_div
        result.bottom_divergence = bottom_div
        
        result.score = self.calculate_score(result)
        result.advice = self.generate_advice(result.score)
        
        return result
    
    def format_report(self, result: TechnicalMonitorResult) -> str:
        """
        格式化技术监测报告
        
        Args:
            result: 技术监测结果
            
        Returns:
            Markdown格式的报告文本
        """
        lines = []
        
        title = result.code
        if result.name:
            title = f"{result.code} ({result.name})"
        lines.append(f"### {title}")
        lines.append("")
        
        lines.append(f"**当前价格**: {result.current_price:.2f}")
        lines.append("")
        
        lines.append("#### 均线系统")
        lines.append(f"- MA5: {result.indicators.ma5:.2f} | MA10: {result.indicators.ma10:.2f} | MA20: {result.indicators.ma20:.2f}")
        lines.append(f"- 状态: {result.trend_status.value} ({result.trend_signal})")
        lines.append("")
        
        lines.append("#### MACD指标")
        lines.append(f"- DIF: {result.indicators.macd_dif:.4f} | DEA: {result.indicators.macd_dea:.4f} | MACD: {result.indicators.macd_bar:.4f}")
        lines.append(f"- 信号: {result.indicators.macd_signal}")
        lines.append("")
        
        lines.append("#### KDJ指标")
        lines.append(f"- K: {result.indicators.kdj_k:.1f} | D: {result.indicators.kdj_d:.1f} | J: {result.indicators.kdj_j:.1f}")
        lines.append(f"- 状态: {result.indicators.kdj_signal}")
        lines.append("")
        
        if result.top_divergence:
            lines.append("#### ⚠️ 顶背离检测")
            lines.append(f"- 强度: {result.top_divergence.strength:.1f}")
            lines.append(f"- 风险等级: {result.top_divergence.risk_level}")
            lines.append("")
        
        if result.bottom_divergence:
            lines.append("#### ✅ 底背离检测")
            lines.append(f"- 强度: {result.bottom_divergence.strength:.1f}")
            lines.append("")
        
        lines.append("#### 综合评分")
        lines.append(f"- **评分**: {result.score}/100")
        lines.append(f"- **操作建议**: {result.advice}")
        
        if result.timestamp:
            lines.append("")
            lines.append(f"*分析时间: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(lines)


def get_technical_monitor() -> TechnicalMonitor:
    """获取技术监测器实例"""
    return TechnicalMonitor()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    monitor = TechnicalMonitor()
    result = monitor.analyze("600519", interval=60)
    print(monitor.format_report(result))
