from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.core.platform.audit.domain import AuditLogEntry
from src.core.platform.infrastructure.persistence.orm.audit import AuditLogORM


def _to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str, ensure_ascii=False)


def _from_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _coerce_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def audit_to_orm(entry: AuditLogEntry) -> AuditLogORM:
    return AuditLogORM(
        id=entry.id,
        occurred_at=entry.occurred_at,
        actor_user_id=entry.actor_user_id,
        actor_username=entry.actor_username,
        action=entry.action,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        project_id=entry.project_id,
        details_json=_to_json(entry.details),
    )


def audit_from_orm(obj: AuditLogORM) -> AuditLogEntry:
    return AuditLogEntry(
        id=obj.id,
        occurred_at=_coerce_utc_datetime(obj.occurred_at),
        actor_user_id=obj.actor_user_id,
        actor_username=obj.actor_username,
        action=obj.action,
        entity_type=obj.entity_type,
        entity_id=obj.entity_id,
        project_id=obj.project_id,
        details=_from_json(obj.details_json),
    )


__all__ = ["audit_to_orm", "audit_from_orm"]
