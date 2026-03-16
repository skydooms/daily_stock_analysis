# -*- coding: utf-8 -*-
"""
===================================
Trading Module - Order Management
===================================

This module provides order management functionality.

Features:
- Order creation and validation
- Order execution
- Order tracking
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from .base import (
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    BaseBroker,
    OrderError,
)


logger = logging.getLogger(__name__)


class OrderManager:
    """
    Order manager for creating and tracking orders
    
    Usage:
        broker = XQBroker(...)
        manager = OrderManager(broker)
        
        # Create and submit order
        order = manager.create_order(
            stock_code="600519",
            side=OrderSide.BUY,
            quantity=100,
            price=1800.0
        )
        
        # Submit order
        submitted = manager.submit_order(order)
    """
    
    def __init__(self, broker: BaseBroker):
        """
        Initialize order manager
        
        Args:
            broker: Broker instance for order execution
        """
        self._broker = broker
        self._pending_orders: Dict[str, Order] = {}
    
    def create_order(
        self,
        stock_code: str,
        stock_name: str,
        side: OrderSide,
        quantity: int,
        price: Optional[float] = None,
        order_type: OrderType = OrderType.LIMIT
    ) -> Order:
        """
        Create a new order
        
        Args:
            stock_code: Stock code
            stock_name: Stock name
            side: Buy or sell
            quantity: Number of shares
            price: Order price (required for limit orders)
            order_type: Order type
            
        Returns:
            Created Order object
        """
        order_id = self._generate_order_id()
        
        order = Order(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_name,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        self._validate_order(order)
        self._pending_orders[order_id] = order
        
        logger.info(f"Created order: {order_id} - {side.value} {quantity} {stock_code}")
        
        return order
    
    def submit_order(self, order: Order) -> Order:
        """
        Submit an order to the broker
        
        Args:
            order: Order to submit
            
        Returns:
            Updated Order object with broker response
        """
        if order.order_id not in self._pending_orders:
            raise OrderError(f"Order {order.order_id} not found in pending orders")
        
        if not self._broker.is_connected():
            raise OrderError("Broker not connected")
        
        try:
            submitted_order = self._broker.submit_order(order)
            self._pending_orders.pop(order.order_id, None)
            
            logger.info(f"Order submitted: {submitted_order.order_id}")
            
            return submitted_order
            
        except Exception as e:
            logger.error(f"Order submission failed: {e}")
            order.status = OrderStatus.REJECTED
            order.message = str(e)
            raise OrderError(f"Order submission failed: {e}")
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        if order_id in self._pending_orders:
            self._pending_orders[order_id].status = OrderStatus.CANCELLED
            self._pending_orders.pop(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        
        return self._broker.cancel_order(order_id)
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order by ID
        
        Args:
            order_id: Order ID
            
        Returns:
            Order object or None
        """
        if order_id in self._pending_orders:
            return self._pending_orders[order_id]
        
        return self._broker.get_order(order_id)
    
    def get_pending_orders(self) -> List[Order]:
        """
        Get all pending orders
        
        Returns:
            List of pending Order objects
        """
        return list(self._pending_orders.values())
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"ORD{timestamp}{unique_id}"
    
    def _validate_order(self, order: Order) -> None:
        """
        Validate order before submission
        
        Args:
            order: Order to validate
            
        Raises:
            OrderError: If validation fails
        """
        if not order.stock_code:
            raise OrderError("Stock code is required")
        
        if order.quantity <= 0:
            raise OrderError("Quantity must be positive")
        
        if order.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
            if order.price is None or order.price <= 0:
                raise OrderError(f"Price is required for {order.order_type.value} orders")
        
        if order.order_type == OrderType.STOP and order.price is None:
            raise OrderError("Stop price is required for stop orders")
