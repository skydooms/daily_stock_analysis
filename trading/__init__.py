# -*- coding: utf-8 -*-
"""
Trading Module

This module provides stock trading functionality.

Usage:
    from trading import BaseBroker, Order, Position
    from trading.broker import XQBroker

    # Configure broker
    broker = XQBroker(
        account_id="your_account",
        token="your_token"
    )
    
    # Connect
    if broker.connect():
        # Get account info
        account = broker.get_account_info()
        print(f"Total assets: {account.total_assets}")
        
        # Submit order
        order = Order(
            order_id="",
            stock_code="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=150.0
        )
        result = broker.submit_order(order)
        print(f"Order status: {result.status}")
"""

from .base import (
    OrderSide,
    OrderType,
    OrderStatus,
    Order,
    Position,
    AccountInfo,
    BaseBroker,
    TradingError,
    ConnectionError,
    OrderError,
    InsufficientFundsError,
    InsufficientSharesError,
)

__all__ = [
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "Order",
    "Position",
    "AccountInfo",
    "BaseBroker",
    "TradingError",
    "ConnectionError",
    "OrderError",
    "InsufficientFundsError",
    "InsufficientSharesError",
]
