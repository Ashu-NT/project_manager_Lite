from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.common.exceptions import BusinessRuleError

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth.session import UserSessionPrincipal

    from src.core.platform.application.security.auth.auth_service import AuthService

logger = logging.getLogger(__name__)

_SWITCH_TYPES = frozenset({"tenant", "organization"})


def commit_context_switch(
    service: AuthService,
    target_principal: UserSessionPrincipal,
    *,
    switch_type: str,
) -> None:
    user_session = service._user_session
    current_principal = user_session.principal if user_session is not None else None
    if user_session is None or current_principal is None:
        raise BusinessRuleError(
            "Authentication is required to switch context.",
            code="AUTHENTICATION_REQUIRED",
        )

    normalized_switch_type = str(switch_type or "").strip().lower()
    if normalized_switch_type not in _SWITCH_TYPES:
        raise BusinessRuleError(
            "Context switch type is invalid.",
            code="CONTEXT_SWITCH_TYPE_INVALID",
        )
    if target_principal.user_id != current_principal.user_id:
        raise BusinessRuleError(
            "Context authority cannot be transferred between users.",
            code="CONTEXT_SWITCH_PRINCIPAL_MISMATCH",
        )

    old_tenant_id = _clean_optional(current_principal.active_tenant_id)
    old_organization_id = _clean_optional(
        current_principal.active_organization_id
    )
    new_tenant_id = _clean_optional(target_principal.active_tenant_id)
    new_organization_id = _clean_optional(
        target_principal.active_organization_id
    )
    if new_tenant_id is None:
        raise BusinessRuleError(
            "A validated tenant is required for context switching.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    if (
        normalized_switch_type == "organization"
        and old_tenant_id != new_tenant_id
    ):
        raise BusinessRuleError(
            "Organization switching cannot change the active tenant.",
            code="ORGANIZATION_TENANT_MISMATCH",
        )

    if (
        old_tenant_id == new_tenant_id
        and old_organization_id == new_organization_id
    ):
        user_session.set_principal(target_principal)
        return

    occurred_at = datetime.now(timezone.utc)
    try:
        _stage_persisted_session_context(
            service,
            target_principal,
            tenant_id=new_tenant_id,
            organization_id=new_organization_id,
            occurred_at=occurred_at,
        )
        _add_context_switch_audit(
            service,
            current_principal=current_principal,
            target_principal=target_principal,
            switch_type=normalized_switch_type,
            old_tenant_id=old_tenant_id,
            old_organization_id=old_organization_id,
            new_tenant_id=new_tenant_id,
            new_organization_id=new_organization_id,
        )
        service._session.commit()
    except Exception as exc:
        service._session.rollback()
        logger.exception(
            "Context switch rolled back switch_type=%s actor_user_id=%s "
            "target_tenant_id=%s target_organization_id=%s",
            normalized_switch_type,
            current_principal.user_id,
            new_tenant_id,
            new_organization_id,
        )
        raise BusinessRuleError(
            "Context could not be changed securely. Please try again.",
            code="CONTEXT_SWITCH_AUDIT_UNAVAILABLE",
        ) from exc

    user_session.set_principal(target_principal)


def _stage_persisted_session_context(
    service: AuthService,
    target_principal: UserSessionPrincipal,
    *,
    tenant_id: str,
    organization_id: str | None,
    occurred_at: datetime,
) -> None:
    session_id = _clean_optional(target_principal.session_id)
    if service._auth_session_repo is None or session_id is None:
        return
    auth_session = service._auth_session_repo.get(session_id)
    if (
        auth_session is None
        or auth_session.user_id != target_principal.user_id
        or auth_session.revoked_at is not None
    ):
        raise BusinessRuleError(
            "The authenticated session is no longer available.",
            code="AUTH_SESSION_INVALID",
        )
    auth_session.last_active_tenant_id = tenant_id
    auth_session.last_active_organization_id = organization_id
    auth_session.updated_at = occurred_at
    service._auth_session_repo.update(auth_session)


def _add_context_switch_audit(
    service: AuthService,
    *,
    current_principal: UserSessionPrincipal,
    target_principal: UserSessionPrincipal,
    switch_type: str,
    old_tenant_id: str | None,
    old_organization_id: str | None,
    new_tenant_id: str,
    new_organization_id: str | None,
) -> None:
    audit_repo = service._security_audit_repo
    if audit_repo is None:
        raise BusinessRuleError(
            "Security audit persistence is required for context switching.",
            code="SECURITY_AUDIT_REQUIRED",
        )
    session_id = _clean_optional(target_principal.session_id)
    action = f"auth.context.{switch_type}.switched"
    field = "tenant_id" if switch_type == "tenant" else "organization_id"
    old_value = old_tenant_id if switch_type == "tenant" else old_organization_id
    new_value = new_tenant_id if switch_type == "tenant" else new_organization_id
    entry = AuditEntry.create(
        operation=action,
        entity_type="auth_session",
        entity_id=session_id or current_principal.user_id,
        entity_parent_id=new_tenant_id,
        module="auth",
        actor_id=current_principal.user_id,
        actor_username=str(current_principal.username or "").strip()[:128] or None,
        tenant_id=new_tenant_id,
        organization_id=new_organization_id,
        request_id=_current_request_id(service),
        source="auth",
        severity="medium",
        compliance_tag="SOC2",
        field=field,
        old_value=old_value,
        new_value=new_value,
        metadata={
            "action": action,
            "outcome": "success",
            "switch_type": switch_type,
            "old_tenant_id": old_tenant_id,
            "old_organization_id": old_organization_id,
            "new_tenant_id": new_tenant_id,
            "new_organization_id": new_organization_id,
        },
    )
    audit_repo.add_for_tenant(entry, new_tenant_id)


def _current_request_id(service: AuthService) -> str | None:
    provider = service._request_id_provider
    if provider is None:
        return None
    try:
        return _clean_optional(provider())
    except Exception:
        return None


def _clean_optional(value: object) -> str | None:
    return str(value or "").strip()[:255] or None


__all__ = ["commit_context_switch"]
