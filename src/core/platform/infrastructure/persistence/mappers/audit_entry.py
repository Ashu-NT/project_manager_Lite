from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.core.platform.audit.domain.audit_entry import AuditEntry
from src.core.platform.infrastructure.persistence.orm.audit_entry import AuditEntryORM


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


def audit_entry_to_orm(entry: AuditEntry) -> AuditEntryORM:
    return AuditEntryORM(
        id=entry.id,
        timestamp=entry.timestamp,
        actor_id=entry.actor_id,
        actor_type=entry.actor_type,
        actor_username=entry.actor_username,
        actor_ip=entry.actor_ip,
        actor_user_agent=entry.actor_user_agent,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        entity_parent_id=entry.entity_parent_id,
        operation=entry.operation,
        field=entry.field,
        old_value=entry.old_value,
        new_value=entry.new_value,
        module=entry.module,
        tenant_id=entry.tenant_id,
        organization_id=entry.organization_id,
        workspace_id=entry.workspace_id,
        request_id=entry.request_id,
        source=entry.source,
        severity=entry.severity,
        compliance_tag=entry.compliance_tag,
        metadata_json=_to_json(entry.metadata),
    )


def audit_entry_from_orm(obj: AuditEntryORM) -> AuditEntry:
    return AuditEntry(
        id=obj.id,
        timestamp=_coerce_utc(obj.timestamp),
        actor_id=obj.actor_id,
        actor_type=obj.actor_type,
        actor_username=obj.actor_username,
        actor_ip=obj.actor_ip,
        actor_user_agent=obj.actor_user_agent,
        entity_type=obj.entity_type,
        entity_id=obj.entity_id,
        entity_parent_id=obj.entity_parent_id,
        operation=obj.operation,
        field=obj.field,
        old_value=obj.old_value,
        new_value=obj.new_value,
        module=obj.module,
        tenant_id=obj.tenant_id,
        organization_id=obj.organization_id,
        workspace_id=obj.workspace_id,
        request_id=obj.request_id,
        source=obj.source,
        severity=obj.severity,
        compliance_tag=obj.compliance_tag,
        metadata=_from_json(obj.metadata_json),
    )


__all__ = ["audit_entry_to_orm", "audit_entry_from_orm"]
