# -*- coding: utf-8 -*-
"""
Backtest Engine Module

This module provides backtesting functionality for trading strategies.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
import pandas as pd
import numpy as np

from .base import BaseStrategy, Signal, SignalType
from .performance import PerformanceAnalyzer


logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Order data class"""
    order_id: str
    stock_code: str
    signal_type: SignalType
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0
    price: Optional[float] = None
    filled_price: float = 0.0
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.now)
    fee: float = 0.0
    slippage: float = 0.0
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "order_id": self.order_id,
            "stock_code": self.stock_code,
            "signal_type": self.signal_type.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "filled_price": self.filled_price,
            "filled_quantity": self.filled_quantity,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "fee": self.fee,
            "slippage": self.slippage,
            "reason": self.reason,
        }


@dataclass
class Trade:
    """Trade record"""
    trade_id: str
    stock_code: str
    trade_type: str  # buy, sell
    quantity: int
    price: float
    amount: float
    fee: float
    timestamp: datetime
    signal_reason: str = ""
    pnl: float = 0.0
    pnl_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trade_id": self.trade_id,
            "stock_code": self.stock_code,
            "trade_type": self.trade_type,
            "quantity": self.quantity,
            "price": self.price,
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp.isoformat(),
            "signal_reason": self.signal_reason,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
        }


@dataclass
class Position:
    """Position data class"""
    stock_code: str
    quantity: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    profit_loss: float = 0.0
    profit_loss_pct: float = 0.0
    
    def update_price(self, price: float) -> None:
        """Update current price and calculate P&L"""
        self.current_price = price
        self.market_value = self.quantity * price
        if self.quantity > 0 and self.avg_cost > 0:
            self.profit_loss = (price - self.avg_cost) * self.quantity
            self.profit_loss_pct = (price / self.avg_cost - 1) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stock_code": self.stock_code,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "profit_loss": self.profit_loss,
            "profit_loss_pct": self.profit_loss_pct,
        }


@dataclass
class BacktestConfig:
    """Backtest configuration"""
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003  # 0.03%
    slippage_rate: float = 0.001  # 0.1%
    min_commission: float = 5.0
    position_size_pct: float = 0.1  # 10% per position
    max_positions: int = 10
    allow_short: bool = False
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None


@dataclass
class BacktestResult:
    """Backtest result"""
    stock_code: str
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_return: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stock_code": self.stock_code,
            "strategy_name": self.strategy_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_trade_return": self.avg_trade_return,
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": self.equity_curve,
        }


class BacktestEngine:
    """
    Backtest Engine
    
    Executes trading strategies on historical data and calculates performance.
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        """
        Initialize backtest engine
        
        Args:
            config: Backtest configuration
        """
        self.config = config or BacktestConfig()
        self._cash = self.config.initial_capital
        self._positions: Dict[str, Position] = {}
        self._trades: List[Trade] = []
        self._equity_curve: List[Dict[str, Any]] = []
        self._trade_counter = 0
    
    def run(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        stock_code: str
    ) -> BacktestResult:
        """
        Run backtest
        
        Args:
            strategy: Trading strategy
            data: Historical data
            stock_code: Stock code
            
        Returns:
            BacktestResult
        """
        self._reset()
        
        signals = strategy.generate_signals(data)
        
        signal_dict = {}
        for signal in signals:
            ts = signal.timestamp
            if isinstance(ts, str):
                ts = pd.to_datetime(ts)
            signal_dict[ts] = signal
        
        for i, row in data.iterrows():
            timestamp = row.get("date", i)
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            
            current_price = row["close"]
            
            if stock_code in self._positions:
                self._positions[stock_code].update_price(current_price)
            
            if timestamp in signal_dict:
                signal = signal_dict[timestamp]
                signal.stock_code = stock_code
                self._execute_signal(signal, row)
            
            self._check_stop_loss_take_profit(stock_code, row)
            
            equity = self._calculate_equity(current_price)
            self._equity_curve.append({
                "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
                "equity": equity,
                "cash": self._cash,
                "position_value": equity - self._cash,
            })
        
        return self._create_result(strategy, data, stock_code)
    
    def _reset(self) -> None:
        """Reset backtest state"""
        self._cash = self.config.initial_capital
        self._positions.clear()
        self._trades.clear()
        self._equity_curve.clear()
        self._trade_counter = 0
    
    def _execute_signal(self, signal: Signal, row: pd.Series) -> None:
        """Execute trading signal"""
        stock_code = signal.stock_code
        price = signal.price or row["close"]
        
        if signal.is_buy:
            self._execute_buy(stock_code, price, signal.reason)
        elif signal.is_sell:
            self._execute_sell(stock_code, price, signal.reason)
    
    def _execute_buy(
        self,
        stock_code: str,
        price: float,
        reason: str
    ) -> Optional[Trade]:
        """Execute buy order"""
        position_size = self._cash * self.config.position_size_pct
        
        slippage = price * self.config.slippage_rate
        execution_price = price + slippage
        
        quantity = int(position_size / execution_price)
        if quantity <= 0:
            return None
        
        amount = quantity * execution_price
        fee = max(amount * self.config.commission_rate, self.config.min_commission)
        
        total_cost = amount + fee
        if total_cost > self._cash:
            quantity = int((self._cash - self.config.min_commission) / (execution_price * (1 + self.config.commission_rate)))
            if quantity <= 0:
                return None
            amount = quantity * execution_price
            fee = max(amount * self.config.commission_rate, self.config.min_commission)
            total_cost = amount + fee
        
        self._cash -= total_cost
        
        if stock_code in self._positions:
            pos = self._positions[stock_code]
            total_quantity = pos.quantity + quantity
            total_cost_basis = pos.avg_cost * pos.quantity + execution_price * quantity
            pos.avg_cost = total_cost_basis / total_quantity if total_quantity > 0 else 0
            pos.quantity = total_quantity
        else:
            self._positions[stock_code] = Position(
                stock_code=stock_code,
                quantity=quantity,
                avg_cost=execution_price,
                current_price=execution_price,
            )
        
        self._trade_counter += 1
        trade = Trade(
            trade_id=f"T{self._trade_counter:06d}",
            stock_code=stock_code,
            trade_type="buy",
            quantity=quantity,
            price=execution_price,
            amount=amount,
            fee=fee,
            timestamp=datetime.now(),
            signal_reason=reason,
        )
        self._trades.append(trade)
        
        return trade
    
    def _execute_sell(
        self,
        stock_code: str,
        price: float,
        reason: str
    ) -> Optional[Trade]:
        """Execute sell order"""
        if stock_code not in self._positions:
            return None
        
        position = self._positions[stock_code]
        if position.quantity <= 0:
            return None
        
        quantity = position.quantity
        
        slippage = price * self.config.slippage_rate
        execution_price = price - slippage
        
        amount = quantity * execution_price
        fee = max(amount * self.config.commission_rate, self.config.min_commission)
        
        pnl = (execution_price - position.avg_cost) * quantity - fee
        pnl_pct = (execution_price / position.avg_cost - 1) * 100
        
        self._cash += amount - fee
        
        del self._positions[stock_code]
        
        self._trade_counter += 1
        trade = Trade(
            trade_id=f"T{self._trade_counter:06d}",
            stock_code=stock_code,
            trade_type="sell",
            quantity=quantity,
            price=execution_price,
            amount=amount,
            fee=fee,
            timestamp=datetime.now(),
            signal_reason=reason,
            pnl=pnl,
            pnl_pct=pnl_pct,
        )
        self._trades.append(trade)
        
        return trade
    
    def _check_stop_loss_take_profit(
        self,
        stock_code: str,
        row: pd.Series
    ) -> None:
        """Check stop loss and take profit"""
        if stock_code not in self._positions:
            return
        
        position = self._positions[stock_code]
        current_price = row["close"]
        
        if self.config.stop_loss_pct:
            stop_loss_price = position.avg_cost * (1 - self.config.stop_loss_pct)
            if current_price <= stop_loss_price:
                self._execute_sell(stock_code, current_price, "Stop loss triggered")
                return
        
        if self.config.take_profit_pct:
            take_profit_price = position.avg_cost * (1 + self.config.take_profit_pct)
            if current_price >= take_profit_price:
                self._execute_sell(stock_code, current_price, "Take profit triggered")
    
    def _calculate_equity(self, current_price: float) -> float:
        """Calculate total equity"""
        equity = self._cash
        for pos in self._positions.values():
            equity += pos.quantity * current_price
        return equity
    
    def _create_result(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        stock_code: str
    ) -> BacktestResult:
        """Create backtest result"""
        final_price = data.iloc[-1]["close"]
        final_equity = self._calculate_equity(final_price)
        
        sell_trades = [t for t in self._trades if t.trade_type == "sell"]
        winning_trades = [t for t in sell_trades if t.pnl > 0]
        losing_trades = [t for t in sell_trades if t.pnl <= 0]
        
        total_return = final_equity - self.config.initial_capital
        total_return_pct = (final_equity / self.config.initial_capital - 1) * 100
        
        equity_values = [e["equity"] for e in self._equity_curve]
        max_equity = max(equity_values) if equity_values else final_equity
        min_equity = min(equity_values) if equity_values else final_equity
        max_drawdown = max_equity - min_equity
        max_drawdown_pct = (max_drawdown / max_equity * 100) if max_equity > 0 else 0
        
        returns = []
        for i in range(1, len(equity_values)):
            if equity_values[i - 1] > 0:
                returns.append((equity_values[i] - equity_values[i - 1]) / equity_values[i - 1])
        
        sharpe_ratio = 0.0
        if returns:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return > 0:
                sharpe_ratio = avg_return / std_return * np.sqrt(252)
        
        win_rate = len(winning_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        total_profit = sum(t.pnl for t in winning_trades)
        total_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")
        
        avg_trade_return = np.mean([t.pnl_pct for t in sell_trades]) if sell_trades else 0
        
        start_date = data.iloc[0].get("date", data.index[0])
        end_date = data.iloc[-1].get("date", data.index[-1])
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        
        return BacktestResult(
            stock_code=stock_code,
            strategy_name=strategy.name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.config.initial_capital,
            final_capital=final_equity,
            total_return=total_return,
            total_return_pct=total_return_pct,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(self._trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_trade_return=avg_trade_return,
            trades=self._trades,
            equity_curve=self._equity_curve,
        )
