# -*- coding: utf-8 -*-
"""Stock monitor repository for database access."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, delete, desc, or_, select, update
from sqlalchemy.exc import IntegrityError

from src.storage import DatabaseManager
from src.monitor.models import (
    StockMonitorAlert, StockMonitorConfig, StockMonitorState,
    get_now_cn, TZ_CN
)

logger = logging.getLogger(__name__)


def is_same_day_cn(d1: datetime, d2: datetime) -> bool:
    """Check if two datetimes are the same day in China timezone."""
    d1_cn = d1.astimezone(TZ_CN) if d1.tzinfo else d1.replace(tzinfo=TZ_CN)
    d2_cn = d2.astimezone(TZ_CN) if d2.tzinfo else d2.replace(tzinfo=TZ_CN)
    return (d1_cn.year == d2_cn.year and
            d1_cn.month == d2_cn.month and
            d1_cn.day == d2_cn.day)


class StockMonitorRepository:
    """Database access layer for stock monitor."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Ensure monitor tables exist."""
        from src.monitor.models import Base
        engine = self.db._engine
        Base.metadata.create_all(engine)

    def add_config(
        self,
        stock_code: str,
        stock_name: Optional[str] = None,
        user_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        monitor_type: str = "realtime",
        level1_threshold: float = 3.5,
        level1_enabled: bool = True,
        level2_threshold: float = 2.0,
        level2_enabled: bool = True,
        level3_threshold: float = 0.5,
        level3_enabled: bool = True,
        window_minutes: int = 10,
    ) -> Optional[StockMonitorConfig]:
        """Add a new monitor configuration."""
        with self.db.get_session() as session:
            try:
                config = StockMonitorConfig(
                    stock_code=stock_code.upper(),
                    stock_name=stock_name,
                    user_id=user_id,
                    chat_id=chat_id,
                    monitor_type=monitor_type,
                    level1_threshold=level1_threshold,
                    level1_enabled=level1_enabled,
                    level2_threshold=level2_threshold,
                    level2_enabled=level2_enabled,
                    level3_threshold=level3_threshold,
                    level3_enabled=level3_enabled,
                    window_minutes=window_minutes,
                    is_active=True,
                )
                session.add(config)
                session.flush()
                state = StockMonitorState(
                    config_id=config.id,
                    stock_code=stock_code.upper(),
                )
                session.add(state)
                session.commit()
                session.refresh(config)
                logger.info(f"[MonitorRepo] Added config: {stock_code} for user={user_id}")
                return config
            except IntegrityError:
                session.rollback()
                logger.warning(f"[MonitorRepo] Config already exists: {stock_code} for user={user_id}")
                return None
            except Exception as e:
                session.rollback()
                logger.error(f"[MonitorRepo] Failed to add config: {e}")
                raise

    def remove_config(self, config_id: int) -> bool:
        """Remove a monitor configuration by ID."""
        with self.db.get_session() as session:
            result = session.execute(
                delete(StockMonitorConfig).where(StockMonitorConfig.id == config_id)
            )
            session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"[MonitorRepo] Removed config id={config_id}")
            return deleted

    def remove_config_by_stock(self, stock_code: str, user_id: Optional[str] = None) -> int:
        """Remove monitor configuration(s) by stock code."""
        with self.db.get_session() as session:
            conditions = [StockMonitorConfig.stock_code == stock_code.upper()]
            if user_id:
                conditions.append(StockMonitorConfig.user_id == user_id)
            result = session.execute(
                delete(StockMonitorConfig).where(and_(*conditions))
            )
            session.commit()
            count = result.rowcount
            if count > 0:
                logger.info(f"[MonitorRepo] Removed {count} config(s) for {stock_code}")
            return count

    def get_config(self, config_id: int) -> Optional[StockMonitorConfig]:
        """Get a monitor configuration by ID."""
        with self.db.get_session() as session:
            return session.execute(
                select(StockMonitorConfig).where(StockMonitorConfig.id == config_id)
            ).scalar_one_or_none()

    def get_config_by_stock(
        self, stock_code: str, user_id: Optional[str] = None
    ) -> Optional[StockMonitorConfig]:
        """Get a monitor configuration by stock code and user."""
        with self.db.get_session() as session:
            conditions = [StockMonitorConfig.stock_code == stock_code.upper()]
            if user_id:
                conditions.append(StockMonitorConfig.user_id == user_id)
            return session.execute(
                select(StockMonitorConfig).where(and_(*conditions))
            ).scalar_one_or_none()

    def list_configs(
        self,
        user_id: Optional[str] = None,
        is_active: Optional[bool] = True,
        monitor_type: Optional[str] = None,
    ) -> List[StockMonitorConfig]:
        """List monitor configurations with optional filters."""
        with self.db.get_session() as session:
            conditions = []
            if user_id:
                conditions.append(StockMonitorConfig.user_id == user_id)
            if is_active is not None:
                conditions.append(StockMonitorConfig.is_active == is_active)
            if monitor_type:
                conditions.append(StockMonitorConfig.monitor_type == monitor_type)

            query = select(StockMonitorConfig)
            if conditions:
                query = query.where(and_(*conditions))
            query = query.order_by(StockMonitorConfig.created_at.desc())

            return list(session.execute(query).scalars().all())

    def list_active_configs(self) -> List[StockMonitorConfig]:
        """List all active monitor configurations."""
        return self.list_configs(is_active=True)

    def set_config_active(self, config_id: int, is_active: bool) -> bool:
        """Set the active status of a configuration."""
        with self.db.get_session() as session:
            result = session.execute(
                update(StockMonitorConfig)
                .where(StockMonitorConfig.id == config_id)
                .values(is_active=is_active, updated_at=get_now_cn())
            )
            session.commit()
            return result.rowcount > 0

    def get_state(self, config_id: int) -> Optional[StockMonitorState]:
        """Get the monitoring state for a configuration."""
        with self.db.get_session() as session:
            return session.execute(
                select(StockMonitorState).where(StockMonitorState.config_id == config_id)
            ).scalar_one_or_none()

    def get_state_by_stock(self, stock_code: str) -> Optional[StockMonitorState]:
        """Get the monitoring state by stock code."""
        with self.db.get_session() as session:
            return session.execute(
                select(StockMonitorState).where(
                    StockMonitorState.stock_code == stock_code.upper()
                )
            ).scalar_one_or_none()

    def update_state(
        self,
        config_id: int,
        baseline_price: Optional[float] = None,
        baseline_time: Optional[datetime] = None,
        today_start_price: Optional[float] = None,
        today_start_time: Optional[datetime] = None,
        last_price: Optional[float] = None,
        last_change_pct: Optional[float] = None,
        last_check_time: Optional[datetime] = None,
        alert_level1_triggered: Optional[bool] = None,
        alert_level2_triggered: Optional[bool] = None,
        alert_level3_triggered: Optional[bool] = None,
    ) -> bool:
        """Update the monitoring state."""
        with self.db.get_session() as session:
            values = {"updated_at": get_now_cn()}
            if baseline_price is not None:
                values["baseline_price"] = baseline_price
            if baseline_time is not None:
                values["baseline_time"] = baseline_time
            if today_start_price is not None:
                values["today_start_price"] = today_start_price
            if today_start_time is not None:
                values["today_start_time"] = today_start_time
            if last_price is not None:
                values["last_price"] = last_price
            if last_change_pct is not None:
                values["last_change_pct"] = last_change_pct
            if last_check_time is not None:
                values["last_check_time"] = last_check_time
            if alert_level1_triggered is not None:
                values["alert_level1_triggered"] = alert_level1_triggered
            if alert_level2_triggered is not None:
                values["alert_level2_triggered"] = alert_level2_triggered
            if alert_level3_triggered is not None:
                values["alert_level3_triggered"] = alert_level3_triggered

            result = session.execute(
                update(StockMonitorState)
                .where(StockMonitorState.config_id == config_id)
                .values(**values)
            )
            session.commit()
            return result.rowcount > 0

    def reset_baseline(
        self,
        config_id: int,
        baseline_price: float,
        baseline_time: datetime,
    ) -> bool:
        """Reset window baseline and clear level 3 alert flags."""
        return self.update_state(
            config_id=config_id,
            baseline_price=baseline_price,
            baseline_time=baseline_time,
            last_price=baseline_price,
            last_change_pct=0.0,
            last_check_time=get_now_cn(),
            alert_level3_triggered=False,
        )

    def reset_today_start(
        self,
        config_id: int,
        start_price: float,
        start_time: datetime,
    ) -> bool:
        """Reset today's start price and clear level 1/2 alert flags."""
        return self.update_state(
            config_id=config_id,
            today_start_price=start_price,
            today_start_time=start_time,
            alert_level1_triggered=False,
            alert_level2_triggered=False,
        )

    def add_alert(
        self,
        config_id: int,
        stock_code: str,
        alert_level: int,
        alert_type: str,
        change_pct: float,
        price: float,
        notified: bool = False,
    ) -> Optional[StockMonitorAlert]:
        """Add an alert record."""
        with self.db.get_session() as session:
            try:
                alert = StockMonitorAlert(
                    config_id=config_id,
                    stock_code=stock_code.upper(),
                    alert_level=alert_level,
                    alert_type=alert_type,
                    change_pct=change_pct,
                    price=price,
                    alert_time=get_now_cn(),
                    notified=notified,
                )
                session.add(alert)
                session.commit()
                session.refresh(alert)
                logger.info(
                    f"[MonitorRepo] Added alert: {stock_code} Level {alert_level} {alert_type} {change_pct:.2f}%"
                )
                return alert
            except Exception as e:
                session.rollback()
                logger.error(f"[MonitorRepo] Failed to add alert: {e}")
                return None

    def list_alerts(
        self,
        stock_code: Optional[str] = None,
        config_id: Optional[int] = None,
        user_id: Optional[str] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[StockMonitorAlert]:
        """List recent alerts with optional filters."""
        with self.db.get_session() as session:
            cutoff = get_now_cn() - timedelta(hours=hours)
            conditions = [StockMonitorAlert.alert_time >= cutoff]

            if stock_code:
                conditions.append(StockMonitorAlert.stock_code == stock_code.upper())
            if config_id:
                conditions.append(StockMonitorAlert.config_id == config_id)
            if user_id:
                subquery = select(StockMonitorConfig.id).where(
                    StockMonitorConfig.user_id == user_id
                )
                conditions.append(StockMonitorAlert.config_id.in_(subquery))

            query = (
                select(StockMonitorAlert)
                .where(and_(*conditions))
                .order_by(desc(StockMonitorAlert.alert_time))
                .limit(limit)
            )

            return list(session.execute(query).scalars().all())

    def get_alert_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics for the past N hours."""
        alerts = self.list_alerts(hours=hours, limit=1000)
        if not alerts:
            return {
                "total_alerts": 0,
                "level1_count": 0,
                "level2_count": 0,
                "level3_count": 0,
                "unique_stocks": 0,
            }

        level1_count = sum(1 for a in alerts if a.alert_level == 1)
        level2_count = sum(1 for a in alerts if a.alert_level == 2)
        level3_count = sum(1 for a in alerts if a.alert_level == 3)
        unique_stocks = len(set(a.stock_code for a in alerts))

        return {
            "total_alerts": len(alerts),
            "level1_count": level1_count,
            "level2_count": level2_count,
            "level3_count": level3_count,
            "unique_stocks": unique_stocks,
        }
