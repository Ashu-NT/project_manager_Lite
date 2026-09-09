from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from src.core.platform.contract.repositories.events.notifications.contracts import NotificationRepository
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

    def count_unread_for_user(self, user_id: str) -> int:
        stmt = select(func.count()).select_from(NotificationORM).where(
            NotificationORM.recipient_user_id == user_id,
            NotificationORM.read_at.is_(None),
        )
        return int(self.session.execute(stmt).scalar_one())

    def mark_all_read_for_user(self, user_id: str, *, read_at: datetime) -> int:
        stmt = (
            update(NotificationORM)
            .where(
                NotificationORM.recipient_user_id == user_id,
                NotificationORM.read_at.is_(None),
            )
            .values(read_at=read_at)
        )
        result = self.session.execute(stmt)
        return int(result.rowcount or 0)


__all__ = ["SqlAlchemyNotificationRepository"]
