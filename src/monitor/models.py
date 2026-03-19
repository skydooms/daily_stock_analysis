# -*- coding: utf-8 -*-
"""
Stock monitor data models.

Defines SQLAlchemy models for stock monitoring:
- StockMonitorConfig: User's monitoring configuration
- StockMonitorState: Real-time monitoring state
- StockMonitorAlert: Alert history
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from src.storage import Base
else:
    from src.storage import Base


class StockMonitorConfig(Base):
    """
    Stock monitoring configuration.

    Stores user's monitoring settings for a specific stock.
    """
    __tablename__ = "stock_monitor_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(16), nullable=False, index=True)
    stock_name = Column(String(64))
    user_id = Column(String(64), index=True)
    chat_id = Column(String(64), index=True)
    monitor_type = Column(String(16), nullable=False, default="realtime")
    threshold_1pct_enabled = Column(Boolean, nullable=False, default=True)
    threshold_2pct_enabled = Column(Boolean, nullable=False, default=True)
    window_minutes = Column(Integer, nullable=False, default=10)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    state = relationship("StockMonitorState", back_populates="config", uselist=False)
    alerts = relationship("StockMonitorAlert", back_populates="config")

    __table_args__ = (
        UniqueConstraint("stock_code", "user_id", name="uix_monitor_config_stock_user"),
        Index("ix_monitor_config_user_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<StockMonitorConfig(stock_code={self.stock_code}, user_id={self.user_id}, type={self.monitor_type})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "monitor_type": self.monitor_type,
            "threshold_1pct_enabled": self.threshold_1pct_enabled,
            "threshold_2pct_enabled": self.threshold_2pct_enabled,
            "window_minutes": self.window_minutes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StockMonitorState(Base):
    """
    Real-time monitoring state.

    Tracks the current monitoring state for each configured stock.
    """
    __tablename__ = "stock_monitor_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(
        Integer,
        ForeignKey("stock_monitor_configs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    stock_code = Column(String(16), nullable=False, index=True)
    baseline_price = Column(Float, nullable=True)
    baseline_time = Column(DateTime, nullable=True)
    last_price = Column(Float, nullable=True)
    last_change_pct = Column(Float, nullable=True)
    last_check_time = Column(DateTime, nullable=True, index=True)
    alert_1pct_triggered = Column(Boolean, nullable=False, default=False)
    alert_2pct_triggered = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    config = relationship("StockMonitorConfig", back_populates="state")

    __table_args__ = (
        Index("ix_monitor_state_stock_check", "stock_code", "last_check_time"),
    )

    def __repr__(self) -> str:
        return f"<StockMonitorState(stock_code={self.stock_code}, last_change_pct={self.last_change_pct})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "config_id": self.config_id,
            "stock_code": self.stock_code,
            "baseline_price": self.baseline_price,
            "baseline_time": self.baseline_time.isoformat() if self.baseline_time else None,
            "last_price": self.last_price,
            "last_change_pct": self.last_change_pct,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "alert_1pct_triggered": self.alert_1pct_triggered,
            "alert_2pct_triggered": self.alert_2pct_triggered,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StockMonitorAlert(Base):
    """
    Alert history.

    Records all triggered alerts for audit and statistics.
    """
    __tablename__ = "stock_monitor_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(
        Integer,
        ForeignKey("stock_monitor_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_code = Column(String(16), nullable=False, index=True)
    alert_type = Column(String(16), nullable=False)
    change_pct = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    alert_time = Column(DateTime, nullable=False, default=datetime.now, index=True)
    notified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.now)

    config = relationship("StockMonitorConfig", back_populates="alerts")

    __table_args__ = (
        Index("ix_monitor_alert_stock_time", "stock_code", "alert_time"),
    )

    def __repr__(self) -> str:
        return f"<StockMonitorAlert(stock_code={self.stock_code}, type={self.alert_type}, change_pct={self.change_pct})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "config_id": self.config_id,
            "stock_code": self.stock_code,
            "alert_type": self.alert_type,
            "change_pct": self.change_pct,
            "price": self.price,
            "alert_time": self.alert_time.isoformat() if self.alert_time else None,
            "notified": self.notified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
