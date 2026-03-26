#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟交易回测主程序

功能：
1. 读取关注和持仓股票列表
2. 从zip文件加载1分钟和60分钟数据
3. 使用100万模拟资金进行回测
4. 买入信号使用60分钟数据，交易使用1分钟数据
5. 生成日K线图并标注买入点
"""

import os
import zipfile
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_to_joinquant_code(stock_code: str) -> str:
    """
    将普通股票代码转换为聚宽格式
    
    Args:
        stock_code: 普通股票代码，如 '301205'
        
    Returns:
        聚宽格式的股票代码，如 '301205.XSHE'
    """
    code = str(stock_code).strip()
    
    if '.' in code:
        return code
    
    if code.startswith('6'):
        return f'{code}.XSHG'
    elif code.startswith('0') or code.startswith('3'):
        return f'{code}.XSHE'
    else:
        return f'{code}.XSHG'


def load_watchlist_files(watchlist_dir: str) -> List[Dict[str, str]]:
    """
    读取关注和持仓文件
    
    Args:
        watchlist_dir: 关注和持仓文件目录
        
    Returns:
        股票列表，每个元素包含 'code' 和 'name'
    """
    stocks = []
    watchlist_path = Path(watchlist_dir)
    
    if not watchlist_path.exists():
        logger.warning(f"Watchlist directory not found: {watchlist_dir}")
        return stocks
    
    for file_path in watchlist_path.glob('*.txt*'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 1:
                        code = parts[0]
                        name = ' '.join(parts[1:]) if len(parts) > 1 else ''
                        
                        if code.isdigit() and len(code) in (5, 6):
                            stocks.append({
                                'code': code,
                                'name': name,
                                'joinquant_code': convert_to_joinquant_code(code)
                            })
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
    
    return stocks


class ZipDataLoader:
    """从zip文件加载分钟级数据"""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
    
    def load_data_from_zip(
        self,
        zip_file_path: Path,
        stock_code: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        从zip文件加载指定股票的数据
        
        Args:
            zip_file_path: zip文件路径
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame with columns: datetime, open, high, low, close, volume
        """
        if not zip_file_path.exists():
            logger.warning(f"Zip file not found: {zip_file_path}")
            return pd.DataFrame()
        
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zf:
                file_list = zf.namelist()
                
                prefix = 'sh' if stock_code.startswith('6') else 'sz'
                target_file = f"{prefix}{stock_code}.csv"
                
                if target_file not in file_list:
                    logger.debug(f"Stock {stock_code} ({target_file}) not found in {zip_file_path}")
                    return pd.DataFrame()
                
                df_list = []
                try:
                    with zf.open(target_file) as f:
                        df = pd.read_csv(f)
                        df_list.append(df)
                except Exception as e:
                    logger.error(f"Error reading {target_file} from {zip_file_path}: {e}")
                
                if not df_list:
                    return pd.DataFrame()
                
                df = pd.concat(df_list, ignore_index=True)
                
                if '时间' in df.columns:
                    df['datetime'] = pd.to_datetime(df['时间'])
                    df = df.rename(columns={
                        '开盘价': 'open',
                        '收盘价': 'close',
                        '最高价': 'high',
                        '最低价': 'low',
                        '成交量': 'volume'
                    })
                
                if 'datetime' in df.columns:
                    if start_date:
                        df = df[df['datetime'] >= start_date]
                    if end_date:
                        df = df[df['datetime'] <= end_date]
                    df = df.sort_values('datetime').reset_index(drop=True)
                
                return df
                
        except Exception as e:
            logger.error(f"Error loading data from {zip_file_path}: {e}")
            return pd.DataFrame()
    
    def load_minute_data(
        self,
        stock_code: str,
        years: List[int],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """加载1分钟数据（从按月归档）"""
        df_list = []
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()
        
        current_date = start_date
        while current_date <= end_date:
            year_month = current_date.strftime('%Y-%m')
            month_dir = self.data_dir / 'A股_分时数据_沪深' / '1分钟_按月归档' / year_month
            
            if month_dir.exists():
                for zip_file in month_dir.glob('*_1min.zip'):
                    df = self.load_data_from_zip(zip_file, stock_code, start_date, end_date)
                    if not df.empty:
                        df_list.append(df)
            
            if current_date.month == 12:
                current_date = datetime(current_date.year + 1, 1, 1)
            else:
                current_date = datetime(current_date.year, current_date.month + 1, 1)
        
        if df_list:
            return pd.concat(df_list, ignore_index=True).sort_values('datetime').reset_index(drop=True)
        return pd.DataFrame()
    
    def load_60min_data(
        self,
        stock_code: str,
        years: List[int],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """加载60分钟数据（从按月归档）"""
        df_list = []
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()
        
        current_date = start_date
        while current_date <= end_date:
            year_month = current_date.strftime('%Y-%m')
            month_dir = self.data_dir / 'A股_分时数据_沪深' / '60分钟_按月归档' / year_month
            
            if month_dir.exists():
                for zip_file in month_dir.glob('*_60min.zip'):
                    df = self.load_data_from_zip(zip_file, stock_code, start_date, end_date)
                    if not df.empty:
                        df_list.append(df)
            
            if current_date.month == 12:
                current_date = datetime(current_date.year + 1, 1, 1)
            else:
                current_date = datetime(current_date.year, current_date.month + 1, 1)
        
        if df_list:
            return pd.concat(df_list, ignore_index=True).sort_values('datetime').reset_index(drop=True)
        return pd.DataFrame()


def generate_daily_kline_chart(
    minute_data: pd.DataFrame,
    buy_points: List[Dict],
    stock_code: str,
    stock_name: str,
    output_dir: str = 'backtest_charts'
):
    """
    生成日K线图并标注买入点
    
    Args:
        minute_data: 1分钟数据
        buy_points: 买入点列表
        stock_code: 股票代码
        stock_name: 股票名称
        output_dir: 输出目录
    """
    if minute_data.empty:
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    df = minute_data.copy()
    df['date'] = df['datetime'].dt.date
    
    daily_data = df.groupby('date').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).reset_index()
    
    daily_data['date'] = pd.to_datetime(daily_data['date'])
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    up = daily_data[daily_data['close'] >= daily_data['open']]
    down = daily_data[daily_data['close'] < daily_data['open']]
    
    width = 0.6
    
    ax.bar(up['date'], up['close'] - up['open'], width, bottom=up['open'], color='red', label='上涨')
    ax.bar(up['date'], up['high'] - up['close'], 0.1, bottom=up['close'], color='red')
    ax.bar(up['date'], up['low'] - up['open'], 0.1, bottom=up['open'], color='red')
    
    ax.bar(down['date'], down['close'] - down['open'], width, bottom=down['open'], color='green', label='下跌')
    ax.bar(down['date'], down['high'] - down['open'], 0.1, bottom=down['open'], color='green')
    ax.bar(down['date'], down['low'] - down['close'], 0.1, bottom=down['close'], color='green')
    
    for buy_point in buy_points:
        buy_date = pd.to_datetime(buy_point['date'])
        buy_price = buy_point['price']
        shares = buy_point['shares']
        
        ax.scatter(buy_date, buy_price, color='blue', s=100, zorder=5, marker='^')
        ax.annotate(
            f'买入\n{buy_price:.2f}\n{shares}股',
            xy=(buy_date, buy_price),
            xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
        )
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.xticks(rotation=45)
    
    ax.set_title(f'{stock_name} ({stock_code}) 日K线图', fontsize=16)
    ax.set_xlabel('日期', fontsize=12)
    ax.set_ylabel('价格', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, f'{stock_code}_kline.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"K线图已保存: {output_file}")
    plt.close()


class SimpleBacktestEngine:
    """简化的回测引擎"""
    
    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Dict] = {}
        self.trade_records: List[Dict] = []
        self.equity_curve: List[float] = []
    
    def buy(self, stock_code: str, price: float, shares: int, strategy: str = 'simple') -> bool:
        """买入股票"""
        cost = price * shares
        commission = max(cost * 0.0003, 5)
        transfer_fee = shares * 0.00002
        total_cost = cost + commission + transfer_fee
        
        if self.cash < total_cost:
            return False
        
        self.cash -= total_cost
        
        if stock_code in self.positions:
            position = self.positions[stock_code]
            total_shares = position['shares'] + shares
            total_cost = position['cost_price'] * position['shares'] + price * shares
            new_cost_price = total_cost / total_shares
            
            position['shares'] = total_shares
            position['cost_price'] = new_cost_price
        else:
            self.positions[stock_code] = {
                'shares': shares,
                'cost_price': price,
                'entry_date': datetime.now()
            }
        
        self.trade_records.append({
            'type': 'buy',
            'stock_code': stock_code,
            'price': price,
            'shares': shares,
            'strategy': strategy,
            'date': datetime.now().isoformat()
        })
        
        return True
    
    def sell(self, stock_code: str, price: float, shares: int, strategy: str = 'simple') -> bool:
        """卖出股票"""
        if stock_code not in self.positions:
            return False
        
        position = self.positions[stock_code]
        if position['shares'] < shares:
            shares = position['shares']
        
        revenue = price * shares
        commission = max(revenue * 0.0003, 5)
        stamp_tax = revenue * 0.001
        transfer_fee = shares * 0.00002
        net_revenue = revenue - commission - stamp_tax - transfer_fee
        
        self.cash += net_revenue
        
        realized_pl = (price - position['cost_price']) * shares
        
        position['shares'] -= shares
        if position['shares'] == 0:
            del self.positions[stock_code]
        
        self.trade_records.append({
            'type': 'sell',
            'stock_code': stock_code,
            'price': price,
            'shares': shares,
            'strategy': strategy,
            'realized_pl': realized_pl,
            'date': datetime.now().isoformat()
        })
        
        return True
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """计算总市值"""
        total = self.cash
        for stock_code, position in self.positions.items():
            if stock_code in current_prices:
                total += position['shares'] * current_prices[stock_code]
        return total


def run_backtest(
    watchlist_dir: str,
    data_dir: str,
    years: List[int],
    duration_months: int = 3,
    initial_capital: float = 1000000.0
):
    """
    运行回测
    
    Args:
        watchlist_dir: 关注和持仓文件目录
        data_dir: 数据目录
        years: 需要加载的年份
        duration_months: 回测时长（月）
        initial_capital: 初始资金
    """
    logger.info("=" * 60)
    logger.info("开始回测")
    logger.info(f"初始资金: {initial_capital:,.2f} 元")
    logger.info(f"回测时长: {duration_months} 个月")
    logger.info("=" * 60)
    
    stocks = load_watchlist_files(watchlist_dir)
    logger.info(f"加载到 {len(stocks)} 只股票")
    
    if not stocks:
        logger.warning("没有找到股票，退出回测")
        return
    
    data_loader = ZipDataLoader(data_dir)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30 * duration_months)
    
    logger.info(f"回测时间范围: {start_date.date()} 至 {end_date.date()}")
    
    engine = SimpleBacktestEngine(initial_capital=initial_capital)
    
    results = []
    
    for stock in stocks:
        stock_code = stock['code']
        stock_name = stock['name']
        logger.info(f"\n处理股票: {stock_code} {stock_name}")
        
        minute_data = data_loader.load_minute_data(stock_code, years, start_date, end_date)
        if minute_data.empty:
            logger.warning(f"没有找到 {stock_code} 的1分钟数据，跳过")
            continue
        
        logger.info(f"加载到 {len(minute_data)} 条1分钟数据")
        
        data_60min = data_loader.load_60min_data(stock_code, years, start_date, end_date)
        if not data_60min.empty:
            logger.info(f"加载到 {len(data_60min)} 条60分钟数据")
        
        buy_points = []
        
        position_size = min(engine.cash * 0.1, 100000)
        if len(minute_data) > 0:
            first_price = minute_data['close'].iloc[0]
            shares = int(position_size / first_price / 100) * 100
            
            if shares > 0 and engine.buy(stock_code, first_price, shares, 'demo'):
                buy_points.append({
                    'date': minute_data['datetime'].iloc[0],
                    'price': first_price,
                    'shares': shares
                })
                logger.info(f"模拟买入: {stock_code} @ {first_price:.2f} x {shares}股")
        
        if buy_points:
            generate_daily_kline_chart(minute_data, buy_points, stock_code, stock_name)
        
        results.append({
            'stock_code': stock_code,
            'stock_name': stock_name,
            'has_data': not minute_data.empty,
            'data_points': len(minute_data)
        })
    
    logger.info("\n" + "=" * 60)
    logger.info("回测完成")
    logger.info(f"最终资金: {engine.cash:,.2f} 元")
    logger.info(f"交易记录数: {len(engine.trade_records)}")
    logger.info("=" * 60)
    
    for record in engine.trade_records:
        logger.info(f"{record['type'].upper()}: {record['stock_code']} @ {record['price']:.2f} x {record['shares']}股")
    
    return {
        'engine': engine,
        'results': results,
        'trade_records': engine.trade_records
    }


def main():
    """主函数"""
    import sys
    
    watchlist_dir = r'd:\project\data\关注和持仓'
    data_dir = r'd:\project\data\A股分时数据'
    
    if len(sys.argv) > 1 and isinstance(sys.argv[1], list):
        choice = sys.argv[1][0]
    elif len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        print("选择回测模式:")
        print("1. 3个月回测")
        print("2. 1年回测")
        choice = input("请输入选择 (1/2): ").strip()
    
    if choice == '1':
        duration_months = 3
        years = [2025, 2024]
    elif choice == '2':
        duration_months = 12
        years = [2025, 2024, 2023, 2022, 2021]
    else:
        print("无效选择，使用默认3个月回测")
        duration_months = 3
        years = [2025, 2024]
    
    return run_backtest(
        watchlist_dir=watchlist_dir,
        data_dir=data_dir,
        years=years,
        duration_months=duration_months,
        initial_capital=1000000.0
    )


if __name__ == '__main__':
    main()
