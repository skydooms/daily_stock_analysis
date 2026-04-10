# -*- coding: utf-8 -*-
"""
Stock monitor data models.

Defines SQLAlchemy models for stock monitoring:
- StockMonitorConfig: User's monitoring configuration
- StockMonitorState: Real-time monitoring state
- StockMonitorAlert: Alert history
"""

from datetime import datetime, timedelta, timezone
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

# China timezone (UTC+8)
TZ_CN = timezone(timedelta(hours=8))


def get_now_cn() -> datetime:
    """Get current time in China timezone (UTC+8)."""
    # SQLite doesn't support timezones, return naive datetime
    return datetime.now()


def to_cn_time(dt: datetime) -> datetime:
    """Convert datetime to China timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ_CN)
    return dt.astimezone(TZ_CN)


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

    # Threshold configurations (all in percentage)
    # Level 1: Today's change > level1_threshold (default 3.5%)
    level1_threshold = Column(Float, nullable=False, default=3.5)
    level1_enabled = Column(Boolean, nullable=False, default=True)

    # Level 2: Today's change > level2_threshold (default 2.0%)
    level2_threshold = Column(Float, nullable=False, default=2.0)
    level2_enabled = Column(Boolean, nullable=False, default=True)

    # Level 3: Window change > level3_threshold (default 0.5%)
    level3_threshold = Column(Float, nullable=False, default=0.5)
    level3_enabled = Column(Boolean, nullable=False, default=True)

    window_minutes = Column(Integer, nullable=False, default=10)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, default=get_now_cn, index=True)
    updated_at = Column(DateTime, default=get_now_cn, onupdate=get_now_cn)

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
            "level1_threshold": self.level1_threshold,
            "level1_enabled": self.level1_enabled,
            "level2_threshold": self.level2_threshold,
            "level2_enabled": self.level2_enabled,
            "level3_threshold": self.level3_threshold,
            "level3_enabled": self.level3_enabled,
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

    # Window-based monitoring (for level 3)
    baseline_price = Column(Float, nullable=True)
    baseline_time = Column(DateTime, nullable=True)

    # Today's start price (for level 1 and 2)
    today_start_price = Column(Float, nullable=True)
    today_start_time = Column(DateTime, nullable=True)

    last_price = Column(Float, nullable=True)
    last_change_pct = Column(Float, nullable=True)
    last_check_time = Column(DateTime, nullable=True, index=True)

    # Alert trigger flags
    alert_level1_triggered = Column(Boolean, nullable=False, default=False)
    alert_level2_triggered = Column(Boolean, nullable=False, default=False)
    alert_level3_triggered = Column(Boolean, nullable=False, default=False)

    updated_at = Column(DateTime, default=get_now_cn, onupdate=get_now_cn)

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
            "today_start_price": self.today_start_price,
            "today_start_time": self.today_start_time.isoformat() if self.today_start_time else None,
            "last_price": self.last_price,
            "last_change_pct": self.last_change_pct,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "alert_level1_triggered": self.alert_level1_triggered,
            "alert_level2_triggered": self.alert_level2_triggered,
            "alert_level3_triggered": self.alert_level3_triggered,
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
    alert_level = Column(Integer, nullable=False)  # 1, 2, or 3
    alert_type = Column(String(32), nullable=False)  # 'today_change' or 'window_change'
    change_pct = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    alert_time = Column(DateTime, nullable=False, default=get_now_cn, index=True)
    notified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_now_cn)

    config = relationship("StockMonitorConfig", back_populates="alerts")

    __table_args__ = (
        Index("ix_monitor_alert_stock_time", "stock_code", "alert_time"),
    )

    def __repr__(self) -> str:
        return f"<StockMonitorAlert(stock_code={self.stock_code}, level={self.alert_level}, change_pct={self.change_pct})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "config_id": self.config_id,
            "stock_code": self.stock_code,
            "alert_level": self.alert_level,
            "alert_type": self.alert_type,
            "change_pct": self.change_pct,
            "price": self.price,
            "alert_time": self.alert_time.isoformat() if self.alert_time else None,
            "notified": self.notified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
