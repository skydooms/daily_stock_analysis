# -*- coding: utf-8 -*-
"""
===================================
美股市场数据服务
===================================

职责：
1. 获取道琼斯工业平均指数、纳斯达克综合指数的最新收盘数据
2. 统计并排序当日涨跌幅排名靠前的板块
3. 生成板块涨跌分布图表
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pandas as pd

from src.config import get_config

logger = logging.getLogger(__name__)

US_SECTOR_ETFS = {
    'XLK': '科技',
    'XLF': '金融',
    'XLE': '能源',
    'XLV': '医疗',
    'XLY': '消费',
    'XLI': '工业',
    'XLB': '材料',
    'XLRE': '房地产',
    'XLU': '公用事业',
    'XLC': '通信',
    'IYZ': '电信',
}


@dataclass
class USIndexData:
    """美股指数数据"""
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: Optional[int] = None
    timestamp: Optional[datetime] = None


@dataclass
class SectorData:
    """板块数据"""
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: Optional[int] = None


@dataclass
class USMarketData:
    """美股市场数据"""
    indices: List[USIndexData] = field(default_factory=list)
    sectors: List[SectorData] = field(default_factory=list)
    top_gainers: List[SectorData] = field(default_factory=list)
    top_losers: List[SectorData] = field(default_factory=list)
    timestamp: Optional[datetime] = None


class USMarketService:
    """美股市场数据服务"""
    
    INDEX_SYMBOLS = {
        '^DJI': '道琼斯工业平均指数',
        '^IXIC': '纳斯达克综合指数',
        '^GSPC': '标普500指数',
    }
    
    def __init__(self):
        self.config = get_config()
        self._yf = None
    
    @property
    def yf(self):
        """延迟加载yfinance"""
        if self._yf is None:
            try:
                import yfinance as yf
                self._yf = yf
            except ImportError:
                logger.error("yfinance库未安装，请执行: pip install yfinance")
                raise ImportError("请安装yfinance库: pip install yfinance")
        return self._yf
    
    def get_index_data(self, symbol: str) -> Optional[USIndexData]:
        """
        获取单个指数数据
        
        Args:
            symbol: 指数代码（如 ^DJI, ^IXIC）
            
        Returns:
            指数数据，失败返回None
        """
        try:
            ticker = self.yf.Ticker(symbol)
            hist = ticker.history(period='2d')
            
            if hist is None or hist.empty or len(hist) < 1:
                logger.warning(f"无法获取指数 {symbol} 的历史数据")
                return None
            
            latest = hist.iloc[-1]
            if len(hist) >= 2:
                prev = hist.iloc[-2]
                change = float(latest['Close'] - prev['Close'])
                change_pct = float((latest['Close'] / prev['Close'] - 1) * 100)
            else:
                change = 0.0
                change_pct = 0.0
            
            name = self.INDEX_SYMBOLS.get(symbol, symbol)
            
            return USIndexData(
                symbol=symbol,
                name=name,
                price=float(latest['Close']),
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                volume=int(latest.get('Volume', 0)) if 'Volume' in latest else None,
                timestamp=datetime.now(),
            )
            
        except Exception as e:
            logger.error(f"获取指数 {symbol} 数据失败: {e}")
            return None
    
    def get_all_indices(self) -> List[USIndexData]:
        """
        获取所有主要指数数据
        
        Returns:
            指数数据列表
        """
        indices = []
        for symbol in self.INDEX_SYMBOLS:
            data = self.get_index_data(symbol)
            if data:
                indices.append(data)
        return indices
    
    def get_sector_data(self, symbol: str) -> Optional[SectorData]:
        """
        获取单个板块ETF数据
        
        Args:
            symbol: ETF代码（如 XLK, XLF）
            
        Returns:
            板块数据，失败返回None
        """
        try:
            ticker = self.yf.Ticker(symbol)
            hist = ticker.history(period='2d')
            
            if hist is None or hist.empty or len(hist) < 1:
                logger.warning(f"无法获取板块ETF {symbol} 的历史数据")
                return None
            
            latest = hist.iloc[-1]
            if len(hist) >= 2:
                prev = hist.iloc[-2]
                change = float(latest['Close'] - prev['Close'])
                change_pct = float((latest['Close'] / prev['Close'] - 1) * 100)
            else:
                change = 0.0
                change_pct = 0.0
            
            name = US_SECTOR_ETFS.get(symbol, symbol)
            
            return SectorData(
                symbol=symbol,
                name=name,
                price=float(latest['Close']),
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                volume=int(latest.get('Volume', 0)) if 'Volume' in latest else None,
            )
            
        except Exception as e:
            logger.error(f"获取板块ETF {symbol} 数据失败: {e}")
            return None
    
    def get_all_sectors(self) -> List[SectorData]:
        """
        获取所有板块数据
        
        Returns:
            板块数据列表
        """
        sectors = []
        for symbol in US_SECTOR_ETFS:
            data = self.get_sector_data(symbol)
            if data:
                sectors.append(data)
        return sectors
    
    def get_sector_rankings(self) -> tuple:
        """
        获取板块涨跌排名
        
        Returns:
            (领涨板块列表, 领跌板块列表)
        """
        sectors = self.get_all_sectors()
        
        if not sectors:
            return [], []
        
        sorted_sectors = sorted(sectors, key=lambda x: x.change_pct, reverse=True)
        
        top_gainers = sorted_sectors[:5]
        top_losers = sorted_sectors[-5:][::-1]
        
        return top_gainers, top_losers
    
    def get_market_summary(self) -> USMarketData:
        """
        获取美股市场摘要
        
        Returns:
            美股市场数据
        """
        indices = self.get_all_indices()
        sectors = self.get_all_sectors()
        top_gainers, top_losers = self.get_sector_rankings()
        
        return USMarketData(
            indices=indices,
            sectors=sectors,
            top_gainers=top_gainers,
            top_losers=top_losers,
            timestamp=datetime.now(),
        )
    
    def format_market_report(self, data: USMarketData) -> str:
        """
        格式化市场报告
        
        Args:
            data: 美股市场数据
            
        Returns:
            Markdown格式的报告文本
        """
        lines = []
        
        lines.append("## 📊 美股市场分析")
        lines.append("")
        
        if data.indices:
            lines.append("### 主要指数")
            lines.append("")
            for idx in data.indices:
                emoji = "🟢" if idx.change_pct >= 0 else "🔴"
                lines.append(f"- {idx.name}: {idx.price:,.2f} ({emoji}{idx.change_pct:+.2f}%)")
            lines.append("")
        
        if data.top_gainers:
            lines.append("### 🔥 领涨板块")
            lines.append("")
            lines.append("| 板块 | 涨跌幅 |")
            lines.append("|------|--------|")
            for sector in data.top_gainers:
                lines.append(f"| {sector.name} | {sector.change_pct:+.2f}% |")
            lines.append("")
        
        if data.top_losers:
            lines.append("### ❄️ 领跌板块")
            lines.append("")
            lines.append("| 板块 | 涨跌幅 |")
            lines.append("|------|--------|")
            for sector in data.top_losers:
                lines.append(f"| {sector.name} | {sector.change_pct:+.2f}% |")
            lines.append("")
        
        if data.timestamp:
            lines.append(f"*数据时间: {data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(lines)
    
    def generate_sector_chart_base64(self, data: USMarketData) -> Optional[str]:
        """
        生成板块涨跌分布图表（Base64编码）
        
        Args:
            data: 美股市场数据
            
        Returns:
            Base64编码的图片字符串，失败返回None
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import io
            import base64
            
            if not data.sectors:
                return None
            
            sectors = sorted(data.sectors, key=lambda x: x.change_pct)
            names = [s.name for s in sectors]
            changes = [s.change_pct for s in sectors]
            
            colors = ['#4CAF50' if c >= 0 else '#F44336' for c in changes]
            
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.barh(names, changes, color=colors)
            
            ax.set_xlabel('涨跌幅 (%)')
            ax.set_title('美股板块涨跌分布')
            ax.axvline(x=0, color='gray', linestyle='-', linewidth=0.5)
            
            for bar, change in zip(bars, changes):
                width = bar.get_width()
                label_x = width + 0.1 if width >= 0 else width - 0.1
                ax.text(label_x, bar.get_y() + bar.get_height()/2,
                       f'{change:+.2f}%', va='center',
                       ha='left' if width >= 0 else 'right')
            
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
            
            return img_base64
            
        except ImportError:
            logger.warning("matplotlib未安装，跳过图表生成")
            return None
        except Exception as e:
            logger.error(f"生成板块图表失败: {e}")
            return None


def get_us_market_service() -> USMarketService:
    """获取美股市场服务实例"""
    return USMarketService()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    service = USMarketService()
    data = service.get_market_summary()
    
    print(service.format_market_report(data))
