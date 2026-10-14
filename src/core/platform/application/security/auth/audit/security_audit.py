from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.domain.security.auth.session import UserSessionContext

if TYPE_CHECKING:
    from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
        TargetUserAuthorization,
    )
    from src.core.platform.application.tenant.tenancy.tenant_context import (
        TenantContextService,
    )
    from src.core.platform.contract.repositories.history.audit.contracts import (
        AuditRepository,
    )


class SecurityAuditRecorder:
    """Writes Auth security audit entries inside the caller's transaction: actor
    operations, system (bootstrap) operations, and authentication events."""

    def __init__(
        self,
        *,
        security_audit_repo: AuditRepository | None,
        tenant_context_service: TenantContextService | None,
        user_session: UserSessionContext | None,
        target_users: TargetUserAuthorization,
    ) -> None:
        self._security_audit_repo = security_audit_repo
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._target_users = target_users

    def add_atomic_security_audit(
        self,
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
        audit_repo = self._security_audit_repo
        if audit_repo is None:
            raise BusinessRuleError(
                "Security audit persistence is required for this operation.",
                code="SECURITY_AUDIT_REQUIRED",
            )
        principal = (
            self._user_session.principal
            if self._user_session is not None
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
        if self._tenant_context_service is not None:
            tenant_id = (
                str(
                    self._tenant_context_service.get_active_tenant_id() or ""
                ).strip()
                or None
            )
            organization_id = (
                str(
                    self._tenant_context_service.get_active_organization_id()
                    or ""
                ).strip()
                or None
            )
        platform_operator = self._target_users.is_platform_operator()
        if requested_tenant_id is not None and requested_tenant_id != tenant_id:
            if not platform_operator:
                raise BusinessRuleError(
                    "Requested security audit scope does not match the active tenant.",
                    code="SECURITY_AUDIT_SCOPE_MISMATCH",
                )
            tenant_id = requested_tenant_id
            organization_id = None
        elif tenant_id is not None:
            tenant_id = self._target_users.require_actor_active_tenant(
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
            changed_fields=(
                {field: {"before": old_value, "after": new_value}} if field else None
            ),
            tenant_id=tenant_id,
            organization_id=organization_id,
            source="auth",
            severity=severity,
            category="SECURITY",
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
        self,
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
        audit_repo = self._security_audit_repo
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
                changed_fields=(
                    {field: {"before": old_value, "after": new_value}} if field else None
                ),
                source=source,
                severity=severity,
                category="SECURITY",
                metadata={
                    **dict(metadata or {}),
                    "action": action,
                    "outcome": "success",
                },
            )
        )

    def add_atomic_auth_event(
        self,
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
        audit_repo = self._security_audit_repo
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
            category="SECURITY",
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


__all__ = ["SecurityAuditRecorder"]
