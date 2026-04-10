# -*- coding: utf-8 -*-
"""
Trading API Endpoints

Provides REST API for:
- Watchlist management
- Position management
- Backtest execution
- Portfolio statistics
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import pandas as pd

from src.trading.portfolio import Portfolio, PortfolioStats
from src.trading.position import Position, PositionStatus
from src.trading.watchlist import WatchItem, WatchStatus, Watchlist
from src.trading.backtest.minute_engine import MinuteBacktestEngine, BacktestConfig, BacktestResult
from src.trading.backtest.data_loader import MinuteDataLoader

router = APIRouter(prefix="/trading", tags=["trading"])


# Pydantic models for request/response
class AddWatchRequest(BaseModel):
    """Request to add stock to watchlist"""
    stock_code: str
    stock_name: str = ""
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    notes: str = ""


class BuyRequest(BaseModel):
    """Request to buy shares"""
    stock_code: str
    shares: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    strategy: str = ""


class SellRequest(BaseModel):
    """Request to sell shares"""
    stock_code: str
    shares: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    strategy: str = ""


class BacktestRequest(BaseModel):
    """Request to run backtest"""
    stock_code: str
    initial_capital: float = 1000000.0
    commission_rate: float = 0.0003
    stamp_tax_rate: float = 0.001
    days: int = 252
    buy_strategies: Optional[List[str]] = None
    sell_strategies: Optional[List[str]] = None


# Global portfolio instance
_portfolio: Optional[Portfolio] = None
_data_loader: Optional[MinuteDataLoader] = None


def get_portfolio() -> Portfolio:
    """Get or create portfolio instance"""
    global _portfolio
    if _portfolio is None:
        _portfolio = Portfolio(initial_capital=1000000.0)
    return _portfolio


def get_data_loader() -> MinuteDataLoader:
    """Get or create data loader instance"""
    global _data_loader
    if _data_loader is None:
        _data_loader = MinuteDataLoader()
    return _data_loader


@router.get("/portfolio")
async def get_portfolio_stats():
    """Get portfolio statistics"""
    portfolio = get_portfolio()
    stats = portfolio.get_stats()
    return stats.to_dict()


@router.get("/positions")
async def get_positions():
    """Get all positions"""
    portfolio = get_portfolio()
    positions = portfolio.get_all_positions()
    return {
        "count": len(positions),
        "positions": [p.to_dict() for p in positions]
    }


@router.get("/positions/{stock_code}")
async def get_position(stock_code: str):
    """Get position by stock code"""
    portfolio = get_portfolio()
    position = portfolio.get_position(stock_code)
    if not position:
        raise HTTPException(status_code=404, detail=f"Position not found: {stock_code}")
    return position.to_dict()


@router.post("/positions/buy")
async def buy_position(request: BuyRequest):
    """Buy shares"""
    portfolio = get_portfolio()
    position = portfolio.buy(
        stock_code=request.stock_code,
        shares=request.shares,
        price=request.price,
        strategy=request.strategy,
    )
    if not position:
        raise HTTPException(status_code=400, detail="Failed to buy shares")
    return {
        "success": True,
        "position": position.to_dict()
    }


@router.post("/positions/sell")
async def sell_position(request: SellRequest):
    """Sell shares"""
    portfolio = get_portfolio()
    result = portfolio.sell(
        stock_code=request.stock_code,
        shares=request.shares,
        price=request.price,
        strategy=request.strategy,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Failed to sell shares")
    return {
        "success": True,
        "trade": result
    }


@router.get("/watchlist")
async def get_watchlist():
    """Get watchlist"""
    portfolio = get_portfolio()
    items = portfolio.watchlist.get_all()
    return {
        "count": len(items),
        "items": [item.to_dict() for item in items]
    }


@router.post("/watchlist/add")
async def add_to_watchlist(request: AddWatchRequest):
    """Add stock to watchlist"""
    portfolio = get_portfolio()
    item = portfolio.add_to_watchlist(
        stock_code=request.stock_code,
        stock_name=request.stock_name,
        target_price=request.target_price,
        stop_loss_price=request.stop_loss_price,
        notes=request.notes,
    )
    return {
        "success": True,
        "item": item.to_dict()
    }


@router.delete("/watchlist/{stock_code}")
async def remove_from_watchlist(stock_code: str):
    """Remove stock from watchlist"""
    portfolio = get_portfolio()
    success = portfolio.remove_from_watchlist(stock_code)
    if not success:
        raise HTTPException(status_code=404, detail=f"Stock not in watchlist: {stock_code}")
    return {"success": True}


@router.get("/trades")
async def get_trade_history(stock_code: Optional[str] = None):
    """Get trade history"""
    portfolio = get_portfolio()
    trades = portfolio.get_trade_history(stock_code)
    return {
        "count": len(trades),
        "trades": trades
    }


@router.post("/backtest/run")
async def run_backtest(request: BacktestRequest):
    """Run backtest for a stock"""
    data_loader = get_data_loader()
    
    daily_data = data_loader.generate_sample_data(request.stock_code, days=request.days)
    
    if daily_data.empty:
        raise HTTPException(status_code=400, detail="Failed to load data for backtest")
    
    config = BacktestConfig(
        initial_capital=request.initial_capital,
        commission_rate=request.commission_rate,
        stamp_tax_rate=request.stamp_tax_rate,
    )
    
    engine = MinuteBacktestEngine(config)
    
    result = engine.run(
        stock_code=request.stock_code,
        daily_data=daily_data,
        buy_strategy_names=request.buy_strategies,
        sell_strategy_names=request.sell_strategies,
    )
    
    return result.to_dict()


@router.get("/backtest/strategies")
async def get_available_strategies():
    """Get available strategies"""
    return {
        "buy_strategies": [
            {
                "name": "volume_price_breakout",
                "description": "3-day volume-price surge, price up >10%, turnover >1.5x avg"
            },
            {
                "name": "divergence_bottom",
                "description": "120-minute bottom divergence (MACD)"
            },
            {
                "name": "deep_pullback",
                "description": "Price dropped >35% from 3-month high"
            }
        ],
        "sell_strategies": [
            {
                "name": "divergence_top",
                "description": "120-minute top divergence (reduce 20%)"
            },
            {
                "name": "daily_surge",
                "description": "Single-day surge >10% (reduce 20%)"
            },
            {
                "name": "price_level_reduce",
                "description": "Price > open_min*1.22 or price_min*1.35 (reduce 20%)"
            },
            {
                "name": "monthly_surge",
                "description": "Monthly gain >40% (close position)"
            },
            {
                "name": "divergence_bottom_add",
                "description": "120-minute bottom divergence (add 20%)"
            },
            {
                "name": "daily_drop",
                "description": "Single-day drop >10% (add 20%)"
            }
        ]
    }


@router.post("/portfolio/reset")
async def reset_portfolio(initial_capital: float = 1000000.0):
    """Reset portfolio"""
    global _portfolio
    _portfolio = Portfolio(initial_capital=initial_capital)
    return {
        "success": True,
        "initial_capital": initial_capital
    }
