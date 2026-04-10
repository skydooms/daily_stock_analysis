# -*- coding: utf-8 -*-
"""
Trading Database Models

SQLAlchemy models for trading module:
- WatchItem: Watchlist items
- Position: Stock positions
- Trade: Trade records
- PriceStats: Price statistics
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class WatchStatusEnum(str, enum.Enum):
    """Watch item status"""
    WATCHING = "watching"
    POSITION = "position"
    CLOSED = "closed"


class TradeTypeEnum(str, enum.Enum):
    """Trade type"""
    BUY = "buy"
    SELL = "sell"


class WatchItemModel(Base):
    """Watchlist item model"""
    __tablename__ = "trading_watchlist"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), unique=True, nullable=False, index=True)
    stock_name = Column(String(50), default="")
    status = Column(String(20), default=WatchStatusEnum.WATCHING.value)
    
    watch_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss_price = Column(Float, nullable=True)
    
    notes = Column(Text, default="")
    tags = Column(String(255), default="")
    
    added_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "status": self.status,
            "watch_price": self.watch_price,
            "target_price": self.target_price,
            "stop_loss_price": self.stop_loss_price,
            "notes": self.notes,
            "tags": self.tags.split(",") if self.tags else [],
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PositionModel(Base):
    """Position model"""
    __tablename__ = "trading_positions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), unique=True, nullable=False, index=True)
    stock_name = Column(String(50), default="")
    
    shares = Column(Integer, default=0)
    cost_price = Column(Float, default=0.0)
    current_price = Column(Float, default=0.0)
    
    price_min_3m = Column(Float, default=0.0)
    price_max_3m = Column(Float, default=0.0)
    close_min_3m = Column(Float, default=0.0)
    close_max_3m = Column(Float, default=0.0)
    
    status = Column(String(20), default="open")
    
    opened_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "shares": self.shares,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "market_value": self.shares * self.current_price,
            "cost_value": self.shares * self.cost_price,
            "profit_loss": self.shares * (self.current_price - self.cost_price),
            "profit_loss_pct": ((self.current_price - self.cost_price) / self.cost_price * 100) if self.cost_price > 0 else 0,
            "price_min_3m": self.price_min_3m,
            "price_max_3m": self.price_max_3m,
            "close_min_3m": self.close_min_3m,
            "close_max_3m": self.close_max_3m,
            "status": self.status,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TradeModel(Base):
    """Trade record model"""
    __tablename__ = "trading_trades"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(50), default="")
    
    trade_type = Column(String(10), nullable=False)
    shares = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    
    commission = Column(Float, default=0.0)
    stamp_tax = Column(Float, default=0.0)
    transfer_fee = Column(Float, default=0.0)
    total_fee = Column(Float, default=0.0)
    
    net_amount = Column(Float, default=0.0)
    realized_pl = Column(Float, default=0.0)
    
    strategy = Column(String(50), default="")
    reason = Column(Text, default="")
    
    traded_at = Column(DateTime, default=datetime.now, index=True)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "trade_type": self.trade_type,
            "shares": self.shares,
            "price": self.price,
            "amount": self.amount,
            "commission": self.commission,
            "stamp_tax": self.stamp_tax,
            "transfer_fee": self.transfer_fee,
            "total_fee": self.total_fee,
            "net_amount": self.net_amount,
            "realized_pl": self.realized_pl,
            "strategy": self.strategy,
            "reason": self.reason,
            "traded_at": self.traded_at.isoformat() if self.traded_at else None,
        }


class PriceStatsModel(Base):
    """Price statistics model"""
    __tablename__ = "trading_price_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), unique=True, nullable=False, index=True)
    
    price_min = Column(Float, default=0.0)
    price_max = Column(Float, default=0.0)
    open_min = Column(Float, default=0.0)
    close_max = Column(Float, default=0.0)
    
    period_days = Column(Integer, default=90)
    
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "stock_code": self.stock_code,
            "price_min": self.price_min,
            "price_max": self.price_max,
            "open_min": self.open_min,
            "close_max": self.close_max,
            "period_days": self.period_days,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BacktestResultModel(Base):
    """Backtest result model"""
    __tablename__ = "trading_backtest_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, index=True)
    
    initial_capital = Column(Float, default=1000000.0)
    final_capital = Column(Float, default=0.0)
    total_return = Column(Float, default=0.0)
    total_return_pct = Column(Float, default=0.0)
    
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    
    win_rate = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    buy_strategies = Column(String(255), default="")
    sell_strategies = Column(String(255), default="")
    
    trade_records = Column(Text, default="")
    equity_curve = Column(Text, default="")
    
    created_at = Column(DateTime, default=datetime.now)
    
    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
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
            "buy_strategies": self.buy_strategies.split(",") if self.buy_strategies else [],
            "sell_strategies": self.sell_strategies.split(",") if self.sell_strategies else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
