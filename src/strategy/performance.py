# -*- coding: utf-8 -*-
"""
Performance Analysis Module

This module provides performance analysis for backtesting results.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data class"""
    total_return: float = 0.0
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade_return: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    avg_holding_period: float = 0.0
    volatility: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "annualized_return": self.annualized_return,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "avg_trade_return": self.avg_trade_return,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "avg_holding_period": self.avg_holding_period,
            "volatility": self.volatility,
            "var_95": self.var_95,
            "cvar_95": self.cvar_95,
        }


class PerformanceAnalyzer:
    """
    Performance analyzer for trading strategy backtests
    
    Calculates various performance metrics including:
    - Return metrics
    - Risk metrics
    - Trade statistics
    """
    
    def __init__(self, risk_free_rate: float = 0.03):
        """
        Initialize performance analyzer
        
        Args:
            risk_free_rate: Annual risk-free rate (default 3%)
        """
        self.risk_free_rate = risk_free_rate
    
    def analyze(
        self,
        equity_curve: List[Dict[str, Any]],
        trades: List[Any],
        initial_capital: float
    ) -> PerformanceMetrics:
        """
        Analyze performance from equity curve and trades
        
        Args:
            equity_curve: List of equity values over time
            trades: List of trade records
            initial_capital: Initial capital
            
        Returns:
            PerformanceMetrics object
        """
        if not equity_curve:
            return PerformanceMetrics()
        
        equity_values = [e.get("equity", 0) for e in equity_curve]
        
        metrics = PerformanceMetrics()
        
        metrics.total_return = equity_values[-1] - initial_capital
        metrics.total_return_pct = (equity_values[-1] / initial_capital - 1) * 100
        
        returns = self._calculate_returns(equity_values)
        
        if returns:
            trading_days = len(returns)
            metrics.annualized_return = (
                (1 + metrics.total_return_pct / 100) ** (252 / trading_days) - 1
            ) * 100 if trading_days > 0 else 0
        
        drawdown_info = self._calculate_drawdown(equity_values)
        metrics.max_drawdown = drawdown_info["max_drawdown"]
        metrics.max_drawdown_pct = drawdown_info["max_drawdown_pct"]
        
        if returns:
            metrics.sharpe_ratio = self._calculate_sharpe_ratio(returns)
            metrics.sortino_ratio = self._calculate_sortino_ratio(returns)
            metrics.volatility = np.std(returns) * np.sqrt(252) * 100
            metrics.var_95 = self._calculate_var(returns, 0.95)
            metrics.cvar_95 = self._calculate_cvar(returns, 0.95)
        
        if metrics.max_drawdown_pct > 0:
            metrics.calmar_ratio = metrics.annualized_return / metrics.max_drawdown_pct
        
        if trades:
            trade_metrics = self._analyze_trades(trades)
            metrics.win_rate = trade_metrics["win_rate"]
            metrics.profit_factor = trade_metrics["profit_factor"]
            metrics.avg_win = trade_metrics["avg_win"]
            metrics.avg_loss = trade_metrics["avg_loss"]
            metrics.avg_trade_return = trade_metrics["avg_trade_return"]
            metrics.total_trades = trade_metrics["total_trades"]
            metrics.winning_trades = trade_metrics["winning_trades"]
            metrics.losing_trades = trade_metrics["losing_trades"]
            metrics.max_consecutive_wins = trade_metrics["max_consecutive_wins"]
            metrics.max_consecutive_losses = trade_metrics["max_consecutive_losses"]
            metrics.avg_holding_period = trade_metrics["avg_holding_period"]
        
        return metrics
    
    def _calculate_returns(self, equity_values: List[float]) -> List[float]:
        """Calculate daily returns"""
        if len(equity_values) < 2:
            return []
        
        returns = []
        for i in range(1, len(equity_values)):
            if equity_values[i - 1] > 0:
                ret = (equity_values[i] - equity_values[i - 1]) / equity_values[i - 1]
                returns.append(ret)
        
        return returns
    
    def _calculate_drawdown(
        self,
        equity_values: List[float]
    ) -> Dict[str, float]:
        """Calculate maximum drawdown"""
        if not equity_values:
            return {"max_drawdown": 0, "max_drawdown_pct": 0}
        
        peak = equity_values[0]
        max_dd = 0
        max_dd_pct = 0
        
        for value in equity_values:
            if value > peak:
                peak = value
            
            dd = peak - value
            dd_pct = (dd / peak * 100) if peak > 0 else 0
            
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
        
        return {
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd_pct,
        }
    
    def _calculate_sharpe_ratio(
        self,
        returns: List[float],
        periods_per_year: int = 252
    ) -> float:
        """Calculate Sharpe ratio"""
        if not returns:
            return 0.0
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        daily_rf = self.risk_free_rate / periods_per_year
        excess_return = avg_return - daily_rf
        
        return excess_return / std_return * np.sqrt(periods_per_year)
    
    def _calculate_sortino_ratio(
        self,
        returns: List[float],
        periods_per_year: int = 252
    ) -> float:
        """Calculate Sortino ratio"""
        if not returns:
            return 0.0
        
        avg_return = np.mean(returns)
        
        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return float("inf")
        
        downside_std = np.std(negative_returns)
        
        if downside_std == 0:
            return 0.0
        
        daily_rf = self.risk_free_rate / periods_per_year
        excess_return = avg_return - daily_rf
        
        return excess_return / downside_std * np.sqrt(periods_per_year)
    
    def _calculate_var(
        self,
        returns: List[float],
        confidence: float = 0.95
    ) -> float:
        """Calculate Value at Risk"""
        if not returns:
            return 0.0
        
        return np.percentile(returns, (1 - confidence) * 100)
    
    def _calculate_cvar(
        self,
        returns: List[float],
        confidence: float = 0.95
    ) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        if not returns:
            return 0.0
        
        var = self._calculate_var(returns, confidence)
        tail_returns = [r for r in returns if r <= var]
        
        return np.mean(tail_returns) if tail_returns else var
    
    def _analyze_trades(self, trades: List[Any]) -> Dict[str, Any]:
        """Analyze trade statistics"""
        if not trades:
            return {
                "win_rate": 0,
                "profit_factor": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "avg_trade_return": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "avg_holding_period": 0,
            }
        
        sell_trades = [t for t in trades if getattr(t, "trade_type", "") == "sell"]
        
        if not sell_trades:
            return {
                "win_rate": 0,
                "profit_factor": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "avg_trade_return": 0,
                "total_trades": len(trades),
                "winning_trades": 0,
                "losing_trades": 0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "avg_holding_period": 0,
            }
        
        pnls = [getattr(t, "pnl", 0) for t in sell_trades]
        pnl_pcts = [getattr(t, "pnl_pct", 0) for t in sell_trades]
        
        winning = [p for p in pnls if p > 0]
        losing = [p for p in pnls if p <= 0]
        
        total_profit = sum(winning)
        total_loss = abs(sum(losing))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")
        
        max_consec_wins = 0
        max_consec_losses = 0
        current_wins = 0
        current_losses = 0
        
        for pnl in pnls:
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_consec_wins = max(max_consec_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consec_losses = max(max_consec_losses, current_losses)
        
        return {
            "win_rate": len(winning) / len(sell_trades) * 100 if sell_trades else 0,
            "profit_factor": profit_factor,
            "avg_win": np.mean(winning) if winning else 0,
            "avg_loss": np.mean(losing) if losing else 0,
            "avg_trade_return": np.mean(pnl_pcts) if pnl_pcts else 0,
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "max_consecutive_wins": max_consec_wins,
            "max_consecutive_losses": max_consec_losses,
            "avg_holding_period": 0,
        }
    
    def generate_report(
        self,
        metrics: PerformanceMetrics,
        strategy_name: str = ""
    ) -> str:
        """
        Generate performance report in Markdown format
        
        Args:
            metrics: Performance metrics
            strategy_name: Strategy name
            
        Returns:
            Markdown report string
        """
        report = f"""# Backtest Performance Report

## Strategy: {strategy_name or "Unknown"}

### Return Metrics

| Metric | Value |
|--------|-------|
| Total Return | {metrics.total_return:,.2f} |
| Total Return % | {metrics.total_return_pct:.2f}% |
| Annualized Return | {metrics.annualized_return:.2f}% |
| Max Drawdown | {metrics.max_drawdown:,.2f} |
| Max Drawdown % | {metrics.max_drawdown_pct:.2f}% |

### Risk Metrics

| Metric | Value |
|--------|-------|
| Sharpe Ratio | {metrics.sharpe_ratio:.2f} |
| Sortino Ratio | {metrics.sortino_ratio:.2f} |
| Calmar Ratio | {metrics.calmar_ratio:.2f} |
| Volatility (Annual) | {metrics.volatility:.2f}% |
| VaR (95%) | {metrics.var_95:.4f} |
| CVaR (95%) | {metrics.cvar_95:.4f} |

### Trade Statistics

| Metric | Value |
|--------|-------|
| Total Trades | {metrics.total_trades} |
| Winning Trades | {metrics.winning_trades} |
| Losing Trades | {metrics.losing_trades} |
| Win Rate | {metrics.win_rate:.2f}% |
| Profit Factor | {metrics.profit_factor:.2f} |
| Average Win | {metrics.avg_win:,.2f} |
| Average Loss | {metrics.avg_loss:,.2f} |
| Avg Trade Return | {metrics.avg_trade_return:.2f}% |
| Max Consecutive Wins | {metrics.max_consecutive_wins} |
| Max Consecutive Losses | {metrics.max_consecutive_losses} |
"""
        return report
