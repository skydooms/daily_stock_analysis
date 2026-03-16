# -*- coding: utf-8 -*-
"""
===================================
EastmoneyFetcher - East Money Direct API
===================================

Data source: East Money (东方财富) direct API
Features: Free, no token required, comprehensive data
API Docs: https://data.eastmoney.com/

Supported markets:
- A-shares (沪深A股)
- Hong Kong stocks (港股)
- US stocks (美股)
- Funds (基金)

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
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .base import BaseFetcher, DataFetchError, RateLimitError, STANDARD_COLUMNS
from .realtime_types import (
    UnifiedRealtimeQuote,
    RealtimeSource,
    get_realtime_circuit_breaker,
    safe_float,
    safe_int,
)


logger = logging.getLogger(__name__)


USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
]


@dataclass
class EastmoneyConfig:
    """East Money API configuration"""
    base_url: str = "https://push2.eastmoney.com/api/qt"
    kline_url: str = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    quote_url: str = "https://push2.eastmoney.com/api/qt/stock/get"
    fund_url: str = "https://fundgz.eastmoney.com"


class EastmoneyFetcher(BaseFetcher):
    """
    East Money (东方财富) data fetcher
    
    Priority: 5 (configurable via EASTMONEY_PRIORITY env)
    
    Supported features:
    - Historical K-line data
    - Real-time quotes
    - Fund data (基金净值)
    - Market statistics
    """
    
    name: str = "EastmoneyFetcher"
    priority: int = 5
    
    def __init__(self):
        """Initialize East Money fetcher"""
        self.config = EastmoneyConfig()
        self._session = requests.Session()
        self._set_headers()
        
    def _set_headers(self):
        """Set request headers with random User-Agent"""
        self._session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://data.eastmoney.com/',
        })
    
    def _get_market_code(self, stock_code: str) -> str:
        """
        Get East Money market code
        
        Args:
            stock_code: Stock code (e.g., '600519', '000001', 'HK00700')
            
        Returns:
            Market code: '1' for Shanghai, '0' for Shenzhen, '116' for HK
        """
        code = stock_code.upper()
        
        if code.startswith('HK') or code.startswith('0'):
            if code.startswith('HK'):
                return '116'  # Hong Kong
            return '0'  # Shenzhen
        
        if code.isdigit():
            if code.startswith(('6', '5', '9')):
                return '1'  # Shanghai
            else:
                return '0'  # Shenzhen
        
        return '1'  # Default to Shanghai
    
    def _format_stock_code(self, stock_code: str) -> str:
        """
        Format stock code for East Money API
        
        Args:
            stock_code: Stock code
            
        Returns:
            Formatted code (e.g., 'sh600519', 'sz000001')
        """
        code = stock_code.upper()
        
        if code.startswith('HK'):
            return code.replace('HK', '') + '.HK'
        
        if code.isdigit():
            if code.startswith(('6', '5', '9')):
                return f'sh{code}'
            else:
                return f'sz{code}'
        
        return code
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
    )
    def _fetch_raw_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Fetch raw K-line data from East Money API
        
        Args:
            stock_code: Stock code
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Raw DataFrame with K-line data
        """
        self.random_sleep(0.5, 1.5)
        self._set_headers()
        
        market = self._get_market_code(stock_code)
        secid = f"{market}.{stock_code}"
        
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': '101',  # Daily K-line
            'fqt': '1',    # Forward adjusted
            'beg': start_date.replace('-', ''),
            'end': end_date.replace('-', ''),
        }
        
        try:
            response = self._session.get(
                self.config.kline_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('rc') != 0 or not data.get('data'):
                raise DataFetchError(f"East Money API error: {data.get('msg', 'Unknown error')}")
            
            klines = data['data'].get('klines', [])
            if not klines:
                raise DataFetchError(f"No data found for {stock_code}")
            
            rows = []
            for kline in klines:
                parts = kline.split(',')
                if len(parts) >= 7:
                    rows.append({
                        'date': parts[0],
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'high': float(parts[3]),
                        'low': float(parts[4]),
                        'volume': int(float(parts[5])),
                        'amount': float(parts[6]),
                        'pct_chg': float(parts[7]) if len(parts) > 7 else 0.0,
                    })
            
            return pd.DataFrame(rows)
            
        except requests.exceptions.RequestException as e:
            if '429' in str(e) or 'rate' in str(e).lower():
                raise RateLimitError(f"East Money rate limit: {e}")
            raise DataFetchError(f"East Money request failed: {e}")
    
    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        Normalize data columns to standard format
        
        Args:
            df: Raw DataFrame
            stock_code: Stock code
            
        Returns:
            Normalized DataFrame
        """
        df = df.copy()
        
        column_mapping = {
            'date': 'date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'amount': 'amount',
            'pct_chg': 'pct_chg',
        }
        
        df = df.rename(columns=column_mapping)
        
        for col in STANDARD_COLUMNS:
            if col not in df.columns:
                df[col] = None
        
        return df[STANDARD_COLUMNS]
    
    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        Get real-time quote from East Money
        
        Args:
            stock_code: Stock code
            
        Returns:
            UnifiedRealtimeQuote object or None
        """
        self.random_sleep(0.3, 1.0)
        self._set_headers()
        
        market = self._get_market_code(stock_code)
        secid = f"{market}.{stock_code}"
        
        params = {
            'secid': secid,
            'fields': 'f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f55,f57,f58,f60,f170,f171',
            'ut': 'fa5fd1943c7b386f1722ccf56a9c8c8f',
        }
        
        try:
            response = self._session.get(
                self.config.quote_url,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('rc') != 0 or not data.get('data'):
                return None
            
            quote_data = data['data']
            
            return UnifiedRealtimeQuote(
                code=stock_code,
                name=quote_data.get('f58', ''),
                price=safe_float(quote_data.get('f43', 0)) / 100,
                change=safe_float(quote_data.get('f50', 0)) / 100,
                change_percent=safe_float(quote_data.get('f170', 0)) / 100,
                open=safe_float(quote_data.get('f46', 0)) / 100,
                high=safe_float(quote_data.get('f44', 0)) / 100,
                low=safe_float(quote_data.get('f45', 0)) / 100,
                prev_close=safe_float(quote_data.get('f60', 0)) / 100,
                volume=safe_int(quote_data.get('f47', 0)),
                amount=safe_float(quote_data.get('f48', 0)),
                turnover_rate=safe_float(quote_data.get('f171', 0)) / 100,
                source=RealtimeSource.EASTMONEY,
            )
            
        except Exception as e:
            logger.warning(f"East Money real-time quote failed for {stock_code}: {e}")
            return None
    
    def get_fund_nav(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        Get fund net asset value (基金净值)
        
        Args:
            fund_code: Fund code (e.g., '000001')
            
        Returns:
            Fund NAV data or None
        """
        self.random_sleep(0.5, 1.5)
        self._set_headers()
        
        url = f"{self.config.fund_url}/fundcode/{fund_code}.js"
        
        try:
            response = self._session.get(url, timeout=10)
            response.raise_for_status()
            
            text = response.text
            if 'fundcode' not in text:
                return None
            
            import json
            json_str = text[text.index('{'):text.rindex('}')+1]
            data = json.loads(json_str)
            
            return {
                'fund_code': data.get('fundcode'),
                'fund_name': data.get('name'),
                'nav': safe_float(data.get('dwjz')),
                'acc_nav': safe_float(data.get('gsz')),
                'nav_date': data.get('jzrq'),
                'update_time': data.get('gztime'),
            }
            
        except Exception as e:
            logger.warning(f"East Money fund NAV failed for {fund_code}: {e}")
            return None
    
    def get_main_indices(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get main market indices
        
        Returns:
            List of index data
        """
        indices = [
            ('sh000001', '上证指数'),
            ('sz399001', '深证成指'),
            ('sz399006', '创业板指'),
        ]
        
        results = []
        for code, name in indices:
            quote = self.get_realtime_quote(code.replace('sh', '').replace('sz', ''))
            if quote:
                results.append({
                    'code': code,
                    'name': name,
                    'current': quote.price,
                    'change': quote.change,
                    'change_pct': quote.change_percent,
                    'volume': quote.volume,
                    'amount': quote.amount,
                })
        
        return results if results else None
