from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.core.platform.domain.history.audit.audit_entry import AuditEntry
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import AuditEntryORM
from src.core.shared.audit.redaction import redact_changed_fields, redact_sensitive


def _to_json(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, default=str, ensure_ascii=False, sort_keys=True)


def _from_json(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _from_json_required(raw: str | None) -> dict[str, Any]:
    return _from_json(raw) or {}


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def audit_entry_to_orm(entry: AuditEntry) -> AuditEntryORM:
    """The redaction boundary: every structured payload is sanitized here,
    once, on the way into persistence -- no producer needs to remember to
    redact its own metadata/before_data/after_data/changed_fields."""
    return AuditEntryORM(
        id=entry.id,
        timestamp=entry.timestamp,
        actor_id=entry.actor_id,
        actor_type=entry.actor_type,
        actor_username=entry.actor_username,
        actor_display_name=entry.actor_display_name,
        actor_ip=entry.actor_ip,
        actor_user_agent=entry.actor_user_agent,
        session_id=entry.session_id,
        authentication_method=entry.authentication_method,
        impersonated_by_actor_id=entry.impersonated_by_actor_id,
        service_account_id=entry.service_account_id,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        entity_parent_id=entry.entity_parent_id,
        entity_version=entry.entity_version,
        operation=entry.operation,
        category=entry.category,
        severity=entry.severity,
        result=entry.result,
        failure_code=entry.failure_code,
        before_data_json=_to_json(redact_sensitive(entry.before_data) if entry.before_data else None),
        after_data_json=_to_json(redact_sensitive(entry.after_data) if entry.after_data else None),
        changed_fields_json=_to_json(
            redact_changed_fields(entry.changed_fields) if entry.changed_fields else None
        ),
        module=entry.module,
        tenant_id=entry.tenant_id,
        organization_id=entry.organization_id,
        workspace_id=entry.workspace_id,
        project_id=entry.project_id,
        request_id=entry.request_id,
        correlation_id=entry.correlation_id,
        causation_id=entry.causation_id,
        source=entry.source,
        permission_used=entry.permission_used,
        approval_request_id=entry.approval_request_id,
        reason=entry.reason,
        metadata_json=_to_json(redact_sensitive(entry.metadata) or {}),
    )


def audit_entry_from_orm(obj: AuditEntryORM) -> AuditEntry:
    return AuditEntry(
        id=obj.id,
        timestamp=_coerce_utc(obj.timestamp),
        actor_id=obj.actor_id,
        actor_type=obj.actor_type,
        actor_username=obj.actor_username,
        actor_display_name=obj.actor_display_name,
        actor_ip=obj.actor_ip,
        actor_user_agent=obj.actor_user_agent,
        session_id=obj.session_id,
        authentication_method=obj.authentication_method,
        impersonated_by_actor_id=obj.impersonated_by_actor_id,
        service_account_id=obj.service_account_id,
        entity_type=obj.entity_type,
        entity_id=obj.entity_id,
        entity_parent_id=obj.entity_parent_id,
        entity_version=obj.entity_version,
        operation=obj.operation,
        category=obj.category,
        severity=obj.severity,
        result=obj.result,
        failure_code=obj.failure_code,
        before_data=_from_json(obj.before_data_json),
        after_data=_from_json(obj.after_data_json),
        changed_fields=_from_json(obj.changed_fields_json),
        module=obj.module,
        tenant_id=obj.tenant_id,
        organization_id=obj.organization_id,
        workspace_id=obj.workspace_id,
        project_id=obj.project_id,
        request_id=obj.request_id,
        correlation_id=obj.correlation_id,
        causation_id=obj.causation_id,
        source=obj.source,
        permission_used=obj.permission_used,
        approval_request_id=obj.approval_request_id,
        reason=obj.reason,
        metadata=_from_json_required(obj.metadata_json),
    )


__all__ = ["audit_entry_to_orm", "audit_entry_from_orm"]
