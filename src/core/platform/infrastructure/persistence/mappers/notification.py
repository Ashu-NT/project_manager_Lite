from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.core.platform.notifications.domain import Notification
from src.core.platform.infrastructure.persistence.orm.notification import NotificationORM


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


def notification_to_orm(notification: Notification) -> NotificationORM:
    return NotificationORM(
        id=notification.id,
        recipient_user_id=notification.recipient_user_id,
        tenant_id=notification.tenant_id,
        category=notification.category,
        title=notification.title,
        body=notification.body,
        created_at=notification.created_at,
        read_at=notification.read_at,
        metadata_json=_to_json(notification.metadata),
    )


def notification_from_orm(obj: NotificationORM) -> Notification:
    return Notification(
        id=obj.id,
        recipient_user_id=obj.recipient_user_id,
        tenant_id=obj.tenant_id,
        category=obj.category,
        title=obj.title,
        body=obj.body,
        created_at=_coerce_utc(obj.created_at),
        read_at=_coerce_utc(obj.read_at) if obj.read_at is not None else None,
        metadata=_from_json(obj.metadata_json),
    )


__all__ = ["notification_to_orm", "notification_from_orm"]
