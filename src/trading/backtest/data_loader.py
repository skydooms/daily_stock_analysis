# -*- coding: utf-8 -*-
"""
Minute Data Loader

Load minute-level data for backtesting:
- From local CSV files
- From API (akshare)
"""

import os
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class MinuteDataLoader:
    """Load minute-level data for backtesting"""
    
    def __init__(self, data_dir: str = "data/minute"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def load_from_file(
        self,
        stock_code: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load minute data from local CSV file
        
        Args:
            stock_code: Stock code
            start_date: Start date filter
            end_date: End date filter
        
        Returns:
            DataFrame with columns: datetime, open, high, low, close, volume
        """
        file_path = os.path.join(self.data_dir, f"{stock_code}_minute.csv")
        
        if not os.path.exists(file_path):
            logger.warning(f"Minute data file not found: {file_path}")
            return pd.DataFrame()
        
        df = pd.read_csv(file_path)
        
        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
        
        if start_date:
            df = df[df["datetime"] >= start_date]
        if end_date:
            df = df[df["datetime"] <= end_date]
        
        return df
    
    def load_from_akshare(
        self,
        stock_code: str,
        period: str = "1",
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """
        Load minute data from akshare
        
        Args:
            stock_code: Stock code (A-share only)
            period: "1", "5", "15", "30", "60"
            adjust: "qfq" (前复权), "hfq" (后复权), "" (不复权)
        
        Returns:
            DataFrame with minute data
        """
        try:
            import akshare as ak
            
            code = stock_code.split(".")[0]
            
            df = ak.stock_zh_a_hist_min_em(
                symbol=code,
                period=period,
                adjust=adjust,
            )
            
            if df.empty:
                return pd.DataFrame()
            
            df = df.rename(columns={
                "时间": "datetime",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
            })
            
            df["datetime"] = pd.to_datetime(df["datetime"])
            
            return df[["datetime", "open", "high", "low", "close", "volume", "amount"]]
            
        except Exception as e:
            logger.error(f"Failed to load minute data from akshare: {e}")
            return pd.DataFrame()
    
    def resample_to_120min(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Resample minute data to 120-minute bars
        
        Args:
            df: DataFrame with minute data
        
        Returns:
            DataFrame with 120-minute bars
        """
        if df.empty or "datetime" not in df.columns:
            return pd.DataFrame()
        
        df = df.copy()
        df = df.set_index("datetime")
        
        resampled = df.resample("120min").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "amount": "sum",
        }).dropna()
        
        resampled = resampled.reset_index()
        
        return resampled
    
    def save_to_file(self, stock_code: str, df: pd.DataFrame) -> bool:
        """
        Save minute data to local file
        
        Args:
            stock_code: Stock code
            df: DataFrame to save
        
        Returns:
            True if successful
        """
        try:
            file_path = os.path.join(self.data_dir, f"{stock_code}_minute.csv")
            df.to_csv(file_path, index=False)
            logger.info(f"Saved minute data to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save minute data: {e}")
            return False
    
    def generate_sample_data(
        self,
        stock_code: str,
        days: int = 90,
        minutes_per_day: int = 240,
    ) -> pd.DataFrame:
        """
        Generate sample minute data for testing
        
        Args:
            stock_code: Stock code
            days: Number of days
            minutes_per_day: Trading minutes per day (240 = 4 hours)
        
        Returns:
            DataFrame with sample minute data
        """
        np.random.seed(hash(stock_code) % 2**32)
        
        total_minutes = days * minutes_per_day
        
        start_datetime = datetime.now() - timedelta(days=days)
        datetimes = pd.date_range(
            start=start_datetime,
            periods=total_minutes,
            freq="1min",
        )
        
        base_price = 100.0
        trend = np.linspace(0, 20, total_minutes)
        noise = np.random.uniform(-1, 1, total_minutes)
        prices = base_price + trend + noise
        
        df = pd.DataFrame({
            "datetime": datetimes,
            "open": prices - np.random.uniform(0, 0.5, total_minutes),
            "high": prices + np.random.uniform(0.5, 1.5, total_minutes),
            "low": prices - np.random.uniform(0.5, 1.5, total_minutes),
            "close": prices,
            "volume": np.random.randint(10000, 100000, total_minutes),
            "amount": np.random.randint(1000000, 10000000, total_minutes),
        })
        
        return df
