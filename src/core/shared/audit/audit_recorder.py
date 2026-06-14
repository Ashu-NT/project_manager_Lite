from __future__ import annotations

from typing import Any


def record_audit_entry(
    owner: object,
    *,
    operation: str,
    entity_type: str,
    entity_id: str,
    module: str,
    actor_id: str | None = None,
    actor_type: str = "user",
    actor_username: str | None = None,
    actor_ip: str | None = None,
    entity_parent_id: str | None = None,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    organization_id: str | None = None,
    workspace_id: str | None = None,
    request_id: str | None = None,
    source: str = "api",
    severity: str = "low",
    compliance_tag: str = "none",
    metadata: dict[str, Any] | None = None,
) -> None:
    enterprise_audit_service = getattr(owner, "_enterprise_audit_service", None)
    if enterprise_audit_service is None:
        return
    enterprise_audit_service.record(
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        module=module,
        actor_id=actor_id,
        actor_type=actor_type,
        actor_username=actor_username,
        actor_ip=actor_ip,
        entity_parent_id=entity_parent_id,
        field=field,
        old_value=old_value,
        new_value=new_value,
        organization_id=organization_id,
        workspace_id=workspace_id,
        request_id=request_id,
        source=source,
        severity=severity,
        compliance_tag=compliance_tag,
        metadata=metadata,
        commit=True,
    )


__all__ = ["record_audit_entry"]
