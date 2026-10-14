from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    authorization_denied,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth.session import UserSessionContext

if TYPE_CHECKING:
    from src.core.platform.application.tenant.tenancy.tenant_context import (
        TenantContextService,
    )
    from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
        UserTenantMembershipRepository,
    )


class TargetUserAuthorization:
    """Checks that an account operation's actor and target user sit inside the
    actor's active tenant, with the platform-operator exemption."""

    def __init__(
        self,
        *,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
        user_tenant_repo: UserTenantMembershipRepository | None,
    ) -> None:
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._user_tenant_repo = user_tenant_repo

    def _current_principal(self):
        if self._user_session is None or self._user_session.principal is None:
            raise BusinessRuleError(
                "Authentication is required for this account operation.",
                code="AUTHENTICATION_REQUIRED",
            )
        return self._user_session.principal

    def is_platform_operator(self) -> bool:
        principal = self._current_principal()
        return (
            "admin" in principal.role_names
            and "platform.admin" in principal.permissions
        )

    def require_self_target(
        self,
        target_user_id: str,
        *,
        operation_label: str,
    ) -> None:
        principal = self._current_principal()
        if principal.user_id != str(target_user_id or "").strip():
            authorization_denied(
                self._user_session,
                message=f"{operation_label.capitalize()} is restricted to the authenticated user.",
                code="AUTH_SELF_SERVICE_REQUIRED",
                operation_label=operation_label,
                target_scope_type="user",
                target_scope_id=target_user_id,
                operation="authorization.target.denied",
            )

    def require_actor_active_tenant(
        self,
        *,
        operation_label: str,
    ) -> str:
        principal = self._current_principal()
        if self._user_session is None:
            authorization_denied(
                self._user_session,
                message="Authentication context is not configured.",
                code="AUTHORIZATION_CONTEXT_REQUIRED",
                operation_label=operation_label,
                operation="authorization.infrastructure.denied",
            )
        active_tenant_id = str(
            self._user_session.active_tenant_id() or ""
        ).strip()
        if not active_tenant_id:
            authorization_denied(
                self._user_session,
                message=f"Active tenant context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
                operation_label=operation_label,
                target_scope_type="tenant",
                operation="authorization.context.denied",
            )
        if self._tenant_context_service is None:
            authorization_denied(
                self._user_session,
                message="Tenant context authorization is not configured.",
                code="AUTHORIZATION_CONTEXT_REQUIRED",
                operation_label=operation_label,
                target_scope_type="tenant",
                target_scope_id=active_tenant_id,
                operation="authorization.infrastructure.denied",
            )
        validated_tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label=operation_label,
        )
        if validated_tenant_id != active_tenant_id:
            authorization_denied(
                self._user_session,
                message="The selected tenant context is inconsistent.",
                code="TENANT_CONTEXT_MISMATCH",
                operation_label=operation_label,
                target_scope_type="tenant",
                target_scope_id=active_tenant_id,
                operation="authorization.context.denied",
            )
        if self._user_tenant_repo is None:
            authorization_denied(
                self._user_session,
                message="Tenant membership authorization is not configured.",
                code="AUTHORIZATION_CONTEXT_REQUIRED",
                operation_label=operation_label,
                target_scope_type="tenant",
                target_scope_id=active_tenant_id,
                operation="authorization.infrastructure.denied",
            )
        if (
            not self.is_platform_operator()
            and not self._user_tenant_repo.is_active_member(
                principal.user_id,
                active_tenant_id,
            )
        ):
            authorization_denied(
                self._user_session,
                message="The authenticated user is not an active member of the selected tenant.",
                code="TENANT_ACCESS_DENIED",
                operation_label=operation_label,
                target_scope_type="tenant",
                target_scope_id=active_tenant_id,
                operation="authorization.membership.denied",
            )
        return active_tenant_id

    def require_target_user_in_customer_tenant(
        self,
        target_user_id: str,
        *,
        operation_label: str,
        denial_code: str = "USER_CROSS_TENANT_DENIED",
    ) -> str:
        active_tenant_id = self.require_actor_active_tenant(
            operation_label=operation_label,
        )
        # require_actor_active_tenant has already denied a missing membership repo.
        if self._user_tenant_repo is None or not self._user_tenant_repo.is_active_member(
            str(target_user_id or "").strip(),
            active_tenant_id,
        ):
            authorization_denied(
                self._user_session,
                message=f"Cannot {operation_label} for a user outside the active tenant.",
                code=denial_code,
                operation_label=operation_label,
                target_scope_type="user",
                target_scope_id=target_user_id,
                operation="authorization.membership.denied",
            )
        return active_tenant_id

    def require_target_user_in_active_tenant(
        self,
        target_user_id: str,
        *,
        operation_label: str,
        denial_code: str = "USER_CROSS_TENANT_DENIED",
    ) -> str:
        principal = self._current_principal()
        if self.is_platform_operator():
            return ""
        if self._user_tenant_repo is None:
            authorization_denied(
                self._user_session,
                message="Tenant membership authorization is not configured.",
                code="AUTHORIZATION_CONTEXT_REQUIRED",
                operation_label=operation_label,
                operation="authorization.infrastructure.denied",
            )
        # _current_principal above guarantees a session.
        session_tenant_id = self._user_session.active_tenant_id() if self._user_session else None
        active_tenant_id = str(session_tenant_id or "").strip() or None
        if active_tenant_id is None:
            authorization_denied(
                self._user_session,
                message=f"Active tenant context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
                operation_label=operation_label,
                target_scope_type="tenant",
                operation="authorization.context.denied",
            )
        if not self._user_tenant_repo.is_active_member(
            principal.user_id,
            active_tenant_id,
        ):
            authorization_denied(
                self._user_session,
                message="The authenticated user is not an active member of the selected tenant.",
                code="TENANT_ACCESS_DENIED",
                operation_label=operation_label,
                target_scope_type="tenant",
                target_scope_id=active_tenant_id,
                operation="authorization.membership.denied",
            )
        if not self._user_tenant_repo.is_active_member(
            str(target_user_id or "").strip(),
            active_tenant_id,
        ):
            authorization_denied(
                self._user_session,
                message=f"Cannot {operation_label} for a user outside the active tenant.",
                code=denial_code,
                operation_label=operation_label,
                target_scope_type="user",
                target_scope_id=target_user_id,
                operation="authorization.membership.denied",
            )
        return active_tenant_id


__all__ = ["TargetUserAuthorization"]
