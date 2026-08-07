from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.contract.events.notifications.contracts import NotificationRepository
from src.core.platform.domain.events.notifications import Notification
from src.core.platform.infrastructure.persistence.mappers.events.notifications.notification import (
    notification_from_orm,
    notification_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.events.notifications.notification import NotificationORM


class SqlAlchemyNotificationRepository(NotificationRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, notification: Notification) -> None:
        self.session.add(notification_to_orm(notification))

    def get(self, notification_id: str) -> Notification | None:
        obj = self.session.get(NotificationORM, notification_id)
        return notification_from_orm(obj) if obj is not None else None

    def list_for_user(
        self,
        user_id: str,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        stmt = select(NotificationORM).where(NotificationORM.recipient_user_id == user_id)
        if unread_only:
            stmt = stmt.where(NotificationORM.read_at.is_(None))
        stmt = stmt.order_by(NotificationORM.created_at.desc()).limit(max(1, int(limit)))
        rows = self.session.execute(stmt).scalars().all()
        return [notification_from_orm(row) for row in rows]

    def mark_read(self, notification_id: str, *, read_at: datetime) -> None:
        obj = self.session.get(NotificationORM, notification_id)
        if obj is None:
            return
        obj.read_at = read_at


__all__ = ["SqlAlchemyNotificationRepository"]
