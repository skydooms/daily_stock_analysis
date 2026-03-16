# -*- coding: utf-8 -*-
"""
Report Generator Module

This module provides report generation functionality for trading analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import os

from ..strategy.performance import PerformanceMetrics
from ..monitoring.statistics import TradeStatistics


logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Report configuration"""
    title: str = "Trading Analysis Report"
    author: str = "Trading System"
    include_charts: bool = True
    include_trades: bool = True
    include_metrics: bool = True
    output_format: str = "markdown"  # markdown, html, json


class ReportGenerator:
    """
    Report generator for trading analysis
    
    Generates comprehensive reports in various formats.
    """
    
    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize report generator
        
        Args:
            config: Report configuration
        """
        self.config = config or ReportConfig()
    
    def generate_backtest_report(
        self,
        strategy_name: str,
        stock_code: str,
        performance: PerformanceMetrics,
        trades: List[Any],
        equity_curve: List[Dict[str, Any]],
        charts: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate backtest report
        
        Args:
            strategy_name: Strategy name
            stock_code: Stock code
            performance: Performance metrics
            trades: List of trades
            equity_curve: Equity curve data
            charts: Dictionary of chart base64 strings
            
        Returns:
            Report content string
        """
        if self.config.output_format == "markdown":
            return self._generate_markdown_report(
                strategy_name, stock_code, performance, trades, equity_curve, charts
            )
        elif self.config.output_format == "html":
            return self._generate_html_report(
                strategy_name, stock_code, performance, trades, equity_curve, charts
            )
        elif self.config.output_format == "json":
            return self._generate_json_report(
                strategy_name, stock_code, performance, trades, equity_curve
            )
        else:
            return self._generate_markdown_report(
                strategy_name, stock_code, performance, trades, equity_curve, charts
            )
    
    def _generate_markdown_report(
        self,
        strategy_name: str,
        stock_code: str,
        performance: PerformanceMetrics,
        trades: List[Any],
        equity_curve: List[Dict[str, Any]],
        charts: Optional[Dict[str, str]] = None
    ) -> str:
        """Generate Markdown format report"""
        report = f"""# {self.config.title}

## Overview

| Item | Value |
|------|-------|
| Strategy | {strategy_name} |
| Stock | {stock_code} |
| Generated | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| Author | {self.config.author} |

## Performance Summary

### Return Metrics

| Metric | Value |
|--------|-------|
| Total Return | {performance.total_return:,.2f} |
| Total Return % | {performance.total_return_pct:.2f}% |
| Annualized Return | {performance.annualized_return:.2f}% |

### Risk Metrics

| Metric | Value |
|--------|-------|
| Max Drawdown | {performance.max_drawdown:,.2f} |
| Max Drawdown % | {performance.max_drawdown_pct:.2f}% |
| Sharpe Ratio | {performance.sharpe_ratio:.2f} |
| Sortino Ratio | {performance.sortino_ratio:.2f} |
| Calmar Ratio | {performance.calmar_ratio:.2f} |
| Volatility (Annual) | {performance.volatility:.2f}% |

### Trade Statistics

| Metric | Value |
|--------|-------|
| Total Trades | {performance.total_trades} |
| Winning Trades | {performance.winning_trades} |
| Losing Trades | {performance.losing_trades} |
| Win Rate | {performance.win_rate:.2f}% |
| Profit Factor | {performance.profit_factor:.2f} |
| Average Win | {performance.avg_win:,.2f} |
| Average Loss | {performance.avg_loss:,.2f} |
| Max Consecutive Wins | {performance.max_consecutive_wins} |
| Max Consecutive Losses | {performance.max_consecutive_losses} |

## Trade Details

"""
        
        if self.config.include_trades and trades:
            report += "| Trade ID | Type | Quantity | Price | Amount | P&L | Reason |\n"
            report += "|----------|------|----------|-------|--------|-----|--------|\n"
            
            for trade in trades[:50]:  # Limit to 50 trades
                trade_id = getattr(trade, "trade_id", "")
                trade_type = getattr(trade, "trade_type", "")
                quantity = getattr(trade, "quantity", 0)
                price = getattr(trade, "price", 0)
                amount = getattr(trade, "amount", 0)
                pnl = getattr(trade, "pnl", 0)
                reason = getattr(trade, "signal_reason", "")[:30]
                
                report += f"| {trade_id} | {trade_type} | {quantity} | {price:.2f} | {amount:.2f} | {pnl:.2f} | {reason} |\n"
            
            if len(trades) > 50:
                report += f"\n*... and {len(trades) - 50} more trades*\n"
        
        report += """
---

*Report generated by Trading Strategy Backtest System*
"""
        
        return report
    
    def _generate_html_report(
        self,
        strategy_name: str,
        stock_code: str,
        performance: PerformanceMetrics,
        trades: List[Any],
        equity_curve: List[Dict[str, Any]],
        charts: Optional[Dict[str, str]] = None
    ) -> str:
        """Generate HTML format report"""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #007bff;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .positive {{
            color: green;
        }}
        .negative {{
            color: red;
        }}
        .chart-container {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{self.config.title}</h1>
        
        <h2>Overview</h2>
        <table>
            <tr><th>Item</th><th>Value</th></tr>
            <tr><td>Strategy</td><td>{strategy_name}</td></tr>
            <tr><td>Stock</td><td>{stock_code}</td></tr>
            <tr><td>Generated</td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
        </table>
        
        <h2>Performance Summary</h2>
        
        <h3>Return Metrics</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Return</td><td>{performance.total_return:,.2f}</td></tr>
            <tr><td>Total Return %</td><td class="{'positive' if performance.total_return_pct >= 0 else 'negative'}">{performance.total_return_pct:.2f}%</td></tr>
            <tr><td>Annualized Return</td><td>{performance.annualized_return:.2f}%</td></tr>
        </table>
        
        <h3>Risk Metrics</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Max Drawdown</td><td class="negative">{performance.max_drawdown:,.2f}</td></tr>
            <tr><td>Max Drawdown %</td><td class="negative">{performance.max_drawdown_pct:.2f}%</td></tr>
            <tr><td>Sharpe Ratio</td><td>{performance.sharpe_ratio:.2f}</td></tr>
            <tr><td>Sortino Ratio</td><td>{performance.sortino_ratio:.2f}</td></tr>
            <tr><td>Calmar Ratio</td><td>{performance.calmar_ratio:.2f}</td></tr>
        </table>
        
        <h3>Trade Statistics</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Trades</td><td>{performance.total_trades}</td></tr>
            <tr><td>Winning Trades</td><td>{performance.winning_trades}</td></tr>
            <tr><td>Losing Trades</td><td>{performance.losing_trades}</td></tr>
            <tr><td>Win Rate</td><td>{performance.win_rate:.2f}%</td></tr>
            <tr><td>Profit Factor</td><td>{performance.profit_factor:.2f}</td></tr>
        </table>
"""
        
        if charts:
            html += "<h2>Charts</h2>"
            for chart_name, chart_base64 in charts.items():
                html += f"""
        <div class="chart-container">
            <h3>{chart_name}</h3>
            <img src="data:image/png;base64,{chart_base64}" alt="{chart_name}">
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        return html
    
    def _generate_json_report(
        self,
        strategy_name: str,
        stock_code: str,
        performance: PerformanceMetrics,
        trades: List[Any],
        equity_curve: List[Dict[str, Any]]
    ) -> str:
        """Generate JSON format report"""
        report = {
            "meta": {
                "title": self.config.title,
                "strategy": strategy_name,
                "stock_code": stock_code,
                "generated_at": datetime.now().isoformat(),
                "author": self.config.author,
            },
            "performance": performance.to_dict(),
            "trades": [t.to_dict() if hasattr(t, "to_dict") else str(t) for t in trades],
            "equity_curve": equity_curve,
        }
        
        return json.dumps(report, indent=2, ensure_ascii=False)
    
    def save_report(
        self,
        report: str,
        filepath: str
    ) -> bool:
        """
        Save report to file
        
        Args:
            report: Report content
            filepath: Output file path
            
        Returns:
            True if successful
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report)
            
            logger.info(f"Report saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            return False
    
    def generate_comparison_report(
        self,
        results: List[Dict[str, Any]],
        title: str = "Strategy Comparison"
    ) -> str:
        """
        Generate strategy comparison report
        
        Args:
            results: List of backtest results
            title: Report title
            
        Returns:
            Markdown report string
        """
        report = f"""# {title}

## Strategy Comparison

| Strategy | Stock | Total Return | Max DD | Sharpe | Win Rate | Trades |
|----------|-------|--------------|--------|--------|----------|--------|
"""
        
        for result in results:
            strategy = result.get("strategy_name", "Unknown")
            stock = result.get("stock_code", "")
            total_return = result.get("total_return_pct", 0)
            max_dd = result.get("max_drawdown_pct", 0)
            sharpe = result.get("sharpe_ratio", 0)
            win_rate = result.get("win_rate", 0)
            trades = result.get("total_trades", 0)
            
            report += f"| {strategy} | {stock} | {total_return:.2f}% | {max_dd:.2f}% | {sharpe:.2f} | {win_rate:.2f}% | {trades} |\n"
        
        report += """
---

*Report generated by Trading Strategy Backtest System*
"""
        
        return report
