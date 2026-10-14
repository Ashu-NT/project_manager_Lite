from __future__ import annotations

from src.core.platform.application.security.auth.queries.auth_queries import (
    AuthQueryHandler,
)
from src.core.platform.application.security.auth.session.session_lifecycle import (
    AuthSessionLifecycle,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    authorization_denied,
    require_permission,
)
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    TargetUserAuthorization,
)
from src.core.platform.application.security.authorization.roles.commands.role_governance import (
    RoleGovernanceCommandHandler,
)
from src.core.platform.application.security.authorization.roles.role_scope_policy import (
    EXPLICIT_SCOPE_ROLE_NAMES,
    PLATFORM_ROLE_NAMES,
    normalize_role_name,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.contract.repositories.security.auth import RoleBindingRepository
from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    UserTenantMembershipRepository,
)
from src.core.platform.domain.security.auth import UserAccount
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
)


class RoleAssignmentHandler:
    """Assigns and revokes platform and customer roles through canonical role governance."""

    def __init__(
        self,
        *,
        auth_queries: AuthQueryHandler,
        role_binding_repo: RoleBindingRepository,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService,
        user_tenant_repo: UserTenantMembershipRepository | None,
        target_users: TargetUserAuthorization,
        lifecycle: AuthSessionLifecycle,
        role_governance_commands: RoleGovernanceCommandHandler,
    ) -> None:
        self._auth_queries = auth_queries
        self._role_binding_repo = role_binding_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._user_tenant_repo = user_tenant_repo
        self._target_users = target_users
        self._lifecycle = lifecycle
        self._role_governance_commands = role_governance_commands

    def _require_canonical_target_membership(
        self,
        target_user_id: str,
        *,
        tenant_id: str,
        operation: str,
    ) -> None:
        if (
            self._user_tenant_repo is not None
            and self._user_tenant_repo.is_active_member(
                target_user_id,
                tenant_id,
            )
        ):
            return
        authorization_denied(
            self._user_session,
            message="The user is not an active member of the selected tenant.",
            code="ROLE_TARGET_TENANT_DENIED",
            operation_label=f"{operation} a canonical tenant role",
            target_scope_type="user",
            target_scope_id=target_user_id,
            operation="authorization.membership.denied",
        )

    def assign_role(self, user_id: str, role_name: str) -> UserAccount:
        require_permission(self._user_session, "auth.manage", operation_label="assign role")
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="assign role"
        )
        role = self._auth_queries.require_tenant_role_by_name(tenant_id, role_name)
        if role.allowed_scope_type == ROLE_SCOPE_PLATFORM:
            authorization_denied(
                self._user_session,
                message="Platform roles require the dedicated provisioning workflow.",
                code="PLATFORM_ROLE_ASSIGNMENT_DENIED",
                operation_label="assign a platform role",
                target_scope_type="role",
                target_scope_id=role.id,
                operation="authorization.platform_role.denied",
            )
        if role.allowed_scope_type != ROLE_SCOPE_TENANT:
            authorization_denied(
                self._user_session,
                message=(
                    f"Role '{role.name}' requires an explicit "
                    f"{role.allowed_scope_type} scope."
                ),
                code="ROLE_SCOPE_REQUIRED",
                operation_label="assign a scoped role",
                target_scope_type="role",
                target_scope_id=role.id,
                operation="authorization.resource_scope.denied",
            )
        user = self._auth_queries.require_user(user_id)
        self._require_canonical_target_membership(
            user.id,
            tenant_id=tenant_id,
            operation="assign",
        )
        self._role_governance_commands.assign_role(
            target_user_id=user.id,
            role_id=role.id,
        )
        self._lifecycle.refresh_current_session_if_user(user.id)
        return user

    def revoke_role(self, user_id: str, role_name: str) -> UserAccount:
        require_permission(self._user_session, "auth.manage", operation_label="revoke role")
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="revoke role"
        )
        role = self._auth_queries.require_tenant_role_by_name(tenant_id, role_name)
        if role.allowed_scope_type == ROLE_SCOPE_PLATFORM:
            authorization_denied(
                self._user_session,
                message="Platform roles require the dedicated provisioning workflow.",
                code="PLATFORM_ROLE_ASSIGNMENT_DENIED",
                operation_label="revoke a platform role",
                target_scope_type="role",
                target_scope_id=role.id,
                operation="authorization.platform_role.denied",
            )
        if role.allowed_scope_type != ROLE_SCOPE_TENANT:
            authorization_denied(
                self._user_session,
                message=(
                    f"Role '{role.name}' requires an explicit "
                    f"{role.allowed_scope_type} scope."
                ),
                code="ROLE_SCOPE_REQUIRED",
                operation_label="revoke a scoped role",
                target_scope_type="role",
                target_scope_id=role.id,
                operation="authorization.resource_scope.denied",
            )
        user = self._auth_queries.require_user(user_id)
        self._require_canonical_target_membership(
            user.id,
            tenant_id=tenant_id,
            operation="revoke",
        )
        binding = self._role_binding_repo.get_active_for_assignment(
            principal_id=user.id,
            role_id=role.id,
            tenant_id=tenant_id,
            actual_scope_type=ROLE_SCOPE_TENANT,
            actual_scope_id=None,
        )
        if binding is not None:
            self._role_governance_commands.revoke_role_binding(
                binding.id
            )
        self._lifecycle.refresh_current_session_if_user(user.id)
        return user

    def _require_customer_assignable_role(
        self,
        role_name: str,
    ) -> str:
        normalized = normalize_role_name(role_name)
        if normalized in PLATFORM_ROLE_NAMES:
            authorization_denied(
                self._user_session,
                message=(
                    f"Platform role '{normalized}' cannot be managed through a "
                    "customer tenant."
                ),
                code="PLATFORM_ROLE_ASSIGNMENT_DENIED",
                operation_label="manage a customer tenant role",
                target_scope_type="role",
                target_scope_id=normalized,
                operation="authorization.permission_ceiling.denied",
            )
        if normalized in EXPLICIT_SCOPE_ROLE_NAMES:
            authorization_denied(
                self._user_session,
                message=f"Role '{normalized}' requires an explicit organization scope.",
                code="ROLE_SCOPE_REQUIRED",
                operation_label="manage a customer tenant role",
                target_scope_type="role",
                target_scope_id=normalized,
                operation="authorization.resource_scope.denied",
            )
        return normalized

    def assign_customer_role(self, user_id: str, role_name: str) -> UserAccount:
        require_permission(
            self._user_session,
            "auth.manage",
            operation_label="assign tenant role",
        )
        self._target_users.require_target_user_in_customer_tenant(
            user_id,
            operation_label="assign a tenant role",
            denial_code="ROLE_CROSS_TENANT_DENIED",
        )
        return self.assign_role(user_id, self._require_customer_assignable_role(role_name))

    def revoke_customer_role(self, user_id: str, role_name: str) -> UserAccount:
        require_permission(
            self._user_session,
            "auth.manage",
            operation_label="revoke tenant role",
        )
        self._target_users.require_target_user_in_customer_tenant(
            user_id,
            operation_label="revoke a tenant role",
            denial_code="ROLE_CROSS_TENANT_DENIED",
        )
        return self.revoke_role(user_id, self._require_customer_assignable_role(role_name))


__all__ = ["RoleAssignmentHandler"]
