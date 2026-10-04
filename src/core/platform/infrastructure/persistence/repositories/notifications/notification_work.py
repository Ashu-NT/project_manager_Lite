"""Transaction-neutral persistence for committed, local in-app delivery work."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.orm.notifications.notification_work import (
    NotificationWorkORM,
)


def enqueue_notification_work(
    session: Session,
    *,
    tenant_id: str,
    organization_id: str | None,
    source_event_id: str,
    recipient_user_id: str,
    category: str,
    title: str,
    body: str,
    metadata: dict | None = None,
) -> None:
    if not all((tenant_id, source_event_id, recipient_user_id, category, title, body)):
        raise ValueError("Notification work requires a scoped event and recipient")
    encoded = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"))
    if len(encoded) > 4096:
        raise ValueError("Notification metadata exceeds the safe bound")
    now = datetime.now(timezone.utc)
    values = dict(
        id=str(uuid4()), tenant_id=tenant_id, organization_id=organization_id,
        source_event_id=source_event_id, recipient_user_id=recipient_user_id,
        category=category, title=title, body=body, metadata_json=encoded,
        status="pending", attempt_count=0, available_at=now, created_at=now,
    )
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        stmt = pg_insert(NotificationWorkORM).values(**values)
    elif dialect == "sqlite":
        stmt = sqlite_insert(NotificationWorkORM).values(**values)
    else:
        raise RuntimeError(f"Unsupported notification work backend: {dialect}")
    inserted = session.execute(stmt.on_conflict_do_nothing(
        index_elements=["tenant_id", "source_event_id", "category", "recipient_user_id"],
    )).rowcount
    if inserted:
        return
    existing = session.scalar(select(NotificationWorkORM).where(
        NotificationWorkORM.tenant_id == tenant_id,
        NotificationWorkORM.source_event_id == source_event_id,
        NotificationWorkORM.category == category,
        NotificationWorkORM.recipient_user_id == recipient_user_id,
    ))
    if existing is None or (
        existing.organization_id != organization_id or existing.title != title
        or existing.body != body or existing.metadata_json != encoded
    ):
        raise ValueError("Notification work event ID was reused with different content")


def next_notification_work(
    session: Session, *, tenant_id: str, organization_id: str | None,
    work_id: str | None = None, lock: bool = True,
) -> NotificationWorkORM | None:
    now = datetime.now(timezone.utc)
    stmt = select(NotificationWorkORM).where(
        NotificationWorkORM.tenant_id == tenant_id,
        NotificationWorkORM.organization_id == organization_id,
        NotificationWorkORM.status.in_(("pending", "retry")),
        NotificationWorkORM.available_at <= now,
    ).order_by(NotificationWorkORM.available_at, NotificationWorkORM.id).limit(1)
    if work_id is not None:
        stmt = stmt.where(NotificationWorkORM.id == work_id)
    if lock and session.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    return session.scalar(stmt)
