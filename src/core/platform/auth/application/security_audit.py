from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.common.exceptions import BusinessRuleError

from .target_user_authorization import (
    is_platform_operator,
    require_actor_active_tenant,
)

if TYPE_CHECKING:
    from .auth_service import AuthService


def add_atomic_security_audit(
    service: AuthService,
    *,
    operation: str,
    entity_type: str,
    entity_id: str,
    action: str,
    severity: str,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    metadata: dict[str, object] | None = None,
    scope_tenant_id: str | None = None,
) -> None:
    audit_repo = service._security_audit_repo
    if audit_repo is None:
        raise BusinessRuleError(
            "Security audit persistence is required for this operation.",
            code="SECURITY_AUDIT_REQUIRED",
        )
    principal = (
        service._user_session.principal
        if service._user_session is not None
        else None
    )
    if principal is None:
        raise BusinessRuleError(
            "Authenticated actor context is required for security auditing.",
            code="SECURITY_AUDIT_ACTOR_REQUIRED",
        )

    requested_tenant_id = str(scope_tenant_id or "").strip() or None
    tenant_id: str | None = None
    organization_id: str | None = None
    if service._tenant_context_service is not None:
        tenant_id = (
            str(
                service._tenant_context_service.get_active_tenant_id() or ""
            ).strip()
            or None
        )
        organization_id = (
            str(
                service._tenant_context_service.get_active_organization_id()
                or ""
            ).strip()
            or None
        )
    platform_operator = is_platform_operator(service)
    if requested_tenant_id is not None and requested_tenant_id != tenant_id:
        if not platform_operator:
            raise BusinessRuleError(
                "Requested security audit scope does not match the active tenant.",
                code="SECURITY_AUDIT_SCOPE_MISMATCH",
            )
        tenant_id = requested_tenant_id
        organization_id = None
    elif tenant_id is not None:
        tenant_id = require_actor_active_tenant(
            service,
            operation_label="record security audit",
        )
    if tenant_id is None and not platform_operator:
        raise BusinessRuleError(
            "Tenant scope is required for customer security auditing.",
            code="SECURITY_AUDIT_SCOPE_REQUIRED",
        )

    entry = AuditEntry.create(
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_parent_id=tenant_id,
        module="platform",
        actor_id=principal.user_id,
        actor_username=principal.username,
        field=field,
        old_value=old_value,
        new_value=new_value,
        tenant_id=tenant_id,
        organization_id=organization_id,
        source="auth",
        severity=severity,
        compliance_tag="SOC2",
        metadata={
            **dict(metadata or {}),
            "action": action,
            "outcome": "success",
        },
    )
    if tenant_id is None:
        audit_repo.add_platform(entry)
    else:
        audit_repo.add_for_tenant(entry, tenant_id)


def add_atomic_system_security_audit(
    service: AuthService,
    *,
    operation: str,
    entity_type: str,
    entity_id: str,
    action: str,
    severity: str,
    actor_username: str,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    metadata: dict[str, object] | None = None,
    source: str = "bootstrap",
) -> None:
    audit_repo = service._security_audit_repo
    if audit_repo is None:
        raise BusinessRuleError(
            "Security audit persistence is required for this operation.",
            code="SECURITY_AUDIT_REQUIRED",
        )
    normalized_actor = str(actor_username or "").strip()
    if not normalized_actor:
        raise BusinessRuleError(
            "System audit actor is required.",
            code="SECURITY_AUDIT_ACTOR_REQUIRED",
        )
    audit_repo.add_platform(
        AuditEntry.create(
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            module="platform",
            actor_type="system",
            actor_username=normalized_actor,
            field=field,
            old_value=old_value,
            new_value=new_value,
            source=source,
            severity=severity,
            compliance_tag="SOC2",
            metadata={
                **dict(metadata or {}),
                "action": action,
                "outcome": "success",
            },
        )
    )


__all__ = [
    "add_atomic_security_audit",
    "add_atomic_system_security_audit",
]
