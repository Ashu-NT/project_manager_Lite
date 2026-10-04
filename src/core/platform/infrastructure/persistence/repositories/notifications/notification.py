from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.core.platform.contract.repositories.notifications.contracts import (
    NotificationRepository,
)
from src.core.platform.domain.notifications import Notification
from src.core.platform.infrastructure.persistence.mappers.notifications.notification import (
    notification_from_orm,
    notification_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.notifications.notification import (
    NotificationORM,
)


class SqlAlchemyNotificationRepository(NotificationRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, notification: Notification) -> None:
        self.session.add(notification_to_orm(notification))

    def add_idempotent(self, notification: Notification) -> tuple[Notification, bool]:
        if not notification.tenant_id or not notification.source_event_id:
            raise ValueError("Idempotent notifications require tenant and source event IDs")
        values = {
            column.name: getattr(notification_to_orm(notification), column.name)
            for column in NotificationORM.__table__.columns
        }
        dialect = self.session.get_bind().dialect.name
        if dialect == "postgresql":
            stmt = pg_insert(NotificationORM).values(**values).on_conflict_do_nothing(
                index_elements=["tenant_id", "source_event_id", "category", "recipient_user_id"],
                index_where=NotificationORM.source_event_id.is_not(None),
            )
        elif dialect == "sqlite":
            stmt = sqlite_insert(NotificationORM).values(**values).on_conflict_do_nothing(
                index_elements=["tenant_id", "source_event_id", "category", "recipient_user_id"],
                index_where=NotificationORM.source_event_id.is_not(None),
            )
        else:
            raise RuntimeError(f"Unsupported notification idempotency backend: {dialect}")
        inserted = bool(self.session.execute(stmt).rowcount)
        if inserted:
            return notification, True
        existing = self.session.scalar(
            select(NotificationORM).where(
                NotificationORM.tenant_id == notification.tenant_id,
                NotificationORM.source_event_id == notification.source_event_id,
                NotificationORM.category == notification.category,
                NotificationORM.recipient_user_id == notification.recipient_user_id,
            )
        )
        if existing is None:
            raise RuntimeError("Notification identity conflict was not visible in this transaction")
        resolved = notification_from_orm(existing)
        if (
            resolved.organization_id != notification.organization_id
            or resolved.title != notification.title
            or resolved.body != notification.body
            or resolved.metadata != notification.metadata
        ):
            raise ValueError("Notification source identity was reused with different content")
        return resolved, False

    @staticmethod
    def _visibility(user_id: str, tenant_id: str | None, organization_id: str | None):
        invitation = and_(
            NotificationORM.organization_id.is_(None),
            NotificationORM.tenant_id.is_not(None),
            NotificationORM.category.in_(("tenant.invitation.issued", "tenant.invitation.revoked")),
        )
        if tenant_id:
            scoped = and_(
                NotificationORM.tenant_id == tenant_id,
                or_(
                    NotificationORM.organization_id.is_(None),
                    NotificationORM.organization_id == organization_id,
                ),
            )
            scope = or_(scoped, invitation)
        else:
            scope = invitation
        return and_(NotificationORM.recipient_user_id == user_id, scope)

    def get_for_user(
        self, notification_id: str, *, user_id: str,
        tenant_id: str | None, organization_id: str | None,
    ) -> Notification | None:
        obj = self.session.scalar(select(NotificationORM).where(
            NotificationORM.id == notification_id,
            self._visibility(user_id, tenant_id, organization_id),
        ))
        return notification_from_orm(obj) if obj is not None else None

    def list_for_user(
        self,
        user_id: str,
        *,
        tenant_id: str | None,
        organization_id: str | None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        stmt = select(NotificationORM).where(
            self._visibility(user_id, tenant_id, organization_id)
        )
        if unread_only:
            stmt = stmt.where(NotificationORM.read_at.is_(None))
        stmt = stmt.order_by(NotificationORM.created_at.desc(), NotificationORM.id.desc()).limit(
            min(100, max(0, int(limit)))
        )
        rows = self.session.execute(stmt).scalars().all()
        return [notification_from_orm(row) for row in rows]

    def mark_read(
        self, notification_id: str, *, user_id: str,
        tenant_id: str | None, organization_id: str | None, read_at: datetime,
    ) -> None:
        self.session.execute(update(NotificationORM).where(
            NotificationORM.id == notification_id,
            self._visibility(user_id, tenant_id, organization_id),
            NotificationORM.read_at.is_(None),
        ).values(read_at=read_at))

    def count_unread_for_user(
        self, user_id: str, *, tenant_id: str | None, organization_id: str | None,
    ) -> int:
        stmt = select(func.count()).select_from(NotificationORM).where(
            self._visibility(user_id, tenant_id, organization_id),
            NotificationORM.read_at.is_(None),
        )
        return int(self.session.execute(stmt).scalar_one())

    def mark_all_read_for_user(
        self, user_id: str, *, tenant_id: str | None,
        organization_id: str | None, read_at: datetime,
    ) -> int:
        stmt = (
            update(NotificationORM)
            .where(
                self._visibility(user_id, tenant_id, organization_id),
                NotificationORM.read_at.is_(None),
            )
            .values(read_at=read_at)
        )
        result = self.session.execute(stmt)
        return int(result.rowcount or 0)


__all__ = ["SqlAlchemyNotificationRepository"]
