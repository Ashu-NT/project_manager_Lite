from __future__ import annotations

import logging
import os

from src.core.platform.application.security.authorization.roles.role_scope_policy import (
    is_platform_role,
    system_role_scope_type,
)
from src.core.platform.domain.security.auth import (
    Permission,
    Role,
    RolePermissionBinding,
)
from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLE_PERMISSIONS,
)

logger = logging.getLogger(__name__)


def truthy_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def resolve_bootstrap_admin_password() -> str:
    from src.core.platform.common.exceptions import ValidationError

    configured = os.getenv("PM_ADMIN_PASSWORD")
    if configured is not None and configured.strip():
        return configured.strip()
    if not truthy_env(os.getenv("PM_ALLOW_DEFAULT_ADMIN_PASSWORD")):
        raise ValidationError("PM_ADMIN_PASSWORD must be set")
    default_password = "ChangeMe123!"
    logger.warning(
        "=================================================================\n"
        "  FIRST-RUN SETUP: Admin account created with default credentials\n"
        "  Username : admin\n"
        "  Password : %s\n"
        "  You will be prompted to change this password after signing in.\n"
        "  Set PM_ADMIN_PASSWORD in your environment to use a custom value.\n"
        "=================================================================",
        default_password,
    )
    return default_password
from sqlalchemy.orm import Session

from src.core.platform.contract.repositories.security.auth import (
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
)


class AuthPolicySeeder:
    """Idempotently seeds the default permission, role and role-permission catalog."""

    def __init__(
        self,
        *,
        session: Session,
        role_repo: RoleRepository,
        permission_repo: PermissionRepository,
        role_permission_repo: RolePermissionRepository,
    ) -> None:
        self._session = session
        self._role_repo = role_repo
        self._permission_repo = permission_repo
        self._role_permission_repo = role_permission_repo

    def ensure_default_permissions(self) -> None:
        for code, description in DEFAULT_PERMISSIONS.items():
            if self._permission_repo.get_by_code(code) is None:
                self._permission_repo.add(Permission.create(code=code, description=description))

    def ensure_default_roles(self) -> dict[str, Role]:
        roles: dict[str, Role] = {}
        for role_name in DEFAULT_ROLE_PERMISSIONS:
            role = self._role_repo.get_by_name(role_name)
            if role is None:
                role = Role.create(
                    name=role_name,
                    description=f"System role: {role_name}",
                    is_system=True,
                    allowed_scope_type=system_role_scope_type(role_name),
                    is_assignable=not is_platform_role(role_name),
                )
                self._role_repo.add(role)
            roles[role_name] = role
        return roles

    def ensure_role_permissions(self, role_map: dict[str, Role]) -> None:
        permission_map = {p.code: p.id for p in self._permission_repo.list_all()}
        for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
            role = role_map.get(role_name)
            if not role:
                continue
            for code in permission_codes:
                permission_id = permission_map.get(code)
                if not permission_id:
                    continue
                if not self._role_permission_repo.exists(role.id, permission_id):
                    self._role_permission_repo.add(
                        RolePermissionBinding.create(role_id=role.id, permission_id=permission_id)
                    )

    def ensure_auth_policy_definitions(self) -> dict[str, Role]:
        self.ensure_default_permissions()
        self._session.flush()
        role_map = self.ensure_default_roles()
        self._session.flush()
        return role_map

    def ensure_auth_policy_defaults(self) -> dict[str, Role]:
        """Seed complete policy only for explicit local/bootstrap workflows."""
        role_map = self.ensure_auth_policy_definitions()
        self.ensure_role_permissions(role_map)
        self._session.flush()
        return role_map


__all__ = ["AuthPolicySeeder"]
