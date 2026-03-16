# -*- coding: utf-8 -*-
"""
Trade Statistics Module

This module provides trade statistics calculation and analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


@dataclass
class TradeStatistics:
    """
    Trade statistics data class
    
    Contains comprehensive trading statistics.
    """
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    break_even_trades: int = 0
    
    total_pnl: float = 0.0
    total_profit: float = 0.0
    total_loss: float = 0.0
    
    win_rate: float = 0.0
    loss_rate: float = 0.0
    
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade: float = 0.0
    
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    profit_factor: float = 0.0
    payoff_ratio: float = 0.0
    
    avg_holding_bars: float = 0.0
    avg_win_holding_bars: float = 0.0
    avg_loss_holding_bars: float = 0.0
    
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trading_days: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "break_even_trades": self.break_even_trades,
            "total_pnl": self.total_pnl,
            "total_profit": self.total_profit,
            "total_loss": self.total_loss,
            "win_rate": self.win_rate,
            "loss_rate": self.loss_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "avg_trade": self.avg_trade,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "profit_factor": self.profit_factor,
            "payoff_ratio": self.payoff_ratio,
            "avg_holding_bars": self.avg_holding_bars,
            "avg_win_holding_bars": self.avg_win_holding_bars,
            "avg_loss_holding_bars": self.avg_loss_holding_bars,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "trading_days": self.trading_days,
        }


class StatisticsCalculator:
    """
    Statistics calculator for trading analysis
    
    Calculates comprehensive trading statistics from trade records.
    """
    
    @staticmethod
    def calculate(
        trades: List[Any],
        equity_curve: Optional[List[float]] = None
    ) -> TradeStatistics:
        """
        Calculate trade statistics
        
        Args:
            trades: List of trade records
            equity_curve: Optional equity curve for additional metrics
            
        Returns:
            TradeStatistics object
        """
        stats = TradeStatistics()
        
        if not trades:
            return stats
        
        closed_trades = [t for t in trades if getattr(t, "trade_type", "") == "sell"]
        
        if not closed_trades:
            stats.total_trades = len(trades)
            return stats
        
        pnls = [getattr(t, "pnl", 0) for t in closed_trades]
        pnl_pcts = [getattr(t, "pnl_pct", 0) for t in closed_trades]
        
        stats.total_trades = len(closed_trades)
        stats.winning_trades = sum(1 for p in pnls if p > 0)
        stats.losing_trades = sum(1 for p in pnls if p < 0)
        stats.break_even_trades = sum(1 for p in pnls if p == 0)
        
        stats.total_pnl = sum(pnls)
        stats.total_profit = sum(p for p in pnls if p > 0)
        stats.total_loss = abs(sum(p for p in pnls if p < 0))
        
        stats.win_rate = stats.winning_trades / stats.total_trades * 100 if stats.total_trades > 0 else 0
        stats.loss_rate = stats.losing_trades / stats.total_trades * 100 if stats.total_trades > 0 else 0
        
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        stats.avg_win = np.mean(wins) if wins else 0
        stats.avg_loss = np.mean(losses) if losses else 0
        stats.avg_trade = np.mean(pnls)
        
        stats.largest_win = max(wins) if wins else 0
        stats.largest_loss = min(losses) if losses else 0
        
        stats.profit_factor = stats.total_profit / stats.total_loss if stats.total_loss > 0 else float("inf")
        stats.payoff_ratio = abs(stats.avg_win / stats.avg_loss) if stats.avg_loss != 0 else 0
        
        max_consec_wins = 0
        max_consec_losses = 0
        current_wins = 0
        current_losses = 0
        
        for pnl in pnls:
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_consec_wins = max(max_consec_wins, current_wins)
            elif pnl < 0:
                current_losses += 1
                current_wins = 0
                max_consec_losses = max(max_consec_losses, current_losses)
        
        stats.max_consecutive_wins = max_consec_wins
        stats.max_consecutive_losses = max_consec_losses
        
        timestamps = []
        for t in closed_trades:
            ts = getattr(t, "timestamp", None)
            if ts:
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                timestamps.append(ts)
        
        if timestamps:
            stats.start_date = min(timestamps)
            stats.end_date = max(timestamps)
            if stats.start_date and stats.end_date:
                stats.trading_days = (stats.end_date - stats.start_date).days + 1
        
        return stats
    
    @staticmethod
    def calculate_monthly_returns(
        trades: List[Any],
        equity_curve: Optional[List[Dict[str, Any]]] = None
    ) -> pd.DataFrame:
        """
        Calculate monthly returns
        
        Args:
            trades: List of trade records
            equity_curve: Equity curve data
            
        Returns:
            DataFrame with monthly returns
        """
        if equity_curve:
            df = pd.DataFrame(equity_curve)
            if "timestamp" in df.columns and "equity" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df["month"] = df["timestamp"].dt.to_period("M")
                
                monthly = df.groupby("month").agg({
                    "equity": ["first", "last"]
                })
                monthly.columns = ["start_equity", "end_equity"]
                monthly["return"] = (monthly["end_equity"] / monthly["start_equity"] - 1) * 100
                
                return monthly
        
        return pd.DataFrame()
    
    @staticmethod
    def calculate_trade_distribution(
        trades: List[Any]
    ) -> Dict[str, Any]:
        """
        Calculate trade distribution statistics
        
        Args:
            trades: List of trade records
            
        Returns:
            Dictionary with distribution statistics
        """
        closed_trades = [t for t in trades if getattr(t, "trade_type", "") == "sell"]
        
        if not closed_trades:
            return {}
        
        pnls = [getattr(t, "pnl", 0) for t in closed_trades]
        pnl_pcts = [getattr(t, "pnl_pct", 0) for t in closed_trades]
        
        return {
            "pnl_mean": np.mean(pnls),
            "pnl_std": np.std(pnls),
            "pnl_median": np.median(pnls),
            "pnl_skew": pd.Series(pnls).skew(),
            "pnl_kurtosis": pd.Series(pnls).kurtosis(),
            "pnl_pct_mean": np.mean(pnl_pcts),
            "pnl_pct_std": np.std(pnl_pcts),
            "percentile_25": np.percentile(pnls, 25),
            "percentile_50": np.percentile(pnls, 50),
            "percentile_75": np.percentile(pnls, 75),
        }
    
    @staticmethod
    def generate_report(
        stats: TradeStatistics,
        title: str = "Trade Statistics Report"
    ) -> str:
        """
        Generate statistics report in Markdown format
        
        Args:
            stats: TradeStatistics object
            title: Report title
            
        Returns:
            Markdown report string
        """
        report = f"""# {title}

## Trade Summary

| Metric | Value |
|--------|-------|
| Total Trades | {stats.total_trades} |
| Winning Trades | {stats.winning_trades} |
| Losing Trades | {stats.losing_trades} |
| Break-even Trades | {stats.break_even_trades} |
| Win Rate | {stats.win_rate:.2f}% |

## Profit & Loss

| Metric | Value |
|--------|-------|
| Total P&L | {stats.total_pnl:,.2f} |
| Total Profit | {stats.total_profit:,.2f} |
| Total Loss | {stats.total_loss:,.2f} |
| Average Win | {stats.avg_win:,.2f} |
| Average Loss | {stats.avg_loss:,.2f} |
| Average Trade | {stats.avg_trade:,.2f} |
| Largest Win | {stats.largest_win:,.2f} |
| Largest Loss | {stats.largest_loss:,.2f} |

## Risk Metrics

| Metric | Value |
|--------|-------|
| Profit Factor | {stats.profit_factor:.2f} |
| Payoff Ratio | {stats.payoff_ratio:.2f} |
| Max Consecutive Wins | {stats.max_consecutive_wins} |
| Max Consecutive Losses | {stats.max_consecutive_losses} |

## Period

| Metric | Value |
|--------|-------|
| Start Date | {stats.start_date.strftime('%Y-%m-%d') if stats.start_date else 'N/A'} |
| End Date | {stats.end_date.strftime('%Y-%m-%d') if stats.end_date else 'N/A'} |
| Trading Days | {stats.trading_days} |
"""
        return report
