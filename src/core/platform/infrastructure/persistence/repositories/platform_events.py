from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.core.platform.common.exceptions import OperationNotPermittedError
from src.core.platform.platform_events.contracts import PlatformEventRepository
from src.core.platform.platform_events.domain.platform_event import PlatformEvent
from src.core.platform.infrastructure.persistence.mappers.platform_events import (
    platform_event_from_orm,
    platform_event_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.platform_events import PlatformEventORM


class SqlAlchemyPlatformEventRepository(PlatformEventRepository):

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: PlatformEvent) -> None:
        self._prepare_tenant_partition(event.tenant_id)
        orm = platform_event_to_orm(event)
        self._session.add(orm)

    def list_for_tenant(self, tenant_id: str, *, limit: int = 100) -> list[PlatformEvent]:
        self._prepare_tenant_partition(tenant_id)
        stmt = (
            select(PlatformEventORM)
            .where(PlatformEventORM.tenant_id == tenant_id)
            .order_by(PlatformEventORM.created_at.desc())
            .limit(max(1, int(limit)))
        )
        rows = self._session.execute(stmt).scalars().all()
        return [platform_event_from_orm(row) for row in rows]

    def list_for_resource(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        *,
        limit: int = 100,
    ) -> list[PlatformEvent]:
        self._prepare_tenant_partition(tenant_id)
        stmt = (
            select(PlatformEventORM)
            .where(
                PlatformEventORM.tenant_id == tenant_id,
                PlatformEventORM.resource_type == resource_type,
                PlatformEventORM.resource_id == resource_id,
            )
            .order_by(PlatformEventORM.created_at.desc())
            .limit(max(1, int(limit)))
        )
        rows = self._session.execute(stmt).scalars().all()
        return [platform_event_from_orm(row) for row in rows]

    def update(self, event: PlatformEvent) -> None:
        raise OperationNotPermittedError(
            "PlatformEvent records are append-only and cannot be updated.",
            code="PLATFORM_EVENT_IMMUTABLE",
        )

    def delete(self, event_id: str) -> None:
        raise OperationNotPermittedError(
            "PlatformEvent records are append-only and cannot be deleted.",
            code="PLATFORM_EVENT_IMMUTABLE",
        )

    def _prepare_tenant_partition(self, tenant_id: str) -> None:
        normalized_tenant_id = str(tenant_id or "").strip()
        if self._session.get_bind().dialect.name != "postgresql":
            return
        self._session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": normalized_tenant_id},
        )


__all__ = ["SqlAlchemyPlatformEventRepository"]
