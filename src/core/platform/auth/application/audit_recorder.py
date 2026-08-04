from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.common.exceptions import BusinessRuleError

if TYPE_CHECKING:
    from .auth_service import AuthService


def add_atomic_auth_event(
    service: AuthService,
    *,
    action: str,
    username: str,
    user_id: str | None,
    outcome: str,
    details: dict[str, object],
    tenant_id: str | None = None,
    organization_id: str | None = None,
    entity_id: str | None = None,
) -> None:
    audit_repo = service._security_audit_repo
    if audit_repo is None:
        raise BusinessRuleError(
            "Authentication audit persistence is required.",
            code="AUTH_AUDIT_REQUIRED",
        )
    normalized_username = str(username or "").strip().lower()[:255] or "unknown"
    normalized_tenant_id = str(tenant_id or "").strip() or None
    normalized_organization_id = None
    if normalized_tenant_id is not None:
        normalized_organization_id = (
            str(organization_id or "").strip() or None
        )
    entry = AuditEntry.create(
        operation=action,
        entity_type="auth_session",
        entity_id=(
            str(entity_id or "").strip()
            or str(user_id or "").strip()
            or normalized_username
        ),
        entity_parent_id=normalized_tenant_id,
        module="auth",
        actor_id=str(user_id or "").strip() or None,
        actor_type="authentication_subject",
        actor_username=normalized_username,
        tenant_id=normalized_tenant_id,
        organization_id=normalized_organization_id,
        source="auth",
        severity=_severity_for_action(action),
        compliance_tag="SOC2",
        metadata={
            **dict(details),
            "action": action,
            "outcome": str(outcome or "").strip().lower() or "unknown",
        },
    )
    if normalized_tenant_id is None:
        audit_repo.add_platform(entry)
    else:
        audit_repo.add_for_tenant(entry, normalized_tenant_id)


def _severity_for_action(action: str) -> str:
    if "fail" in action or "block" in action or "deny" in action:
        return "high"
    if "logout" in action or "revoke" in action or "expire" in action:
        return "medium"
    return "low"


__all__ = ["add_atomic_auth_event"]
