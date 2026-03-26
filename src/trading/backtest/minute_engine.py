# -*- coding: utf-8 -*-
"""
Minute-Level Backtest Engine

Features:
- Minute-level data backtesting
- Multiple strategy support
- Fee calculation
- Performance metrics
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import logging

from src.trading.portfolio import Portfolio
from src.trading.position import Position
from src.trading.fee_calculator import FeeCalculator, FeeConfig
from src.trading.price_tracker import PriceTracker
from src.trading.strategies.buy_strategies import (
    BuyStrategyManager,
    VolumePriceBreakout,
    DivergenceBottom,
    DeepPullback,
    BuySignal,
)
from src.trading.strategies.sell_strategies import (
    SellStrategyManager,
    DivergenceTop,
    DailySurge,
    PriceLevelReduce,
    MonthlySurge,
    DivergenceBottomAdd,
    DailyDrop,
    SellSignal,
)

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtest configuration"""
    initial_capital: float = 1000000.0
    commission_rate: float = 0.0003
    stamp_tax_rate: float = 0.001
    transfer_fee_rate: float = 0.00002
    slippage_rate: float = 0.001
    position_size_pct: float = 0.2
    max_position_pct: float = 0.8


@dataclass
class BacktestResult:
    """Backtest result"""
    stock_code: str
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    trade_records: List[dict] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    positions: List[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "stock_code": self.stock_code,
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "trade_records": self.trade_records,
            "equity_curve": self.equity_curve,
            "positions": self.positions,
        }


class MinuteBacktestEngine:
    """
    Minute-level backtest engine
    
    Features:
    - Process minute-level data
    - Support multiple buy/sell strategies
    - Calculate fees and slippage
    - Track performance metrics
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.fee_calculator = FeeCalculator(FeeConfig(
            commission_rate=self.config.commission_rate,
            stamp_tax_rate=self.config.stamp_tax_rate,
            transfer_fee_rate=self.config.transfer_fee_rate,
        ))
        self.price_tracker = PriceTracker()
        
        self.buy_strategy_manager = BuyStrategyManager([
            VolumePriceBreakout(),
            DivergenceBottom(),
            DeepPullback(),
        ])
        
        self.sell_strategy_manager = SellStrategyManager([
            DivergenceTop(),
            DailySurge(),
            PriceLevelReduce(),
            MonthlySurge(),
            DivergenceBottomAdd(),
            DailyDrop(),
        ])
    
    def run(
        self,
        stock_code: str,
        daily_data: pd.DataFrame,
        minute_data: Optional[pd.DataFrame] = None,
        buy_strategy_names: Optional[List[str]] = None,
        sell_strategy_names: Optional[List[str]] = None,
    ) -> BacktestResult:
        """
        Run backtest
        
        Args:
            stock_code: Stock code
            daily_data: Daily OHLCV data
            minute_data: Optional minute-level data (for divergence detection)
            buy_strategy_names: List of buy strategy names to use
            sell_strategy_names: List of sell strategy names to use
        
        Returns:
            BacktestResult
        """
        if daily_data.empty:
            logger.warning(f"No daily data for {stock_code}")
            return self._empty_result(stock_code)
        
        portfolio = Portfolio(
            initial_capital=self.config.initial_capital,
            fee_config=FeeConfig(
                commission_rate=self.config.commission_rate,
                stamp_tax_rate=self.config.stamp_tax_rate,
                transfer_fee_rate=self.config.transfer_fee_rate,
            ),
        )
        
        trade_records = []
        equity_curve = []
        position_records = []
        
        stats = self.price_tracker.update(stock_code, daily_data)
        
        for i in range(max(30, len(daily_data) - 252), len(daily_data)):
            current_date = daily_data.index[i] if isinstance(daily_data.index, pd.DatetimeIndex) else daily_data["date"].iloc[i]
            current_price = float(daily_data["close"].iloc[i])
            
            self.price_tracker.update(stock_code, daily_data.iloc[:i+1])
            
            position = portfolio.get_position(stock_code)
            position_info = position.to_dict() if position else None
            
            buy_signals = self.buy_strategy_manager.check_all(
                stock_code=stock_code,
                data=daily_data.iloc[:i+1],
                minute_data=minute_data,
            )
            
            for signal in buy_signals:
                if buy_strategy_names and signal.strategy_name not in buy_strategy_names:
                    continue
                
                if position_info and position_info.get("shares", 0) > 0:
                    current_position_pct = (position_info["shares"] * current_price) / portfolio.total_value
                    if current_position_pct >= self.config.max_position_pct:
                        continue
                
                shares = int((portfolio.cash * self.config.position_size_pct) / current_price / 100) * 100
                
                if shares > 0:
                    slippage = current_price * self.config.slippage_rate
                    buy_price = current_price + slippage
                    
                    result = portfolio.buy(
                        stock_code=stock_code,
                        shares=shares,
                        price=buy_price,
                        strategy=signal.strategy_name,
                    )
                    
                    if result:
                        trade_records.append({
                            "type": "buy",
                            "date": str(current_date),
                            "stock_code": stock_code,
                            "shares": shares,
                            "price": buy_price,
                            "strategy": signal.strategy_name,
                            "reason": signal.reason,
                            "timestamp": datetime.now().isoformat(),
                        })
            
            if position:
                sell_signals = self.sell_strategy_manager.check_all(
                    stock_code=stock_code,
                    data=daily_data.iloc[:i+1],
                    position=position_info,
                    minute_data=minute_data,
                )
                
                for signal in sell_signals:
                    if sell_strategy_names and signal.strategy_name not in sell_strategy_names:
                        continue
                    
                    if signal.action == "sell" and position.shares > 0:
                        shares_to_sell = int(position.shares * signal.shares_pct / 100) * 100
                        shares_to_sell = min(shares_to_sell, position.shares)
                        
                        if shares_to_sell > 0:
                            slippage = current_price * self.config.slippage_rate
                            sell_price = current_price - slippage
                            
                            result = portfolio.sell(
                                stock_code=stock_code,
                                shares=shares_to_sell,
                                price=sell_price,
                                strategy=signal.strategy_name,
                            )
                            
                            if result:
                                trade_records.append({
                                    "type": "sell",
                                    "date": str(current_date),
                                    "stock_code": stock_code,
                                    "shares": shares_to_sell,
                                    "price": sell_price,
                                    "strategy": signal.strategy_name,
                                    "reason": signal.reason,
                                    "realized_pl": result.get("realized_pl", 0),
                                    "timestamp": datetime.now().isoformat(),
                                })
                    
                    elif signal.action == "buy":
                        shares = int((portfolio.cash * signal.shares_pct) / current_price / 100) * 100
                        
                        if shares > 0:
                            slippage = current_price * self.config.slippage_rate
                            buy_price = current_price + slippage
                            
                            result = portfolio.buy(
                                stock_code=stock_code,
                                shares=shares,
                                price=buy_price,
                                strategy=signal.strategy_name,
                            )
                            
                            if result:
                                trade_records.append({
                                    "type": "buy",
                                    "date": str(current_date),
                                    "stock_code": stock_code,
                                    "shares": shares,
                                    "price": buy_price,
                                    "strategy": signal.strategy_name,
                                    "reason": signal.reason,
                                    "timestamp": datetime.now().isoformat(),
                                })
            
            equity_curve.append(portfolio.total_value)
            
            if position:
                position_records.append({
                    "date": str(current_date),
                    "shares": position.shares,
                    "cost_price": position.cost_price,
                    "current_price": current_price,
                    "market_value": position.market_value,
                    "profit_loss": position.profit_loss,
                    "profit_loss_pct": position.profit_loss_pct,
                })
        
        return self._calculate_result(
            stock_code=stock_code,
            portfolio=portfolio,
            trade_records=trade_records,
            equity_curve=equity_curve,
            position_records=position_records,
        )
    
    def _calculate_result(
        self,
        stock_code: str,
        portfolio: Portfolio,
        trade_records: List[dict],
        equity_curve: List[float],
        position_records: List[dict],
    ) -> BacktestResult:
        """Calculate backtest result"""
        total_return = portfolio.total_value - self.config.initial_capital
        total_return_pct = (total_return / self.config.initial_capital) * 100
        
        equity_array = np.array(equity_curve)
        if len(equity_array) > 1:
            returns = np.diff(equity_array) / equity_array[:-1]
            max_drawdown = np.min(returns)
            max_drawdown_pct = max_drawdown * 100
            
            if np.std(returns) > 0:
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
            else:
                sharpe_ratio = 0.0
        else:
            max_drawdown = 0.0
            max_drawdown_pct = 0.0
            sharpe_ratio = 0.0
        
        winning_trades = sum(1 for t in trade_records if t.get("type") == "sell" and t.get("realized_pl", 0) > 0)
        losing_trades = sum(1 for t in trade_records if t.get("type") == "sell" and t.get("realized_pl", 0) <= 0)
        total_trades = winning_trades + losing_trades
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        return BacktestResult(
            stock_code=stock_code,
            initial_capital=self.config.initial_capital,
            final_capital=portfolio.total_value,
            total_return=total_return,
            total_return_pct=total_return_pct,
            max_drawdown=max_drawdown * portfolio.total_value,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            trade_records=trade_records,
            equity_curve=equity_curve,
            positions=position_records,
        )
    
    def _empty_result(self, stock_code: str) -> BacktestResult:
        """Return empty result"""
        return BacktestResult(
            stock_code=stock_code,
            initial_capital=self.config.initial_capital,
            final_capital=self.config.initial_capital,
            total_return=0.0,
            total_return_pct=0.0,
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            win_rate=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
        )
