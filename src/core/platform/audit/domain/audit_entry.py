from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.core.platform.common.ids import generate_id


@dataclass
class AuditLogEntry:
    id: str
    occurred_at: datetime
    actor_user_id: str | None
    actor_username: str | None
    action: str
    entity_type: str
    entity_id: str
    project_id: str | None = None
    organization_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
        action: str,
        entity_type: str,
        entity_id: str,
        *,
        actor_user_id: str | None = None,
        actor_username: str | None = None,
        project_id: str | None = None,
        organization_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> "AuditLogEntry":
        return AuditLogEntry(
            id=generate_id(),
            occurred_at=datetime.now(timezone.utc),
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            organization_id=organization_id,
            details=details or {},
        )


@dataclass
class AuditEntry:
    """Enterprise compliance and security audit entry."""

    id: str
    timestamp: datetime

    actor_id: str | None
    actor_type: str
    actor_username: str | None
    actor_ip: str | None
    actor_user_agent: str | None

    entity_type: str
    entity_id: str
    entity_parent_id: str | None

    operation: str
    field: str | None
    old_value: str | None
    new_value: str | None

    module: str
    tenant_id: str | None
    organization_id: str | None
    workspace_id: str | None

    request_id: str | None
    source: str
    severity: str
    compliance_tag: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
        *,
        operation: str,
        entity_type: str,
        entity_id: str,
        module: str,
        actor_id: str | None = None,
        actor_type: str = "user",
        actor_username: str | None = None,
        actor_ip: str | None = None,
        actor_user_agent: str | None = None,
        entity_parent_id: str | None = None,
        field: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        tenant_id: str | None = None,
        organization_id: str | None = None,
        workspace_id: str | None = None,
        request_id: str | None = None,
        source: str = "api",
        severity: str = "low",
        compliance_tag: str = "none",
        metadata: dict[str, Any] | None = None,
    ) -> "AuditEntry":
        return AuditEntry(
            id=generate_id(),
            timestamp=datetime.now(timezone.utc),
            actor_id=actor_id,
            actor_type=actor_type,
            actor_username=actor_username,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_parent_id=entity_parent_id,
            operation=operation,
            field=field,
            old_value=old_value,
            new_value=new_value,
            module=module,
            tenant_id=tenant_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            request_id=request_id,
            source=source,
            severity=severity,
            compliance_tag=compliance_tag,
            metadata=metadata or {},
        )


__all__ = ["AuditLogEntry", "AuditEntry"]
