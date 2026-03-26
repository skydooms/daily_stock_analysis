# -*- coding: utf-8 -*-
"""
Portfolio Management Module

Manages:
- Multiple positions
- Cash balance
- Total market value
- Profit/Loss tracking
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import logging

from .position import Position, PositionStatus
from .watchlist import Watchlist, WatchItem, WatchStatus
from .fee_calculator import FeeCalculator, FeeConfig

logger = logging.getLogger(__name__)


@dataclass
class PortfolioStats:
    """Portfolio statistics"""
    total_value: float
    cash: float
    market_value: float
    cost_value: float
    total_profit_loss: float
    total_profit_loss_pct: float
    position_count: int
    watch_count: int
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "total_value": self.total_value,
            "cash": self.cash,
            "market_value": self.market_value,
            "cost_value": self.cost_value,
            "total_profit_loss": self.total_profit_loss,
            "total_profit_loss_pct": self.total_profit_loss_pct,
            "position_count": self.position_count,
            "watch_count": self.watch_count,
            "updated_at": self.updated_at.isoformat(),
        }


class Portfolio:
    """
    Portfolio manager for simulated trading
    
    Features:
    - Manage multiple positions
    - Track cash and market value
    - Calculate profit/loss
    - Support buy/sell operations
    """
    
    def __init__(
        self,
        initial_capital: float = 1000000.0,
        fee_config: Optional[FeeConfig] = None,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.watchlist = Watchlist()
        self.fee_calculator = FeeCalculator(fee_config or FeeConfig())
        
        self._trade_history: List[dict] = []
    
    @property
    def market_value(self) -> float:
        """Total market value of all positions"""
        return sum(p.market_value for p in self.positions.values())
    
    @property
    def cost_value(self) -> float:
        """Total cost value of all positions"""
        return sum(p.cost_value for p in self.positions.values())
    
    @property
    def total_value(self) -> float:
        """Total portfolio value (cash + market value)"""
        return self.cash + self.market_value
    
    @property
    def total_profit_loss(self) -> float:
        """Total profit/loss"""
        return self.total_value - self.initial_capital
    
    @property
    def total_profit_loss_pct(self) -> float:
        """Total profit/loss percentage"""
        if self.initial_capital == 0:
            return 0.0
        return (self.total_profit_loss / self.initial_capital) * 100
    
    def get_stats(self) -> PortfolioStats:
        """Get portfolio statistics"""
        return PortfolioStats(
            total_value=self.total_value,
            cash=self.cash,
            market_value=self.market_value,
            cost_value=self.cost_value,
            total_profit_loss=self.total_profit_loss,
            total_profit_loss_pct=self.total_profit_loss_pct,
            position_count=len(self.positions),
            watch_count=self.watchlist.count(),
        )
    
    def add_to_watchlist(
        self,
        stock_code: str,
        stock_name: str = "",
        **kwargs
    ) -> WatchItem:
        """Add stock to watchlist"""
        item = self.watchlist.add(stock_code, stock_name, **kwargs)
        logger.info(f"Added {stock_code} to watchlist")
        return item
    
    def remove_from_watchlist(self, stock_code: str) -> bool:
        """Remove stock from watchlist"""
        return self.watchlist.remove(stock_code)
    
    def buy(
        self,
        stock_code: str,
        shares: int,
        price: float,
        stock_name: str = "",
        strategy: str = "",
    ) -> Optional[Position]:
        """
        Buy shares of a stock
        
        Args:
            stock_code: Stock code
            shares: Number of shares to buy
            price: Price per share
            stock_name: Stock name
            strategy: Strategy name that triggered this buy
        
        Returns:
            Position if successful, None otherwise
        """
        amount = shares * price
        fee_result = self.fee_calculator.calculate_buy_fee(amount)
        
        total_cost = amount + fee_result.total_fee
        
        if total_cost > self.cash:
            logger.warning(f"Insufficient cash: need {total_cost}, have {self.cash}")
            return None
        
        self.cash -= total_cost
        
        if stock_code in self.positions:
            position = self.positions[stock_code]
            position.add_shares(shares, price)
        else:
            position = Position(
                stock_code=stock_code,
                stock_name=stock_name,
                shares=shares,
                cost_price=price,
                current_price=price,
            )
            self.positions[stock_code] = position
        
        self.watchlist.update_status(stock_code, WatchStatus.POSITION)
        
        trade_record = {
            "stock_code": stock_code,
            "trade_type": "buy",
            "shares": shares,
            "price": price,
            "amount": amount,
            "fee": fee_result.total_fee,
            "total_cost": total_cost,
            "strategy": strategy,
            "timestamp": datetime.now().isoformat(),
        }
        self._trade_history.append(trade_record)
        
        logger.info(f"Bought {shares} shares of {stock_code} at {price:.2f}, fee: {fee_result.total_fee:.2f}")
        
        return position
    
    def sell(
        self,
        stock_code: str,
        shares: int,
        price: float,
        strategy: str = "",
    ) -> Optional[dict]:
        """
        Sell shares of a stock
        
        Args:
            stock_code: Stock code
            shares: Number of shares to sell
            price: Price per share
            strategy: Strategy name that triggered this sell
        
        Returns:
            Trade result if successful, None otherwise
        """
        if stock_code not in self.positions:
            logger.warning(f"No position for {stock_code}")
            return None
        
        position = self.positions[stock_code]
        
        if shares > position.shares:
            shares = position.shares
        
        amount = shares * price
        fee_result = self.fee_calculator.calculate_sell_fee(amount)
        
        net_amount = fee_result.total_amount
        
        realized_pl = position.reduce_shares(shares)
        
        self.cash += net_amount
        
        if position.shares == 0:
            del self.positions[stock_code]
            self.watchlist.update_status(stock_code, WatchStatus.WATCHING)
        
        trade_record = {
            "stock_code": stock_code,
            "trade_type": "sell",
            "shares": shares,
            "price": price,
            "amount": amount,
            "fee": fee_result.total_fee,
            "net_amount": net_amount,
            "realized_pl": realized_pl,
            "strategy": strategy,
            "timestamp": datetime.now().isoformat(),
        }
        self._trade_history.append(trade_record)
        
        logger.info(f"Sold {shares} shares of {stock_code} at {price:.2f}, P/L: {realized_pl:.2f}")
        
        return trade_record
    
    def update_position_price(
        self,
        stock_code: str,
        price: float,
        price_min: float = None,
        price_max: float = None,
        close_min: float = None,
        close_max: float = None,
    ) -> None:
        """Update position price and stats"""
        if stock_code in self.positions:
            self.positions[stock_code].update_price(
                price, price_min, price_max, close_min, close_max
            )
    
    def get_position(self, stock_code: str) -> Optional[Position]:
        """Get position by stock code"""
        return self.positions.get(stock_code)
    
    def get_all_positions(self) -> List[Position]:
        """Get all positions"""
        return list(self.positions.values())
    
    def get_trade_history(self, stock_code: str = None) -> List[dict]:
        """Get trade history"""
        if stock_code:
            return [t for t in self._trade_history if t["stock_code"] == stock_code]
        return self._trade_history
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "market_value": self.market_value,
            "total_value": self.total_value,
            "total_profit_loss": self.total_profit_loss,
            "total_profit_loss_pct": self.total_profit_loss_pct,
            "positions": [p.to_dict() for p in self.positions.values()],
            "watchlist": self.watchlist.to_dict(),
            "trade_count": len(self._trade_history),
        }
