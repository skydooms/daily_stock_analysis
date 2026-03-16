# -*- coding: utf-8 -*-
"""
Test Cases for Trading Strategy Backtest System

This module provides comprehensive test cases for:
- Time slice functionality
- Technical indicators
- Trading strategies
- Backtest engine
- Performance analysis
- Message push
- Visualization
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTimeSlice(unittest.TestCase):
    """Test cases for time slice functionality"""
    
    def setUp(self):
        """Set up test data"""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        self.test_data = pd.DataFrame({
            "date": dates,
            "open": np.random.uniform(100, 110, 100),
            "high": np.random.uniform(110, 120, 100),
            "low": np.random.uniform(90, 100, 100),
            "close": np.random.uniform(100, 110, 100),
            "volume": np.random.randint(1000000, 10000000, 100),
        })
    
    def test_time_frame_enum(self):
        """Test TimeFrame enum"""
        from src.strategy.time_slice import TimeFrame
        
        self.assertEqual(TimeFrame.DAY_1.value, "1d")
        self.assertEqual(TimeFrame.HOUR_1.value, "1h")
        self.assertEqual(TimeFrame.MIN_5.value, "5m")
        
        tf = TimeFrame.from_string("daily")
        self.assertEqual(tf, TimeFrame.DAY_1)
        
        self.assertTrue(TimeFrame.MIN_5.is_intraday)
        self.assertFalse(TimeFrame.DAY_1.is_intraday)
    
    def test_time_slice_generation(self):
        """Test time slice generation"""
        from src.strategy.time_slice import TimeSliceGenerator, TimeFrame
        
        generator = TimeSliceGenerator()
        slices = generator.generate(self.test_data, "TEST", TimeFrame.DAY_1)
        
        self.assertGreater(len(slices), 0)
        self.assertEqual(slices[0].stock_code, "TEST")
        self.assertEqual(slices[0].timeframe, TimeFrame.DAY_1)
    
    def test_time_slice_properties(self):
        """Test time slice properties"""
        from src.strategy.time_slice import TimeSlice, TimeFrame
        
        slice_obj = TimeSlice(
            stock_code="TEST",
            timeframe=TimeFrame.DAY_1,
            timestamp=datetime.now(),
            open=100,
            high=110,
            low=90,
            close=105,
            volume=1000000,
        )
        
        self.assertEqual(slice_obj.range, 20)
        self.assertEqual(slice_obj.body, 5)
        self.assertTrue(slice_obj.is_bullish)
        self.assertFalse(slice_obj.is_bearish)


class TestIndicators(unittest.TestCase):
    """Test cases for technical indicators"""
    
    def setUp(self):
        """Set up test data"""
        np.random.seed(42)
        self.close_prices = np.array([100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                                       111, 110, 112, 114, 113, 115, 117, 116, 118, 120])
        self.high_prices = self.close_prices + np.random.uniform(1, 3, 20)
        self.low_prices = self.close_prices - np.random.uniform(1, 3, 20)
        self.volumes = np.random.randint(1000000, 10000000, 20)
    
    def test_sma_calculation(self):
        """Test SMA calculation"""
        from src.strategy.indicators import IndicatorCalculator
        
        sma = IndicatorCalculator.sma(self.close_prices, 5)
        
        self.assertEqual(len(sma), len(self.close_prices))
        self.assertTrue(np.isnan(sma[3]))
        self.assertFalse(np.isnan(sma[4]))
    
    def test_ema_calculation(self):
        """Test EMA calculation"""
        from src.strategy.indicators import IndicatorCalculator
        
        ema = IndicatorCalculator.ema(self.close_prices, 5)
        
        self.assertEqual(len(ema), len(self.close_prices))
        self.assertFalse(np.isnan(ema[0]))
    
    def test_macd_calculation(self):
        """Test MACD calculation"""
        from src.strategy.indicators import IndicatorCalculator
        
        dif, dea, macd = IndicatorCalculator.macd(self.close_prices)
        
        self.assertEqual(len(dif), len(self.close_prices))
        self.assertEqual(len(dea), len(self.close_prices))
        self.assertEqual(len(macd), len(self.close_prices))
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        from src.strategy.indicators import IndicatorCalculator
        
        rsi = IndicatorCalculator.rsi(self.close_prices, 14)
        
        self.assertEqual(len(rsi), len(self.close_prices))
        self.assertTrue(all(0 <= rsi[i] <= 100 for i in range(14, len(rsi)) if not np.isnan(rsi[i])))
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        from src.strategy.indicators import IndicatorCalculator
        
        upper, middle, lower = IndicatorCalculator.bollinger_bands(self.close_prices)
        
        self.assertEqual(len(upper), len(self.close_prices))
        self.assertEqual(len(middle), len(self.close_prices))
        self.assertEqual(len(lower), len(self.close_prices))


class TestMAStrategy(unittest.TestCase):
    """Test cases for MA strategy"""
    
    def setUp(self):
        """Set up test data"""
        from src.strategy.strategies.ma_strategy import MAStrategy, MAStrategyConfig
        
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        
        trend = np.linspace(100, 120, 100)
        noise = np.random.uniform(-2, 2, 100)
        prices = trend + noise
        
        self.test_data = pd.DataFrame({
            "date": dates,
            "open": prices - np.random.uniform(0, 2, 100),
            "high": prices + np.random.uniform(1, 3, 100),
            "low": prices - np.random.uniform(1, 3, 100),
            "close": prices,
            "volume": np.random.randint(1000000, 10000000, 100),
        })
        
        config = MAStrategyConfig(fast_period=5, slow_period=10)
        self.strategy = MAStrategy(config)
    
    def test_strategy_initialization(self):
        """Test strategy initialization"""
        self.assertEqual(self.strategy.name, "MAStrategy")
        self.assertEqual(self.strategy.fast_period, 5)
        self.assertEqual(self.strategy.slow_period, 10)
    
    def test_signal_generation(self):
        """Test signal generation"""
        signals = self.strategy.generate_signals(self.test_data)
        
        self.assertIsInstance(signals, list)
        
        for signal in signals:
            self.assertIsNotNone(signal.signal_type)
            self.assertGreater(signal.price, 0)
    
    def test_ma_status(self):
        """Test MA status retrieval"""
        status = self.strategy.get_ma_status(self.test_data)
        
        self.assertIn("fast_ma", status)
        self.assertIn("slow_ma", status)
        self.assertIn("trend", status)


class TestBacktestEngine(unittest.TestCase):
    """Test cases for backtest engine"""
    
    def setUp(self):
        """Set up test data"""
        from src.strategy.backtest_engine import BacktestEngine, BacktestConfig
        from src.strategy.strategies.ma_strategy import MAStrategy
        
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        
        trend = np.linspace(100, 120, 100)
        noise = np.random.uniform(-2, 2, 100)
        prices = trend + noise
        
        self.test_data = pd.DataFrame({
            "date": dates,
            "open": prices - np.random.uniform(0, 2, 100),
            "high": prices + np.random.uniform(1, 3, 100),
            "low": prices - np.random.uniform(1, 3, 100),
            "close": prices,
            "volume": np.random.randint(1000000, 10000000, 100),
        })
        
        config = BacktestConfig(initial_capital=100000, commission_rate=0.0003)
        self.engine = BacktestEngine(config)
        self.strategy = MAStrategy()
    
    def test_backtest_execution(self):
        """Test backtest execution"""
        result = self.engine.run(self.strategy, self.test_data, "TEST")
        
        self.assertIsNotNone(result)
        self.assertEqual(result.stock_code, "TEST")
        self.assertEqual(result.strategy_name, "MAStrategy")
        self.assertGreaterEqual(result.total_trades, 0)
    
    def test_backtest_result_metrics(self):
        """Test backtest result metrics"""
        result = self.engine.run(self.strategy, self.test_data, "TEST")
        
        self.assertIsInstance(result.total_return, float)
        self.assertIsInstance(result.total_return_pct, float)
        self.assertIsInstance(result.max_drawdown, float)
        self.assertIsInstance(result.sharpe_ratio, float)
        self.assertIsInstance(result.win_rate, float)


class TestPerformanceAnalyzer(unittest.TestCase):
    """Test cases for performance analyzer"""
    
    def setUp(self):
        """Set up test data"""
        from src.strategy.performance import PerformanceAnalyzer
        
        self.analyzer = PerformanceAnalyzer()
        
        np.random.seed(42)
        equity = 100000
        self.equity_curve = []
        
        for i in range(100):
            equity += np.random.uniform(-1000, 1500)
            self.equity_curve.append({"equity": equity})
        
        self.trades = [
            type("Trade", (), {
                "trade_type": "sell",
                "pnl": 1000,
                "pnl_pct": 5.0
            })(),
            type("Trade", (), {
                "trade_type": "sell",
                "pnl": -500,
                "pnl_pct": -2.5
            })(),
            type("Trade", (), {
                "trade_type": "sell",
                "pnl": 800,
                "pnl_pct": 4.0
            })(),
        ]
    
    def test_performance_analysis(self):
        """Test performance analysis"""
        metrics = self.analyzer.analyze(self.equity_curve, self.trades, 100000)
        
        self.assertIsNotNone(metrics)
        self.assertIsInstance(metrics.total_return, float)
        self.assertIsInstance(metrics.sharpe_ratio, float)
    
    def test_report_generation(self):
        """Test report generation"""
        metrics = self.analyzer.analyze(self.equity_curve, self.trades, 100000)
        report = self.analyzer.generate_report(metrics, "TestStrategy")
        
        self.assertIn("TestStrategy", report)
        self.assertIn("Total Return", report)


class TestRiskManager(unittest.TestCase):
    """Test cases for risk manager"""
    
    def setUp(self):
        """Set up test data"""
        from src.monitoring.risk_manager import RiskManager, RiskConfig
        
        config = RiskConfig(
            max_position_size_pct=0.1,
            max_daily_loss_pct=0.03,
            default_stop_loss_pct=0.08
        )
        self.risk_manager = RiskManager(config)
    
    def test_position_size_check(self):
        """Test position size check"""
        result = self.risk_manager.can_open_position(
            stock_code="TEST",
            amount=5000,
            total_capital=100000,
            current_exposure=20000
        )
        
        self.assertIn("allowed", result)
        self.assertIn("reasons", result)
    
    def test_position_size_calculation(self):
        """Test position size calculation"""
        shares = self.risk_manager.calculate_position_size(
            entry_price=100,
            stop_loss_price=92,
            total_capital=100000,
            risk_per_trade_pct=0.02
        )
        
        self.assertGreater(shares, 0)
    
    def test_stop_loss_calculation(self):
        """Test stop loss calculation"""
        stop_loss = self.risk_manager.calculate_stop_loss(100, "long")
        
        self.assertEqual(stop_loss, 92.0)


class TestPositionTracker(unittest.TestCase):
    """Test cases for position tracker"""
    
    def setUp(self):
        """Set up test data"""
        from src.monitoring.position_tracker import PositionTracker
        
        self.tracker = PositionTracker()
    
    def test_open_position(self):
        """Test opening position"""
        position = self.tracker.open_position(
            stock_code="TEST",
            quantity=100,
            price=50.0,
            stock_name="Test Stock"
        )
        
        self.assertEqual(position.stock_code, "TEST")
        self.assertEqual(position.quantity, 100)
        self.assertEqual(position.avg_cost, 50.0)
    
    def test_close_position(self):
        """Test closing position"""
        self.tracker.open_position("TEST", 100, 50.0)
        
        result = self.tracker.close_position("TEST", 50, 55.0)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["quantity"], 50)
        self.assertGreater(result["pnl"], 0)
    
    def test_position_summary(self):
        """Test position summary"""
        self.tracker.open_position("TEST1", 100, 50.0)
        self.tracker.open_position("TEST2", 200, 30.0)
        
        summary = self.tracker.get_summary()
        
        self.assertEqual(summary["total_positions"], 2)
        self.assertEqual(summary["total_shares"], 300)


class TestTradeLog(unittest.TestCase):
    """Test cases for trade log"""
    
    def setUp(self):
        """Set up test data"""
        from src.monitoring.trade_log import TradeLog, TradeType
        
        self.trade_log = TradeLog()
        self.trade_type = TradeType
    
    def test_add_trade(self):
        """Test adding trade"""
        trade = self.trade_log.create_trade(
            stock_code="TEST",
            trade_type=self.trade_type.BUY,
            quantity=100,
            price=50.0
        )
        
        self.assertIsNotNone(trade.trade_id)
        self.assertEqual(trade.stock_code, "TEST")
    
    def test_get_trades(self):
        """Test getting trades"""
        self.trade_log.create_trade("TEST1", self.trade_type.BUY, 100, 50.0)
        self.trade_log.create_trade("TEST2", self.trade_type.BUY, 200, 30.0)
        
        trades = self.trade_log.get_trades()
        
        self.assertEqual(len(trades), 2)
    
    def test_statistics(self):
        """Test trade statistics"""
        self.trade_log.create_trade("TEST", self.trade_type.BUY, 100, 50.0)
        self.trade_log.create_trade("TEST", self.trade_type.SELL, 100, 55.0)
        
        stats = self.trade_log.get_statistics()
        
        self.assertEqual(stats["total_trades"], 2)


class TestChartGenerator(unittest.TestCase):
    """Test cases for chart generator"""
    
    def setUp(self):
        """Set up test data"""
        from src.visualization.charts import ChartGenerator, ChartConfig
        
        config = ChartConfig(title="Test Chart")
        self.generator = ChartGenerator(config)
        
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=50, freq="D")
        
        self.test_data = pd.DataFrame({
            "date": dates,
            "open": np.random.uniform(100, 110, 50),
            "high": np.random.uniform(110, 120, 50),
            "low": np.random.uniform(90, 100, 50),
            "close": np.random.uniform(100, 110, 50),
            "volume": np.random.randint(1000000, 10000000, 50),
        })
    
    def test_line_chart_generation(self):
        """Test line chart generation"""
        chart = self.generator.generate_line_chart(
            self.test_data,
            "date",
            ["close"],
            title="Price Chart"
        )
        
        self.assertIsNotNone(chart)
        self.assertIsInstance(chart, str)
    
    def test_candlestick_chart_generation(self):
        """Test candlestick chart generation"""
        chart = self.generator.generate_candlestick_chart(
            self.test_data,
            title="Candlestick Chart"
        )
        
        self.assertIsNotNone(chart)
    
    def test_equity_curve_generation(self):
        """Test equity curve generation"""
        equity_curve = [
            {"equity": 100000 + i * 100} for i in range(50)
        ]
        
        chart = self.generator.generate_equity_curve(equity_curve)
        
        self.assertIsNotNone(chart)


if __name__ == "__main__":
    unittest.main(verbosity=2)
