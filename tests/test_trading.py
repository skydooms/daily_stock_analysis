# -*- coding: utf-8 -*-
"""
Test cases for trading module

Tests:
- Fee calculation
- Position management
- Watchlist management
- Portfolio operations
- Buy/Sell strategies
- Backtest engine
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestFeeCalculator:
    """Test fee calculator"""
    
    def test_buy_fee_calculation(self):
        """Test buy fee calculation"""
        from src.trading.fee_calculator import FeeCalculator, FeeConfig
        
        config = FeeConfig(
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            transfer_fee_rate=0.00002,
            min_commission=5.0,
        )
        calculator = FeeCalculator(config)
        
        result = calculator.calculate_buy_fee(100000)
        
        assert result.commission == 30.0
        assert result.stamp_tax == 0.0
        assert result.transfer_fee == 2.0
        assert result.total_fee == 32.0
        assert result.total_amount == 100032.0
    
    def test_sell_fee_calculation(self):
        """Test sell fee calculation"""
        from src.trading.fee_calculator import FeeCalculator, FeeConfig
        
        config = FeeConfig(
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            transfer_fee_rate=0.00002,
            min_commission=5.0,
        )
        calculator = FeeCalculator(config)
        
        result = calculator.calculate_sell_fee(100000)
        
        assert result.commission == 30.0
        assert result.stamp_tax == 100.0
        assert result.transfer_fee == 2.0
        assert result.total_fee == 132.0
        assert result.total_amount == 99868.0
    
    def test_min_commission(self):
        """Test minimum commission"""
        from src.trading.fee_calculator import FeeCalculator, FeeConfig
        
        config = FeeConfig(min_commission=5.0)
        calculator = FeeCalculator(config)
        
        result = calculator.calculate_buy_fee(1000)
        
        assert result.commission == 5.0


class TestPosition:
    """Test position management"""
    
    def test_position_creation(self):
        """Test position creation"""
        from src.trading.position import Position, PositionStatus
        
        position = Position(
            stock_code="600519",
            stock_name="贵州茅台",
            shares=100,
            cost_price=1800.0,
            current_price=1850.0,
        )
        
        assert position.stock_code == "600519"
        assert position.shares == 100
        assert position.market_value == 185000.0
        assert position.profit_loss == 5000.0
        assert position.profit_loss_pct == pytest.approx(2.78, 0.1)
    
    def test_add_shares(self):
        """Test adding shares"""
        from src.trading.position import Position
        
        position = Position(
            stock_code="600519",
            shares=100,
            cost_price=1800.0,
        )
        
        position.add_shares(100, 1900.0)
        
        assert position.shares == 200
        assert position.cost_price == 1850.0
    
    def test_reduce_shares(self):
        """Test reducing shares"""
        from src.trading.position import Position
        
        position = Position(
            stock_code="600519",
            shares=100,
            cost_price=1800.0,
            current_price=1900.0,
        )
        
        realized_pl = position.reduce_shares(50)
        
        assert position.shares == 50
        assert realized_pl == 5000.0


class TestWatchlist:
    """Test watchlist management"""
    
    def test_add_to_watchlist(self):
        """Test adding to watchlist"""
        from src.trading.watchlist import Watchlist, WatchStatus
        
        watchlist = Watchlist()
        item = watchlist.add("600519", "贵州茅台")
        
        assert item.stock_code == "600519"
        assert watchlist.count() == 1
    
    def test_remove_from_watchlist(self):
        """Test removing from watchlist"""
        from src.trading.watchlist import Watchlist
        
        watchlist = Watchlist()
        watchlist.add("600519", "贵州茅台")
        
        result = watchlist.remove("600519")
        
        assert result is True
        assert watchlist.count() == 0
    
    def test_get_by_status(self):
        """Test getting items by status"""
        from src.trading.watchlist import Watchlist, WatchStatus
        
        watchlist = Watchlist()
        watchlist.add("600519", "贵州茅台")
        watchlist.add("000858", "五粮液")
        watchlist.update_status("600519", WatchStatus.POSITION)
        
        items = watchlist.get_by_status(WatchStatus.POSITION)
        
        assert len(items) == 1
        assert items[0].stock_code == "600519"


class TestPortfolio:
    """Test portfolio management"""
    
    def test_portfolio_creation(self):
        """Test portfolio creation"""
        from src.trading.portfolio import Portfolio
        
        portfolio = Portfolio(initial_capital=1000000.0)
        
        assert portfolio.cash == 1000000.0
        assert portfolio.total_value == 1000000.0
        assert len(portfolio.positions) == 0
    
    def test_buy_stock(self):
        """Test buying stock"""
        from src.trading.portfolio import Portfolio
        
        portfolio = Portfolio(initial_capital=1000000.0)
        position = portfolio.buy("600519", 100, 1800.0, "贵州茅台")
        
        assert position is not None
        assert position.shares == 100
        assert portfolio.cash < 1000000.0
    
    def test_sell_stock(self):
        """Test selling stock"""
        from src.trading.portfolio import Portfolio
        
        portfolio = Portfolio(initial_capital=1000000.0)
        portfolio.buy("600519", 100, 1800.0, "贵州茅台")
        
        result = portfolio.sell("600519", 50, 1900.0)
        
        assert result is not None
        assert portfolio.get_position("600519").shares == 50
    
    def test_insufficient_cash(self):
        """Test buying with insufficient cash"""
        from src.trading.portfolio import Portfolio
        
        portfolio = Portfolio(initial_capital=10000.0)
        position = portfolio.buy("600519", 100, 1800.0, "贵州茅台")
        
        assert position is None


class TestPriceTracker:
    """Test price tracker"""
    
    def test_price_tracking(self):
        """Test price tracking"""
        from src.trading.price_tracker import PriceTracker
        
        tracker = PriceTracker(period_days=90)
        
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        data = pd.DataFrame({
            "date": dates,
            "open": np.random.uniform(100, 110, 100),
            "high": np.random.uniform(110, 120, 100),
            "low": np.random.uniform(90, 100, 100),
            "close": np.random.uniform(100, 110, 100),
            "volume": np.random.randint(1000000, 10000000, 100),
        })
        
        stats = tracker.update("600519", data)
        
        assert stats.price_min > 0
        assert stats.price_max > 0
        assert stats.open_min > 0
        assert stats.close_max > 0


class TestVolumePriceAnalyzer:
    """Test volume-price analyzer"""
    
    def test_volume_price_surge_detection(self):
        """Test volume-price surge detection"""
        from src.trading.signals.volume_price import VolumePriceAnalyzer
        
        analyzer = VolumePriceAnalyzer(
            surge_days=3,
            surge_threshold=0.10,
            turnover_multiplier=1.5,
        )
        
        close = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 115, 120, 125])
        volume = np.array([1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 2000, 2500, 3000])
        
        signal = analyzer.detect_volume_price_surge(close, volume)
        
        if signal:
            assert signal.signal_type == "surge"
            assert signal.price_change_pct > 10


class TestBacktestEngine:
    """Test backtest engine"""
    
    def test_backtest_run(self):
        """Test backtest run"""
        from src.trading.backtest.minute_engine import MinuteBacktestEngine, BacktestConfig
        from src.trading.backtest.data_loader import MinuteDataLoader
        
        config = BacktestConfig(initial_capital=1000000.0)
        engine = MinuteBacktestEngine(config)
        
        loader = MinuteDataLoader()
        daily_data = loader.generate_sample_data("600519", days=100)
        
        result = engine.run(
            stock_code="600519",
            daily_data=daily_data,
        )
        
        assert result.stock_code == "600519"
        assert result.initial_capital == 1000000.0
        assert result.final_capital > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
