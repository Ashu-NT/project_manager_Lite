from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from src.core.platform.contract.read.history.activity_actor_reader import (
    ActivityActorKind,
    ActivityActorPresentation,
)
from src.core.platform.infrastructure.persistence.orm.security.auth.auth import UserORM
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import (
    UserTenantORM,
)


class SqlAlchemyActivityActorReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve_batch(
        self, *, tenant_id: str, actor_ids: tuple[str, ...]
    ) -> dict[str, ActivityActorPresentation]:
        if not actor_ids:
            return {}
        if len(actor_ids) > 200:
            raise ValueError("Activity actor lookup exceeds the bounded page size")
        rows = self._session.execute(
            select(
                UserORM.id, UserORM.account_type, UserORM.is_active,
                UserORM.display_name, UserORM.username, UserTenantORM.status,
            )
            .join(UserTenantORM, and_(
                UserTenantORM.user_id == UserORM.id,
                UserTenantORM.tenant_id == tenant_id,
            ))
            .where(UserORM.id.in_(actor_ids))
        ).all()
        labels: dict[str, ActivityActorPresentation] = {}
        for row in rows:
            if row.account_type != "human":
                labels[row.id] = ActivityActorPresentation(ActivityActorKind.SERVICE, "Service account")
            elif not row.is_active or row.status != "active":
                labels[row.id] = ActivityActorPresentation(ActivityActorKind.DISABLED, "Former user")
            else:
                label = str(row.display_name or row.username or "").strip()
                labels[row.id] = ActivityActorPresentation(ActivityActorKind.HUMAN, label or "User")
        return labels


__all__ = ["SqlAlchemyActivityActorReader"]
