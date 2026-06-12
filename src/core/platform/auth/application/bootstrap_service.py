from __future__ import annotations

import os
from typing import TYPE_CHECKING

from src.core.platform.auth.domain import UserRoleBinding

from .default_seed_service import (
    ensure_default_permissions,
    ensure_default_roles,
    ensure_role_permissions,
    resolve_bootstrap_admin_password,
)

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount

    from .auth_service import AuthService


def bootstrap_defaults(service: AuthService) -> UserAccount:
    ensure_default_permissions(service)
    service._session.flush()
    role_map = ensure_default_roles(service)
    service._session.flush()
    ensure_role_permissions(service, role_map)
    service._session.flush()

    admin_username = (os.getenv("PM_ADMIN_USERNAME", "admin").strip() or "admin").lower()
    admin = service._user_repo.get_by_username(admin_username)
    if admin is None:
        admin_password = resolve_bootstrap_admin_password()
        admin = service.register_user(
            username=admin_username,
            raw_password=admin_password,
            display_name="Administrator",
            role_names=["admin"],
            must_change_password=True,
            commit=False,
            bypass_permission=True,
        )
    else:
        admin_role = role_map.get("admin")
        if admin_role and not service._user_role_repo.exists(admin.id, admin_role.id):
            service._user_role_repo.add(UserRoleBinding.create(user_id=admin.id, role_id=admin_role.id))

    service._session.commit()
    return admin


__all__ = ["bootstrap_defaults"]
