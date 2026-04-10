# -*- coding: utf-8 -*-
"""
JoinQuant 五分钟级历史数据下载脚本

功能：
- 从 JoinQuant 下载五分钟级历史数据
- 支持指定股票列表、日期范围
- 支持断点续传
- 显示下载进度和剩余流量

使用方法：
    python scripts/download_5min_data.py --stocks 康龙化成 药明康德 --start 2024-12-11 --end 2025-12-18
    python scripts/download_5min_data.py --all  # 下载所有默认股票

注意：
- 试用账号只能获取 2024-12-11 至 2025-12-18 的数据
- 试用账号不支持港股数据，只支持 A 股
- 试用账号每日限额 100 万条
"""

import argparse
import logging
import os
import sys
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
    "康龙化成": "300759.XSHE",
    "药明康德": "603259.XSHG",
}

DEFAULT_OUTPUT_DIR = Path(r"d:\project\data\minute_data")

JQ_ACCOUNT = os.environ.get("JQ_ACCOUNT", "13350387459")
JQ_PASSWORD = os.environ.get("JQ_PASSWORD", "127297Liu")

TRIAL_START_DATE = "2024-12-11"
TRIAL_END_DATE = "2025-12-18"


def check_jqdatasdk_installed() -> bool:
    """Check if jqdatasdk is installed."""
    try:
        import jqdatasdk
        return True
    except ImportError:
        return False


def login_jq() -> bool:
    """Login to JoinQuant."""
    try:
        from jqdatasdk import auth, get_query_count
        
        auth(JQ_ACCOUNT, JQ_PASSWORD)
        
        count = get_query_count()
        logger.info(f"登录成功！剩余流量: {count['spare']:,} / {count['total']:,} 条")
        return True
    except Exception as e:
        logger.error(f"登录失败: {e}")
        return False


def get_remaining_quota() -> int:
    """Get remaining query quota."""
    try:
        from jqdatasdk import get_query_count
        count = get_query_count()
        return count['spare']
    except Exception:
        return 0


def download_5min_data(
    stock_code: str,
    stock_name: str,
    start_date: str,
    end_date: str,
    output_dir: Path,
    batch_months: int = 3,
) -> Tuple[bool, int]:
    """
    Download 5-minute data for a single stock.
    
    Args:
        stock_code: JoinQuant format stock code
        stock_name: Stock name for file naming
        start_date: Start date 'YYYY-MM-DD'
        end_date: End date 'YYYY-MM-DD'
        output_dir: Output directory
        batch_months: Months per batch download
        
    Returns:
        Tuple of (success, rows_downloaded)
    """
    from jqdatasdk import get_price
    
    output_file = output_dir / f"{stock_code.replace('.', '_')}_{stock_name}_5min.csv"
    
    if output_file.exists():
        logger.info(f"文件已存在，跳过: {output_file}")
        df_existing = pd.read_csv(output_file)
        return True, len(df_existing)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    all_data = []
    total_rows = 0
    current_start = start_dt
    
    while current_start < end_dt:
        current_end = min(
            current_start + timedelta(days=batch_months * 30),
            end_dt
        )
        
        remaining = get_remaining_quota()
        if remaining < 10000:
            logger.warning(f"剩余流量不足 ({remaining:,} 条)，暂停下载")
            break
        
        try:
            logger.info(f"下载 {stock_code} ({stock_name}): {current_start.strftime('%Y-%m-%d')} ~ {current_end.strftime('%Y-%m-%d')}")
            
            df = get_price(
                security=stock_code,
                start_date=current_start.strftime("%Y-%m-%d"),
                end_date=current_end.strftime("%Y-%m-%d"),
                frequency="5m",
                fields=["open", "close", "high", "low", "volume", "money"],
            )
            
            if df is not None and not df.empty:
                df = df.reset_index()
                df.columns = ["datetime", "open", "close", "high", "low", "volume", "money"]
                df["stock_code"] = stock_code
                df["stock_name"] = stock_name
                all_data.append(df)
                total_rows += len(df)
                logger.info(f"  获取 {len(df)} 条数据，累计 {total_rows} 条")
            else:
                logger.warning(f"  该时间段无数据")
                
        except Exception as e:
            logger.error(f"  下载失败: {e}")
        
        current_start = current_end + timedelta(days=1)
    
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        final_df = final_df.sort_values("datetime").drop_duplicates(subset=["datetime"])
        final_df.to_csv(output_file, index=False, encoding="utf-8")
        logger.info(f"保存到: {output_file} ({len(final_df)} 条)")
        return True, len(final_df)
    else:
        logger.warning(f"未获取到数据: {stock_code}")
        return False, 0


def main():
    parser = argparse.ArgumentParser(
        description="从 JoinQuant 下载五分钟级历史数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/download_5min_data.py --all
    python scripts/download_5min_data.py --stocks 康龙化成 药明康德
    python scripts/download_5min_data.py --codes 300759.XSHE 603259.XSHG
    python scripts/download_5min_data.py --start 2024-12-11 --end 2025-12-18

注意:
    - 试用账号只能获取 2024-12-11 至 2025-12-18 的数据
    - 试用账号不支持港股数据，只支持 A 股
    - 试用账号每日限额 100 万条
        """,
    )
    
    parser.add_argument(
        "--all", action="store_true",
        help="下载所有默认股票（康龙化成、药明康德）"
    )
    parser.add_argument(
        "--stocks", nargs="+",
        help="指定股票名称列表（如：康龙化成 药明康德）"
    )
    parser.add_argument(
        "--codes", nargs="+",
        help="指定 JoinQuant 股票代码列表（如：300759.XSHE 603259.XSHG）"
    )
    parser.add_argument(
        "--start", default=TRIAL_START_DATE,
        help=f"开始日期 (默认: {TRIAL_START_DATE}, 试用账号限制)"
    )
    parser.add_argument(
        "--end", default=TRIAL_END_DATE,
        help=f"结束日期 (默认: {TRIAL_END_DATE}, 试用账号限制)"
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT_DIR),
        help=f"输出目录 (默认: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--batch-months", type=int, default=3,
        help="每次下载的月数 (默认: 3)"
    )
    
    args = parser.parse_args()
    
    if not check_jqdatasdk_installed():
        logger.error("jqdatasdk 未安装，请运行: pip install jqdatasdk")
        sys.exit(1)
    
    if not login_jq():
        sys.exit(1)
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    stocks_to_download: Dict[str, str] = {}
    
    if args.all:
        stocks_to_download = DEFAULT_STOCKS.copy()
    elif args.stocks:
        for name in args.stocks:
            for key, code in DEFAULT_STOCKS.items():
                if name in key:
                    stocks_to_download[key] = code
                    break
    elif args.codes:
        for code in args.codes:
            stocks_to_download[code] = code
    else:
        logger.info("未指定股票，下载所有默认股票")
        stocks_to_download = DEFAULT_STOCKS.copy()
    
    logger.info(f"准备下载 {len(stocks_to_download)} 只股票的五分钟数据")
    logger.info(f"时间范围: {args.start} ~ {args.end}")
    logger.info(f"输出目录: {output_dir}")
    
    results = []
    for name, code in stocks_to_download.items():
        success, rows = download_5min_data(
            stock_code=code,
            stock_name=name,
            start_date=args.start,
            end_date=args.end,
            output_dir=output_dir,
            batch_months=args.batch_months,
        )
        results.append((name, code, success, rows))
    
    remaining = get_remaining_quota()
    logger.info("=" * 60)
    logger.info("下载完成！结果汇总：")
    for name, code, success, rows in results:
        status = "成功" if success else "失败"
        logger.info(f"  {name} ({code}): {status}, {rows:,} 条")
    logger.info(f"剩余流量: {remaining:,} 条")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
