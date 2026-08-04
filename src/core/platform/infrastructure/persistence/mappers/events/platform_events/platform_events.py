from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.core.platform.domain.events.platform_events.platform_event import PlatformEvent
from src.core.platform.infrastructure.persistence.orm.events.platform_events.platform_events import PlatformEventORM


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


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def platform_event_to_orm(event: PlatformEvent) -> PlatformEventORM:
    return PlatformEventORM(
        id=event.id,
        operation=event.operation,
        actor_user_id=event.actor_user_id,
        tenant_id=event.tenant_id,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        outcome=event.outcome,
        severity=event.severity,
        created_at=event.created_at,
        metadata_json=_to_json(event.metadata),
    )


def platform_event_from_orm(obj: PlatformEventORM) -> PlatformEvent:
    return PlatformEvent(
        id=obj.id,
        operation=obj.operation,
        actor_user_id=obj.actor_user_id,
        tenant_id=obj.tenant_id,
        resource_type=obj.resource_type,
        resource_id=obj.resource_id,
        outcome=obj.outcome,
        severity=obj.severity,
        created_at=_coerce_utc(obj.created_at),
        metadata=_from_json(obj.metadata_json),
    )


__all__ = ["platform_event_to_orm", "platform_event_from_orm"]
