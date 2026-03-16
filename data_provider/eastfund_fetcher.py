# -*- coding: utf-8 -*-
"""
===================================
EastfundFetcher - Tian Tian Fund (天天基金) API
===================================

Data source: Tian Tian Fund (天天基金) API
Features: Free, no token required, comprehensive fund data
Website: https://fund.eastmoney.com/

Supported features:
- Fund NAV (基金净值)
- Fund holdings (基金持仓)
- Fund performance (基金业绩)
- Fund information (基金信息)

Anti-rate-limit strategy:
1. Random sleep between requests
2. User-Agent rotation
3. Exponential backoff retry
"""

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

import pandas as pd
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .base import BaseFetcher, DataFetchError, RateLimitError
from .realtime_types import safe_float, safe_int


logger = logging.getLogger(__name__)


USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


@dataclass
class FundInfo:
    """Fund information data class"""
    fund_code: str
    fund_name: str
    fund_type: str = ""
    manager: str = ""
    company: str = ""
    establish_date: str = ""
    scale: float = 0.0


@dataclass
class FundNAV:
    """Fund net asset value data class"""
    fund_code: str
    fund_name: str
    nav: float = 0.0
    acc_nav: float = 0.0
    nav_date: str = ""
    daily_return: float = 0.0
    subscribe_status: str = ""


@dataclass
class FundHolding:
    """Fund holding data class"""
    stock_code: str
    stock_name: str
    holding_ratio: float = 0.0
    holding_shares: int = 0
    holding_value: float = 0.0


class EastfundFetcher(BaseFetcher):
    """
    Tian Tian Fund (天天基金) data fetcher
    
    Priority: 6 (configurable via EASTFUND_PRIORITY env)
    
    Supported features:
    - Fund NAV query
    - Fund holdings query
    - Fund performance query
    - Fund information query
    """
    
    name: str = "EastfundFetcher"
    priority: int = 6
    
    def __init__(self):
        """Initialize Tian Tian Fund fetcher"""
        self.base_url = "https://fund.eastmoney.com"
        self.api_url = "https://fundgz.eastmoney.com"
        self._session = requests.Session()
        self._set_headers()
        
    def _set_headers(self):
        """Set request headers with random User-Agent"""
        self._session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://fund.eastmoney.com/',
        })
    
    def _fetch_raw_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Fetch raw data (not supported for funds)
        
        Note: Fund data is not time-series like stocks,
        use get_fund_nav_history() instead.
        """
        raise DataFetchError("EastfundFetcher does not support stock K-line data. Use get_fund_nav_history() for fund NAV history.")
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """Normalize data columns"""
        return df
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
    )
    def get_fund_info(self, fund_code: str) -> Optional[FundInfo]:
        """
        Get fund basic information
        
        Args:
            fund_code: Fund code (e.g., '000001')
            
        Returns:
            FundInfo object or None
        """
        self.random_sleep(0.5, 1.5)
        self._set_headers()
        
        url = f"{self.base_url}/fund/{fund_code}.html"
        
        try:
            response = self._session.get(url, timeout=10)
            response.raise_for_status()
            
            text = response.text
            
            import re
            
            fund_name = ""
            name_match = re.search(r'<span class="funCur-FundName">(.*?)</span>', text)
            if name_match:
                fund_name = name_match.group(1).strip()
            
            fund_type = ""
            type_match = re.search(r'基金类型：(.*?)</a>', text)
            if type_match:
                fund_type = type_match.group(1).strip()
            
            manager = ""
            manager_match = re.search(r'基金经理：<a[^>]*>(.*?)</a>', text)
            if manager_match:
                manager = manager_match.group(1).strip()
            
            company = ""
            company_match = re.search(r'基金公司：<a[^>]*>(.*?)</a>', text)
            if company_match:
                company = company_match.group(1).strip()
            
            scale = 0.0
            scale_match = re.search(r'基金规模：.*?(\d+\.?\d*)亿元', text)
            if scale_match:
                scale = safe_float(scale_match.group(1))
            
            return FundInfo(
                fund_code=fund_code,
                fund_name=fund_name,
                fund_type=fund_type,
                manager=manager,
                company=company,
                scale=scale,
            )
            
        except Exception as e:
            logger.warning(f"Tian Tian Fund info failed for {fund_code}: {e}")
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
    )
    def get_fund_nav(self, fund_code: str) -> Optional[FundNAV]:
        """
        Get fund net asset value (实时净值)
        
        Args:
            fund_code: Fund code (e.g., '000001')
            
        Returns:
            FundNAV object or None
        """
        self.random_sleep(0.3, 1.0)
        self._set_headers()
        
        url = f"{self.api_url}/fundcode/{fund_code}.js"
        
        try:
            response = self._session.get(url, timeout=10)
            response.raise_for_status()
            
            text = response.text
            if 'fundcode' not in text:
                return None
            
            import json
            json_str = text[text.index('{'):text.rindex('}')+1]
            data = json.loads(json_str)
            
            return FundNAV(
                fund_code=data.get('fundcode', fund_code),
                fund_name=data.get('name', ''),
                nav=safe_float(data.get('dwjz')),
                acc_nav=safe_float(data.get('gsz')),
                nav_date=data.get('jzrq', ''),
                daily_return=safe_float(data.get('gszzl')),
            )
            
        except Exception as e:
            logger.warning(f"Tian Tian Fund NAV failed for {fund_code}: {e}")
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
    )
    def get_fund_nav_history(
        self,
        fund_code: str,
        start_date: str = None,
        end_date: str = None,
        days: int = 30
    ) -> pd.DataFrame:
        """
        Get fund NAV history (历史净值)
        
        Args:
            fund_code: Fund code
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            days: Number of days to fetch
            
        Returns:
            DataFrame with NAV history
        """
        self.random_sleep(0.5, 1.5)
        self._set_headers()
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        url = f"{self.base_url}/fund/{fund_code}.html"
        
        try:
            response = self._session.get(url, timeout=10)
            response.raise_for_status()
            
            text = response.text
            
            import re
            import json
            
            fund_name = ""
            name_match = re.search(r'<span class="funCur-FundName">(.*?)</span>', text)
            if name_match:
                fund_name = name_match.group(1).strip()
            
            rows = []
            nav_pattern = re.compile(
                r'<td>(\d{4}-\d{2}-\d{2})</td>\s*'
                r'<td class="tor bold">(\d+\.?\d*)</td>\s*'
                r'<td class="tor bold">(\d+\.?\d*)</td>\s*'
                r'<td class="tor .*?>([+-]?\d+\.?\d*%)?</td>',
                re.MULTILINE
            )
            
            for match in nav_pattern.finditer(text):
                date_str = match.group(1)
                nav = safe_float(match.group(2))
                acc_nav = safe_float(match.group(3))
                daily_return_str = match.group(4) or "0%"
                daily_return = safe_float(daily_return_str.replace('%', ''))
                
                if start_date and date_str < start_date:
                    continue
                if date_str > end_date:
                    continue
                
                rows.append({
                    'date': date_str,
                    'nav': nav,
                    'acc_nav': acc_nav,
                    'daily_return': daily_return,
                })
            
            if not rows:
                raise DataFetchError(f"No NAV history found for {fund_code}")
            
            df = pd.DataFrame(rows)
            df = df.sort_values('date', ascending=True).reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.warning(f"Tian Tian Fund NAV history failed for {fund_code}: {e}")
            raise DataFetchError(f"Failed to get NAV history for {fund_code}: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
    )
    def get_fund_holdings(self, fund_code: str) -> Optional[List[FundHolding]]:
        """
        Get fund stock holdings (基金持仓)
        
        Args:
            fund_code: Fund code
            
        Returns:
            List of FundHolding objects
        """
        self.random_sleep(0.5, 1.5)
        self._set_headers()
        
        url = f"{self.base_url}/fund/{fund_code}.html"
        
        try:
            response = self._session.get(url, timeout=10)
            response.raise_for_status()
            
            text = response.text
            
            import re
            
            holdings = []
            holding_pattern = re.compile(
                r'<td>\s*(\d{6})\s*</td>\s*'
                r'<td[^>]*>\s*<a[^>]*>(.*?)</a>\s*</td>\s*'
                r'<td[^>]*>(\d+\.?\d*)%</td>',
                re.MULTILINE
            )
            
            for match in holding_pattern.finditer(text):
                stock_code = match.group(1)
                stock_name = match.group(2).strip()
                holding_ratio = safe_float(match.group(3))
                
                holdings.append(FundHolding(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    holding_ratio=holding_ratio,
                ))
            
            return holdings if holdings else None
            
        except Exception as e:
            logger.warning(f"Tian Tian Fund holdings failed for {fund_code}: {e}")
            return None
    
    def search_funds(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search funds by keyword
        
        Args:
            keyword: Search keyword
            limit: Maximum number of results
            
        Returns:
            List of fund information
        """
        self.random_sleep(0.5, 1.5)
        self._set_headers()
        
        url = "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
        params = {
            'm': '1',
            'key': keyword,
        }
        
        try:
            response = self._session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            text = response.text
            if 'Datas' not in text:
                return []
            
            import json
            data = json.loads(text)
            
            results = []
            for item in data.get('Datas', [])[:limit]:
                results.append({
                    'fund_code': item.get('CODE'),
                    'fund_name': item.get('NAME'),
                    'fund_type': item.get('FundBaseInfo', {}).get('FTYPE'),
                    'fund_pinyin': item.get('JIANPIN'),
                })
            
            return results
            
        except Exception as e:
            logger.warning(f"Tian Tian Fund search failed for '{keyword}': {e}")
            return []
