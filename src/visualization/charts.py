# -*- coding: utf-8 -*-
"""
Chart Generator Module

This module provides chart generation functionality for trading analysis.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
import base64
from io import BytesIO

import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


class ChartType(Enum):
    """Chart type enumeration"""
    LINE = "line"
    CANDLESTICK = "candlestick"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"


@dataclass
class ChartConfig:
    """Chart configuration"""
    title: str = ""
    width: int = 800
    height: int = 400
    show_legend: bool = True
    show_grid: bool = True
    dark_mode: bool = True
    font_family: str = "Arial"
    font_size: int = 12


class ChartGenerator:
    """
    Chart generator for trading visualization
    
    Generates various types of charts for trading analysis.
    Uses matplotlib for rendering.
    """
    
    def __init__(self, config: Optional[ChartConfig] = None):
        """
        Initialize chart generator
        
        Args:
            config: Chart configuration
        """
        self.config = config or ChartConfig()
        self._setup_matplotlib()
    
    def _setup_matplotlib(self) -> None:
        """Setup matplotlib configuration"""
        try:
            import matplotlib
            import matplotlib.pyplot as plt
            
            if self.config.dark_mode:
                plt.style.use("dark_background")
            
            matplotlib.rcParams["font.family"] = self.config.font_family
            matplotlib.rcParams["font.size"] = self.config.font_size
            
        except ImportError:
            logger.warning("matplotlib not installed, chart generation will be limited")
    
    def generate_line_chart(
        self,
        data: pd.DataFrame,
        x_column: str,
        y_columns: List[str],
        title: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Generate line chart
        
        Args:
            data: DataFrame with data
            x_column: X-axis column name
            y_columns: Y-axis column names
            title: Chart title
            labels: Column label mapping
            
        Returns:
            Base64 encoded image string or None
        """
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(self.config.width / 100, self.config.height / 100))
            
            for col in y_columns:
                label = labels.get(col, col) if labels else col
                ax.plot(data[x_column], data[col], label=label)
            
            ax.set_title(title or self.config.title)
            ax.set_xlabel(x_column)
            ax.set_ylabel("Value")
            
            if self.config.show_legend:
                ax.legend()
            
            if self.config.show_grid:
                ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Line chart generation failed: {e}")
            return None
    
    def generate_candlestick_chart(
        self,
        data: pd.DataFrame,
        title: Optional[str] = None,
        show_volume: bool = True,
        show_ma: bool = True,
        ma_periods: List[int] = None
    ) -> Optional[str]:
        """
        Generate candlestick chart
        
        Args:
            data: DataFrame with OHLCV data
            title: Chart title
            show_volume: Whether to show volume
            show_ma: Whether to show moving averages
            ma_periods: MA periods to show
            
        Returns:
            Base64 encoded image string or None
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from matplotlib.patches import Rectangle
            
            if ma_periods is None:
                ma_periods = [5, 10, 20]
            
            if show_volume:
                fig, (ax1, ax2) = plt.subplots(
                    2, 1,
                    figsize=(self.config.width / 100, self.config.height / 100),
                    gridspec_kw={"height_ratios": [3, 1]}
                )
            else:
                fig, ax1 = plt.subplots(figsize=(self.config.width / 100, self.config.height / 100))
                ax2 = None
            
            dates = range(len(data))
            
            for i, (idx, row) in enumerate(data.iterrows()):
                open_price = row["open"]
                close_price = row["close"]
                high_price = row["high"]
                low_price = row["low"]
                
                color = "green" if close_price >= open_price else "red"
                
                ax1.plot([i, i], [low_price, high_price], color=color, linewidth=1)
                
                body_bottom = min(open_price, close_price)
                body_height = abs(close_price - open_price)
                rect = Rectangle((i - 0.3, body_bottom), 0.6, body_height, color=color, alpha=0.8)
                ax1.add_patch(rect)
            
            if show_ma:
                for period in ma_periods:
                    ma = data["close"].rolling(period).mean()
                    ax1.plot(dates, ma, label=f"MA{period}", linewidth=1)
            
            ax1.set_title(title or self.config.title)
            ax1.set_ylabel("Price")
            
            if self.config.show_legend and show_ma:
                ax1.legend()
            
            if self.config.show_grid:
                ax1.grid(True, alpha=0.3)
            
            if show_volume and ax2 is not None:
                colors = ["green" if data.iloc[i]["close"] >= data.iloc[i]["open"] else "red"
                         for i in range(len(data))]
                ax2.bar(dates, data["volume"], color=colors, alpha=0.7)
                ax2.set_ylabel("Volume")
                ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Candlestick chart generation failed: {e}")
            return None
    
    def generate_equity_curve(
        self,
        equity_curve: List[Dict[str, Any]],
        benchmark: Optional[List[float]] = None,
        title: str = "Equity Curve"
    ) -> Optional[str]:
        """
        Generate equity curve chart
        
        Args:
            equity_curve: List of equity values
            benchmark: Optional benchmark values
            title: Chart title
            
        Returns:
            Base64 encoded image string or None
        """
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(self.config.width / 100, self.config.height / 100))
            
            equity_values = [e.get("equity", 0) for e in equity_curve]
            timestamps = range(len(equity_values))
            
            ax.plot(timestamps, equity_values, label="Strategy", linewidth=2)
            
            if benchmark:
                ax.plot(timestamps, benchmark, label="Benchmark", linewidth=1, linestyle="--")
            
            ax.fill_between(timestamps, equity_values, alpha=0.3)
            
            ax.set_title(title)
            ax.set_xlabel("Time")
            ax.set_ylabel("Equity")
            
            if self.config.show_legend:
                ax.legend()
            
            if self.config.show_grid:
                ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Equity curve generation failed: {e}")
            return None
    
    def generate_drawdown_chart(
        self,
        equity_curve: List[Dict[str, Any]],
        title: str = "Drawdown"
    ) -> Optional[str]:
        """
        Generate drawdown chart
        
        Args:
            equity_curve: List of equity values
            title: Chart title
            
        Returns:
            Base64 encoded image string or None
        """
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(self.config.width / 100, self.config.height / 100))
            
            equity_values = [e.get("equity", 0) for e in equity_curve]
            
            peak = equity_values[0]
            drawdowns = []
            
            for eq in equity_values:
                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak * 100 if peak > 0 else 0
                drawdowns.append(dd)
            
            timestamps = range(len(drawdowns))
            
            ax.fill_between(timestamps, drawdowns, 0, color="red", alpha=0.5)
            ax.plot(timestamps, drawdowns, color="red", linewidth=1)
            
            ax.set_title(title)
            ax.set_xlabel("Time")
            ax.set_ylabel("Drawdown %")
            
            if self.config.show_grid:
                ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Drawdown chart generation failed: {e}")
            return None
    
    def generate_pie_chart(
        self,
        data: Dict[str, float],
        title: str = "Portfolio Distribution"
    ) -> Optional[str]:
        """
        Generate pie chart
        
        Args:
            data: Dictionary with labels and values
            title: Chart title
            
        Returns:
            Base64 encoded image string or None
        """
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(self.config.width / 100, self.config.height / 100))
            
            labels = list(data.keys())
            values = list(data.values())
            
            colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
            
            wedges, texts, autotexts = ax.pie(
                values,
                labels=labels,
                autopct="%1.1f%%",
                colors=colors,
                startangle=90
            )
            
            ax.set_title(title)
            
            plt.tight_layout()
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Pie chart generation failed: {e}")
            return None
    
    def generate_returns_distribution(
        self,
        returns: List[float],
        title: str = "Returns Distribution"
    ) -> Optional[str]:
        """
        Generate returns distribution histogram
        
        Args:
            returns: List of returns
            title: Chart title
            
        Returns:
            Base64 encoded image string or None
        """
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(self.config.width / 100, self.config.height / 100))
            
            ax.hist(returns, bins=30, color="steelblue", alpha=0.7, edgecolor="white")
            
            ax.axvline(x=0, color="red", linestyle="--", linewidth=1)
            
            mean_return = np.mean(returns)
            ax.axvline(x=mean_return, color="green", linestyle="-", linewidth=2, label=f"Mean: {mean_return:.2%}")
            
            ax.set_title(title)
            ax.set_xlabel("Return")
            ax.set_ylabel("Frequency")
            
            if self.config.show_legend:
                ax.legend()
            
            if self.config.show_grid:
                ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Returns distribution generation failed: {e}")
            return None
    
    def generate_monthly_returns_heatmap(
        self,
        monthly_returns: pd.DataFrame,
        title: str = "Monthly Returns"
    ) -> Optional[str]:
        """
        Generate monthly returns heatmap
        
        Args:
            monthly_returns: DataFrame with monthly returns
            title: Chart title
            
        Returns:
            Base64 encoded image string or None
        """
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            fig, ax = plt.subplots(figsize=(self.config.width / 100, self.config.height / 100))
            
            sns.heatmap(
                monthly_returns,
                annot=True,
                fmt=".1f",
                cmap="RdYlGn",
                center=0,
                ax=ax
            )
            
            ax.set_title(title)
            
            plt.tight_layout()
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Monthly returns heatmap generation failed: {e}")
            return None
    
    def _fig_to_base64(self, fig) -> str:
        """
        Convert matplotlib figure to base64 string
        
        Args:
            fig: Matplotlib figure
            
        Returns:
            Base64 encoded image string
        """
        import matplotlib.pyplot as plt
        
        buffer = BytesIO()
        fig.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        plt.close(fig)
        
        return img_base64
    
    def generate_trading_chart_with_signals(
        self,
        data: pd.DataFrame,
        signals: List[Any],
        title: str = "Trading Signals"
    ) -> Optional[str]:
        """
        Generate trading chart with buy/sell signals
        
        Args:
            data: DataFrame with OHLCV data
            signals: List of trading signals
            title: Chart title
            
        Returns:
            Base64 encoded image string or None
        """
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(self.config.width / 100, self.config.height / 100))
            
            dates = range(len(data))
            ax.plot(dates, data["close"], label="Close Price", linewidth=1)
            
            buy_signals = [s for s in signals if getattr(s, "signal_type", None) and s.signal_type.value == "buy"]
            sell_signals = [s for s in signals if getattr(s, "signal_type", None) and s.signal_type.value == "sell"]
            
            for signal in buy_signals:
                timestamp = getattr(signal, "timestamp", None)
                if timestamp:
                    if isinstance(timestamp, str):
                        timestamp = pd.to_datetime(timestamp)
                    for i, row in data.iterrows():
                        row_date = row.get("date", i)
                        if isinstance(row_date, str):
                            row_date = pd.to_datetime(row_date)
                        if row_date == timestamp:
                            ax.scatter(i, signal.price, marker="^", color="green", s=100, zorder=5)
                            break
            
            for signal in sell_signals:
                timestamp = getattr(signal, "timestamp", None)
                if timestamp:
                    if isinstance(timestamp, str):
                        timestamp = pd.to_datetime(timestamp)
                    for i, row in data.iterrows():
                        row_date = row.get("date", i)
                        if isinstance(row_date, str):
                            row_date = pd.to_datetime(row_date)
                        if row_date == timestamp:
                            ax.scatter(i, signal.price, marker="v", color="red", s=100, zorder=5)
                            break
            
            ax.set_title(title)
            ax.set_xlabel("Time")
            ax.set_ylabel("Price")
            
            if self.config.show_legend:
                ax.legend()
            
            if self.config.show_grid:
                ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Trading signals chart generation failed: {e}")
            return None
