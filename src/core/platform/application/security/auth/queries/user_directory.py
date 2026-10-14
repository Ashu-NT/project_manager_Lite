from __future__ import annotations

from src.core.platform.application.security.auth.queries.auth_queries import (
    AuthQueryHandler,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    TargetUserAuthorization,
)
from src.core.platform.application.security.authorization.roles.role_scope_policy import (
    is_customer_assignable_role,
    is_platform_role,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    PlatformOverviewRollupReader,
)
from src.core.platform.contract.repositories.security.auth import (
    RoleRepository,
    UserRepository,
)
from src.core.platform.domain.security.auth import (
    Role,
    UserAccount,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


class UserDirectoryQueryHandler:
    """Tenant-scoped user and role directory reads for administration screens."""

    def __init__(
        self,
        *,
        auth_queries: AuthQueryHandler,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        user_session: UserSessionContext | None,
        overview_rollup_reader: PlatformOverviewRollupReader | None,
        target_users: TargetUserAuthorization,
    ) -> None:
        self._auth_queries = auth_queries
        self._user_repo = user_repo
        self._role_repo = role_repo
        self._user_session = user_session
        self._overview_rollup_reader = overview_rollup_reader
        self._target_users = target_users

    def list_users(self) -> list[UserAccount]:
        require_any_permission(
            self._user_session,
            ("auth.manage", "auth.read", "access.manage", "security.manage"),
            operation_label="list users",
        )
        if self._target_users.is_platform_operator():
            return self._user_repo.list_all()
        tenant_id = self._target_users.require_actor_active_tenant(
            operation_label="list tenant users",
        )
        return [
            user
            for user in self._user_repo.list_for_tenant(tenant_id)
            if not any(
                is_platform_role(role_name)
                for role_name in self._auth_queries.canonical_platform_authority(
                    user.id
                ).role_names
            )
        ]

    def get_user_rollup_summary(self):
        """Overview-only equivalent of list_users() -- one SQL query instead of one full
        materialization plus, for tenant callers, a per-user platform-role-exclusion N+1. Same
        permission check and platform-operator/tenant-caller branch as list_users(), which the
        paginated Users workspace page keeps calling unchanged."""
        require_any_permission(
            self._user_session,
            ("auth.manage", "auth.read", "access.manage", "security.manage"),
            operation_label="view user rollup summary",
        )
        if self._overview_rollup_reader is None:
            raise BusinessRuleError(
                "Platform overview rollup reader is not configured.",
                code="OVERVIEW_ROLLUP_READER_REQUIRED",
            )
        if self._target_users.is_platform_operator():
            return self._overview_rollup_reader.get_user_summary(tenant_id=None)
        tenant_id = self._target_users.require_actor_active_tenant(
            operation_label="view tenant user rollup summary",
        )
        return self._overview_rollup_reader.get_user_summary(tenant_id=tenant_id)

    def list_roles(self) -> list[Role]:
        require_any_permission(
            self._user_session,
            ("auth.manage", "auth.read"),
            operation_label="list roles",
        )
        if self._target_users.is_platform_operator():
            return self._role_repo.list_all()
        tenant_id = self._target_users.require_actor_active_tenant(
            operation_label="list tenant roles",
        )
        return self._role_repo.list_for_tenant(tenant_id)

    def list_customer_assignable_roles(self) -> list[Role]:
        require_any_permission(
            self._user_session,
            ("auth.manage", "auth.read"),
            operation_label="list tenant-assignable roles",
        )
        tenant_id = self._target_users.require_actor_active_tenant(
            operation_label="list tenant-assignable roles",
        )
        return [
            role
            for role in self._role_repo.list_for_tenant(tenant_id)
            if role.is_system
            and role.status == "active"
            and role.is_assignable
            and role.allowed_scope_type == "tenant"
            and is_customer_assignable_role(role.name)
        ]


__all__ = ["UserDirectoryQueryHandler"]
