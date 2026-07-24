from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.core.platform.activity.domain.activity_entry import ActivityEntry
from src.core.platform.infrastructure.persistence.orm.activity import ActivityEntryORM


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


def activity_to_orm(entry: ActivityEntry) -> ActivityEntryORM:
    return ActivityEntryORM(
        id=entry.id,
        action=entry.action,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        actor_id=entry.actor_id,
        actor_role=entry.actor_role,
        module=entry.module,
        workspace_id=entry.workspace_id,
        tenant_id=entry.tenant_id,
        organization_id=entry.organization_id,
        timestamp=entry.timestamp,
        type=entry.type,
        human_message=entry.human_message,
        details_json=_to_json(entry.details),
        context_json=_to_json(entry.context),
        parent_entity_id=entry.parent_entity_id,
        icon=entry.icon,
        color=entry.color,
        visibility=entry.visibility,
    )


def activity_from_orm(obj: ActivityEntryORM) -> ActivityEntry:
    return ActivityEntry(
        id=obj.id,
        action=obj.action,
        entity_type=obj.entity_type,
        entity_id=obj.entity_id,
        actor_id=obj.actor_id,
        actor_role=obj.actor_role,
        module=obj.module,
        workspace_id=obj.workspace_id,
        tenant_id=obj.tenant_id,
        organization_id=obj.organization_id,
        timestamp=_coerce_utc(obj.timestamp),
        type=obj.type,
        human_message=obj.human_message or "",
        details=_from_json(obj.details_json),
        context=_from_json(obj.context_json),
        parent_entity_id=obj.parent_entity_id,
        icon=obj.icon,
        color=obj.color,
        visibility=obj.visibility,
    )


__all__ = ["activity_to_orm", "activity_from_orm"]
