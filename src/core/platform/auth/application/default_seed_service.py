from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from src.core.platform.auth.domain import Permission, Role, RolePermissionBinding
from src.core.platform.auth.policy import DEFAULT_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS

if TYPE_CHECKING:
    from .auth_service import AuthService

logger = logging.getLogger(__name__)


def truthy_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def resolve_bootstrap_admin_password() -> str:
    configured = os.getenv("PM_ADMIN_PASSWORD")
    if configured is not None and configured.strip():
        return configured.strip()
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


def ensure_default_permissions(service: AuthService) -> None:
    for code, description in DEFAULT_PERMISSIONS.items():
        if service._permission_repo.get_by_code(code) is None:
            service._permission_repo.add(Permission.create(code=code, description=description))


def ensure_default_roles(service: AuthService) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for role_name in DEFAULT_ROLE_PERMISSIONS:
        role = service._role_repo.get_by_name(role_name)
        if role is None:
            role = Role.create(name=role_name, description=f"System role: {role_name}", is_system=True)
            service._role_repo.add(role)
        roles[role_name] = role
    return roles


def ensure_role_permissions(service: AuthService, role_map: dict[str, Role]) -> None:
    permission_map = {p.code: p.id for p in service._permission_repo.list_all()}
    for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
        role = role_map.get(role_name)
        if not role:
            continue
        for code in permission_codes:
            permission_id = permission_map.get(code)
            if not permission_id:
                continue
            if not service._role_permission_repo.exists(role.id, permission_id):
                service._role_permission_repo.add(
                    RolePermissionBinding.create(role_id=role.id, permission_id=permission_id)
                )


__all__ = [
    "ensure_default_permissions",
    "ensure_default_roles",
    "ensure_role_permissions",
    "resolve_bootstrap_admin_password",
    "truthy_env",
]
