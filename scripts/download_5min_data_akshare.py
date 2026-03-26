# -*- coding: utf-8 -*-
"""
AKShare 五分钟级历史数据下载脚本

功能：
- 从 AKShare 下载五分钟级历史数据（免费、无需账号）
- 支持 A 股和港股
- 支持断点续传
- 显示下载进度

使用方法：
    python scripts/download_5min_data_akshare.py --stocks 康龙化成 药明康德
    python scripts/download_5min_data_akshare.py --all  # 下载所有默认股票

注意：
- 新浪接口（stock_zh_a_minute）只能获取最近约 2 个月的分钟数据
- 东方财富接口（stock_zh_a_hist_min_em）支持历史数据，但可能有网络限制
- 港股分钟数据接口目前不稳定，建议使用日K数据作为替代
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_STOCKS = {
    "康龙化成_A股": {"code": "300759", "market": "a股", "symbol": "sz300759"},
    "康龙化成_港股": {"code": "03759", "market": "hk", "symbol": "03759"},
    "药明康德_A股": {"code": "603259", "market": "a股", "symbol": "sh603259"},
    "药明康德_港股": {"code": "02359", "market": "hk", "symbol": "02359"},
}

DEFAULT_OUTPUT_DIR = Path(r"d:\project\data\minute_data")


def download_a_stock_5min_sina(
    symbol: str,
    stock_code: str,
    stock_name: str,
    output_dir: Path,
) -> Tuple[bool, int]:
    """
    Download 5-minute data for A-share stock using Sina interface.
    Note: Only returns recent ~2 months of data.
    """
    import akshare as ak
    
    output_file = output_dir / f"{stock_code}_{stock_name}_5min_sina.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info(f"下载 A股 {stock_code} ({stock_name}) - 新浪接口")
        
        df = ak.stock_zh_a_minute(symbol=symbol, period="5", adjust="qfq")
        
        if df is not None and not df.empty:
            df = df.rename(columns={
                "day": "datetime",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "amount": "money",
            })
            df["stock_code"] = stock_code
            df["stock_name"] = stock_name
            df = df[["datetime", "open", "close", "high", "low", "volume", "money", "stock_code", "stock_name"]]
            df.to_csv(output_file, index=False, encoding="utf-8")
            logger.info(f"保存到: {output_file} ({len(df)} 条)")
            logger.info(f"数据时间范围: {df['datetime'].min()} ~ {df['datetime'].max()}")
            return True, len(df)
        else:
            logger.warning(f"未获取到数据: {stock_code}")
            return False, 0
            
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return False, 0


def download_a_stock_5min_em(
    stock_code: str,
    stock_name: str,
    start_date: str,
    end_date: str,
    output_dir: Path,
    max_retries: int = 3,
) -> Tuple[bool, int]:
    """
    Download 5-minute data for A-share stock using EastMoney interface.
    Supports historical data but may have rate limiting issues.
    """
    import akshare as ak
    
    output_file = output_dir / f"{stock_code}_{stock_name}_5min_em.csv"
    
    if output_file.exists():
        logger.info(f"文件已存在，跳过: {output_file}")
        df_existing = pd.read_csv(output_file)
        return True, len(df_existing)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info(f"下载 A股 {stock_code} ({stock_name}): {start_date} ~ {end_date} - 东方财富接口")
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_data = []
        current_start = start_dt
        
        while current_start < end_dt:
            current_end = min(current_start + timedelta(days=90), end_dt)
            
            for retry in range(max_retries):
                try:
                    logger.info(f"  获取 {current_start.strftime('%Y-%m-%d')} ~ {current_end.strftime('%Y-%m-%d')} (尝试 {retry+1}/{max_retries})")
                    
                    df = ak.stock_zh_a_hist_min_em(
                        symbol=stock_code,
                        start_date=f"{current_start.strftime('%Y-%m-%d')} 09:30:00",
                        end_date=f"{current_end.strftime('%Y-%m-%d')} 15:00:00",
                        period="5",
                        adjust="qfq",
                    )
                    break
                except Exception as e:
                    if retry < max_retries - 1:
                        logger.warning(f"    重试中... ({e})")
                        time.sleep(3)
                    else:
                        logger.error(f"    下载失败: {e}")
                        df = None
            
            if df is not None and not df.empty:
                df = df.rename(columns={
                    "时间": "datetime",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "money",
                })
                df["stock_code"] = stock_code
                df["stock_name"] = stock_name
                all_data.append(df)
                logger.info(f"    获取 {len(df)} 条数据")
            else:
                logger.warning(f"    该时间段无数据")
                
            time.sleep(2)
            current_start = current_end + timedelta(days=1)
        
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            final_df = final_df.sort_values("datetime").drop_duplicates(subset=["datetime"])
            final_df = final_df[["datetime", "open", "close", "high", "low", "volume", "money", "stock_code", "stock_name"]]
            final_df.to_csv(output_file, index=False, encoding="utf-8")
            logger.info(f"保存到: {output_file} ({len(final_df)} 条)")
            return True, len(final_df)
        else:
            logger.warning(f"未获取到数据: {stock_code}")
            return False, 0
            
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return False, 0


def download_hk_stock_daily(
    stock_code: str,
    stock_name: str,
    start_date: str,
    end_date: str,
    output_dir: Path,
) -> Tuple[bool, int]:
    """
    Download daily data for HK stock using AKShare.
    Note: HK minute data interface is currently unstable, using daily data as fallback.
    """
    import akshare as ak
    
    output_file = output_dir / f"HK{stock_code}_{stock_name}_daily.csv"
    
    if output_file.exists():
        logger.info(f"文件已存在，跳过: {output_file}")
        df_existing = pd.read_csv(output_file)
        return True, len(df_existing)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info(f"下载 港股 {stock_code} ({stock_name}) 日K数据: {start_date} ~ {end_date}")
        
        df = ak.stock_hk_daily(symbol=stock_code, adjust="qfq")
        
        if df is not None and not df.empty:
            df = df.rename(columns={
                "date": "datetime",
                "open": "open",
                "close": "close",
                "high": "high",
                "low": "low",
                "volume": "volume",
                "amount": "money",
            })
            df["stock_code"] = f"HK{stock_code}"
            df["stock_name"] = stock_name
            df = df[["datetime", "open", "close", "high", "low", "volume", "money", "stock_code", "stock_name"]]
            
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df[(df["datetime"] >= start_dt) & (df["datetime"] <= end_dt)]
            
            df.to_csv(output_file, index=False, encoding="utf-8")
            logger.info(f"保存到: {output_file} ({len(df)} 条)")
            logger.info(f"数据时间范围: {df['datetime'].min()} ~ {df['datetime'].max()}")
            return True, len(df)
        else:
            logger.warning(f"未获取到数据: {stock_code}")
            return False, 0
            
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return False, 0


def download_hk_stock_5min(
    stock_code: str,
    stock_name: str,
    output_dir: Path,
    max_retries: int = 3,
) -> Tuple[bool, int]:
    """
    Download 5-minute data for HK stock using AKShare.
    Note: HK minute data interface may have network issues.
    Falls back to daily data if minute data is unavailable.
    """
    import akshare as ak
    
    output_file = output_dir / f"HK{stock_code}_{stock_name}_5min.csv"
    
    if output_file.exists():
        logger.info(f"文件已存在，跳过: {output_file}")
        df_existing = pd.read_csv(output_file)
        return True, len(df_existing)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for retry in range(max_retries):
        try:
            logger.info(f"下载 港股 {stock_code} ({stock_name}) 分钟数据 - 尝试 {retry+1}/{max_retries}")
            
            df = ak.stock_hk_hist_min_em(
                symbol=stock_code,
                period="5",
                adjust="qfq",
            )
            
            if df is not None and not df.empty:
                df = df.rename(columns={
                    "时间": "datetime",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "money",
                })
                df["stock_code"] = f"HK{stock_code}"
                df["stock_name"] = stock_name
                df = df[["datetime", "open", "close", "high", "low", "volume", "money", "stock_code", "stock_name"]]
                df.to_csv(output_file, index=False, encoding="utf-8")
                logger.info(f"保存到: {output_file} ({len(df)} 条)")
                return True, len(df)
            else:
                logger.warning(f"未获取到数据: {stock_code}")
                break
                
        except Exception as e:
            logger.warning(f"下载失败: {e}")
            if retry < max_retries - 1:
                time.sleep(3)
    
    logger.warning(f"港股 {stock_code} 分钟数据下载失败，尝试下载日K数据...")
    return download_hk_stock_daily(
        stock_code=stock_code,
        stock_name=stock_name,
        start_date="2019-01-01",
        end_date=datetime.now().strftime("%Y-%m-%d"),
        output_dir=output_dir,
    )


def main():
    parser = argparse.ArgumentParser(
        description="从 AKShare 下载五分钟级历史数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/download_5min_data_akshare.py --all
    python scripts/download_5min_data_akshare.py --stocks 康龙化成 药明康德
    python scripts/download_5min_data_akshare.py --source sina  # 使用新浪接口（最近2个月）
    python scripts/download_5min_data_akshare.py --source em --start 2019-01-01 --end 2026-03-21
    python scripts/download_5min_data_akshare.py --hk-daily  # 港股下载日K数据

数据源说明:
    - sina: 新浪接口，只能获取最近约 2 个月的分钟数据，但稳定
    - em: 东方财富接口，支持历史数据，但可能有网络限制
    - 港股分钟数据接口目前不稳定，会自动降级为日K数据
        """,
    )
    
    parser.add_argument(
        "--all", action="store_true",
        help="下载所有默认股票（康龙化成A股/港股、药明康德A股/港股）"
    )
    parser.add_argument(
        "--stocks", nargs="+",
        help="指定股票名称列表（如：康龙化成 药明康德）"
    )
    parser.add_argument(
        "--source", choices=["sina", "em"], default="sina",
        help="数据源: sina(新浪，最近2个月) 或 em(东方财富，历史数据)"
    )
    parser.add_argument(
        "--hk-daily", action="store_true",
        help="港股直接下载日K数据（跳过分钟数据）"
    )
    parser.add_argument(
        "--start", default="2019-01-01",
        help="开始日期 (仅 em 接口有效，默认: 2019-01-01)"
    )
    parser.add_argument(
        "--end", default=datetime.now().strftime("%Y-%m-%d"),
        help="结束日期 (仅 em 接口有效，默认: 今天)"
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT_DIR),
        help=f"输出目录 (默认: {DEFAULT_OUTPUT_DIR})"
    )
    
    args = parser.parse_args()
    
    try:
        import akshare as ak
        logger.info(f"AKShare 版本: {ak.__version__}")
    except ImportError:
        logger.error("akshare 未安装，请运行: pip install akshare")
        sys.exit(1)
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    stocks_to_download: Dict[str, Dict] = {}
    
    if args.all:
        stocks_to_download = DEFAULT_STOCKS.copy()
    elif args.stocks:
        for name in args.stocks:
            for key, info in DEFAULT_STOCKS.items():
                if name in key:
                    stocks_to_download[key] = info
                    break
    else:
        logger.info("未指定股票，下载所有默认股票")
        stocks_to_download = DEFAULT_STOCKS.copy()
    
    logger.info(f"准备下载 {len(stocks_to_download)} 只股票的数据")
    logger.info(f"数据源: {args.source}")
    logger.info(f"输出目录: {output_dir}")
    
    results = []
    for name, info in stocks_to_download.items():
        stock_name = name.split("_")[0]
        stock_code = info["code"]
        market = info["market"]
        symbol = info.get("symbol", stock_code)
        
        if market == "a股":
            if args.source == "sina":
                success, rows = download_a_stock_5min_sina(
                    symbol=symbol,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    output_dir=output_dir,
                )
            else:
                success, rows = download_a_stock_5min_em(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    start_date=args.start,
                    end_date=args.end,
                    output_dir=output_dir,
                )
        elif market == "hk":
            if args.hk_daily:
                success, rows = download_hk_stock_daily(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    start_date=args.start,
                    end_date=args.end,
                    output_dir=output_dir,
                )
            else:
                success, rows = download_hk_stock_5min(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    output_dir=output_dir,
                )
        else:
            logger.warning(f"不支持的市场类型: {market}")
            success, rows = False, 0
        
        results.append((name, stock_code, market, success, rows))
    
    logger.info("=" * 60)
    logger.info("下载完成！结果汇总：")
    for name, code, market, success, rows in results:
        status = "成功" if success else "失败"
        logger.info(f"  {name} ({code}, {market}): {status}, {rows:,} 条")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
