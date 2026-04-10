# -*- coding: utf-8 -*-
"""
===================================
晨间复盘服务
===================================

职责：
1. 整合美股市场分析
2. 整合A股/港股市场动态（新闻）
3. 整合持仓股票价格区间分析
4. 生成晨间复盘报告
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from src.config import get_config
from src.services.us_market_service import USMarketService, USMarketData
from src.services.price_range_analyzer import (
    PriceRangeAnalyzer, 
    PriceRangeResult,
)

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    summary: str = ""
    source: str = ""
    url: str = ""
    published_time: Optional[datetime] = None
    sector: str = ""
    is_portfolio_related: bool = False


@dataclass
class MorningReviewResult:
    """晨间复盘结果"""
    date: str
    us_market: Optional[USMarketData] = None
    news_items: List[NewsItem] = field(default_factory=list)
    news_by_sector: Dict[str, List[NewsItem]] = field(default_factory=dict)
    price_range_results: Dict[str, Dict[int, PriceRangeResult]] = field(default_factory=dict)
    report_text: str = ""
    timestamp: Optional[datetime] = None


class MorningReviewService:
    """晨间复盘服务"""
    
    def __init__(self):
        self.config = get_config()
        self.us_market_service = USMarketService()
        self.price_range_analyzer = PriceRangeAnalyzer()
        self._search_service = None
        self._portfolio_service = None
        self._data_provider = None
    
    @property
    def search_service(self):
        """延迟加载搜索服务"""
        if self._search_service is None:
            from src.search_service import SearchService
            self._search_service = SearchService()
        return self._search_service
    
    @property
    def portfolio_service(self):
        """延迟加载持仓服务"""
        if self._portfolio_service is None:
            from src.services.portfolio_service import PortfolioService
            self._portfolio_service = PortfolioService()
        return self._portfolio_service
    
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
    
    def get_us_market_analysis(self) -> Optional[USMarketData]:
        """
        获取美股市场分析
        
        Returns:
            美股市场数据
        """
        try:
            return self.us_market_service.get_market_summary()
        except Exception as e:
            logger.error(f"获取美股市场数据失败: {e}")
            return None
    
    def fetch_overnight_news(
        self, 
        hours: int = 12,
        portfolio_codes: Optional[List[str]] = None,
    ) -> List[NewsItem]:
        """
        获取夜间至早间的重要财经新闻
        
        Args:
            hours: 时间范围（小时）
            portfolio_codes: 持仓股票代码列表
            
        Returns:
            新闻列表
        """
        news_items = []
        
        try:
            queries = [
                "A股市场 最新财经新闻",
                "港股市场 最新财经新闻",
                "中国股市 政策消息",
            ]
            
            for query in queries:
                try:
                    results = self.search_service.search_news(
                        query,
                        max_results=5,
                        days=1,
                    )
                    
                    if results:
                        for item in results:
                            news = NewsItem(
                                title=item.get('title', ''),
                                summary=item.get('content', '')[:200] if item.get('content') else '',
                                source=item.get('source', ''),
                                url=item.get('url', ''),
                                published_time=datetime.now(),
                            )
                            news_items.append(news)
                except Exception as e:
                    logger.warning(f"搜索新闻 '{query}' 失败: {e}")
                    continue
            
            news_items = self._deduplicate_news(news_items)
            
            if portfolio_codes:
                news_items = self._mark_portfolio_related(news_items, portfolio_codes)
            
        except Exception as e:
            logger.error(f"获取新闻失败: {e}")
        
        return news_items[:20]
    
    def _deduplicate_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """去重新闻"""
        seen_titles = set()
        unique_items = []
        
        for item in news_items:
            title_key = item.title[:50].lower()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_items.append(item)
        
        return unique_items
    
    def _mark_portfolio_related(
        self, 
        news_items: List[NewsItem], 
        portfolio_codes: List[str],
    ) -> List[NewsItem]:
        """标记持仓相关新闻"""
        for item in news_items:
            title_lower = item.title.lower()
            for code in portfolio_codes:
                if code.lower() in title_lower:
                    item.is_portfolio_related = True
                    break
        
        return news_items
    
    def categorize_news_by_sector(
        self, 
        news_items: List[NewsItem]
    ) -> Dict[str, List[NewsItem]]:
        """
        按板块分类新闻
        
        Args:
            news_items: 新闻列表
            
        Returns:
            {板块: 新闻列表} 字典
        """
        sector_keywords = {
            '科技': ['科技', '互联网', '芯片', '半导体', '人工智能', 'AI', '软件'],
            '金融': ['银行', '保险', '证券', '金融', '央行', '利率'],
            '医药': ['医药', '医疗', '生物', '疫苗', '健康'],
            '消费': ['消费', '零售', '电商', '食品', '饮料'],
            '新能源': ['新能源', '光伏', '风电', '储能', '电池'],
            '房地产': ['房地产', '地产', '住房', '楼市'],
            '军工': ['军工', '国防', '航天'],
        }
        
        categorized = {}
        uncategorized = []
        
        for item in news_items:
            title_lower = item.title.lower()
            matched = False
            
            for sector, keywords in sector_keywords.items():
                if any(kw in title_lower for kw in keywords):
                    if sector not in categorized:
                        categorized[sector] = []
                    item.sector = sector
                    categorized[sector].append(item)
                    matched = True
                    break
            
            if not matched:
                uncategorized.append(item)
        
        if uncategorized:
            categorized['其他'] = uncategorized
        
        return categorized
    
    def get_portfolio_price_ranges(
        self,
        codes: List[str],
        periods: Optional[List[int]] = None,
    ) -> Dict[str, Dict[int, PriceRangeResult]]:
        """
        获取持仓股票价格区间分析
        
        Args:
            codes: 股票代码列表
            periods: 分析周期列表
            
        Returns:
            {股票代码: {周期: 分析结果}} 字典
        """
        if periods is None:
            periods = self.config.price_range_periods
        
        results = {}
        
        for code in codes:
            try:
                multi_period_results = self.price_range_analyzer.analyze_multiple_periods(
                    code, periods
                )
                name = self.get_stock_name(code)
                for period, result in multi_period_results.items():
                    if result:
                        result.name = name
                results[code] = multi_period_results
            except Exception as e:
                logger.error(f"分析股票 {code} 价格区间失败: {e}")
                results[code] = {}
        
        return results
    
    def run_morning_review(
        self,
        portfolio_codes: Optional[List[str]] = None,
    ) -> MorningReviewResult:
        """
        执行晨间复盘
        
        Args:
            portfolio_codes: 持仓股票代码列表（可选，默认从配置获取）
            
        Returns:
            晨间复盘结果
        """
        logger.info("开始执行晨间复盘...")
        
        result = MorningReviewResult(
            date=datetime.now().strftime('%Y-%m-%d'),
            timestamp=datetime.now(),
        )
        
        logger.info("获取美股市场数据...")
        result.us_market = self.get_us_market_analysis()
        
        logger.info("获取财经新闻...")
        result.news_items = self.fetch_overnight_news(
            hours=12,
            portfolio_codes=portfolio_codes,
        )
        result.news_by_sector = self.categorize_news_by_sector(result.news_items)
        
        if portfolio_codes is None:
            portfolio_codes = self.config.stock_list
        
        if portfolio_codes:
            logger.info(f"分析 {len(portfolio_codes)} 只持仓股票价格区间...")
            result.price_range_results = self.get_portfolio_price_ranges(portfolio_codes)
        
        result.report_text = self.generate_report(result)
        
        logger.info("晨间复盘完成")
        return result
    
    def generate_report(self, result: MorningReviewResult) -> str:
        """
        生成晨间复盘报告
        
        Args:
            result: 晨间复盘结果
            
        Returns:
            Markdown格式的报告文本
        """
        lines = []
        
        lines.append(f"# 🌅 晨间复盘报告 - {result.date}")
        lines.append("")
        
        if result.us_market:
            lines.append(self.us_market_service.format_market_report(result.us_market))
            lines.append("")
        
        if result.news_items:
            lines.append("## 📰 A股/港股市场动态")
            lines.append("")
            
            for sector, items in result.news_by_sector.items():
                if items:
                    lines.append(f"### {sector}")
                    lines.append("")
                    for item in items[:5]:
                        marker = "🔴" if item.is_portfolio_related else "•"
                        lines.append(f"- {marker} [{item.title}]({item.url})")
                        if item.summary:
                            lines.append(f"  {item.summary[:100]}...")
                    lines.append("")
        
        if result.price_range_results:
            lines.append("## 💰 持仓股票价格区间分析")
            lines.append("")
            
            for code, period_results in result.price_range_results.items():
                if period_results:
                    name = self.get_stock_name(code)
                    lines.append(
                        self.price_range_analyzer.format_multi_period_report(
                            code, period_results, name
                        )
                    )
                    lines.append("")
        
        if result.timestamp:
            lines.append("---")
            lines.append(f"生成时间: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)


def run_morning_review(
    portfolio_codes: Optional[List[str]] = None,
) -> MorningReviewResult:
    """
    便捷函数：执行晨间复盘
    
    Args:
        portfolio_codes: 持仓股票代码列表
        
    Returns:
        晨间复盘结果
    """
    service = MorningReviewService()
    return service.run_morning_review(portfolio_codes)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    result = run_morning_review(['600519', '300750'])
    print(result.report_text)
