from __future__ import annotations

import os
from typing import TYPE_CHECKING

from src.core.shared.events.domain_events import domain_events
from src.core.platform.domain.security.authorization.roles import ROLE_SCOPE_PLATFORM, RoleBinding
from src.core.platform.common.exceptions import BusinessRuleError

from .default_seed_service import (
    ensure_auth_policy_definitions,
    ensure_auth_policy_defaults,
    resolve_bootstrap_admin_password,
)
from .registration_service import _register_bootstrap_user
from src.core.platform.application.security.auth.audit.security_audit import add_atomic_system_security_audit

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount

    from src.core.platform.application.security.auth.auth_service import AuthService


def bootstrap_policy_catalog(service: AuthService) -> None:
    """Initialize definitions without mutating reviewed role permissions."""
    ensure_auth_policy_definitions(service)
    service._session.commit()


def bootstrap_defaults(service: AuthService) -> UserAccount:
    authority_changed = False
    try:
        role_map = ensure_auth_policy_defaults(service)

        admin_username = (
            os.getenv("PM_ADMIN_USERNAME", "admin").strip() or "admin"
        ).lower()
        admin = service._user_repo.get_by_username(admin_username)
        if admin is None:
            admin_password = resolve_bootstrap_admin_password()
            admin = _register_bootstrap_user(
                service,
                username=admin_username,
                raw_password=admin_password,
                display_name="Administrator",
                role_names=["admin"],
                must_change_password=True,
                commit=False,
            )
            authority_changed = True
        else:
            admin_role = role_map.get("admin")
            if admin_role and service._role_binding_repo is None:
                raise BusinessRuleError(
                    "Canonical role-binding persistence is not configured.",
                    code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
                )
            existing_admin_binding = (
                service._role_binding_repo.get_active_for_assignment(
                    principal_id=admin.id,
                    role_id=admin_role.id,
                    tenant_id=None,
                    actual_scope_type=ROLE_SCOPE_PLATFORM,
                    actual_scope_id=None,
                )
                if admin_role is not None
                else None
            )
            if admin_role and existing_admin_binding is None:
                service._role_binding_repo.add(
                    RoleBinding.create(
                        principal_id=admin.id,
                        role_id=admin_role.id,
                        actual_scope_type=ROLE_SCOPE_PLATFORM,
                    )
                )
                add_atomic_system_security_audit(
                    service,
                    operation="permission_change",
                    entity_type="role_binding",
                    entity_id=admin.id,
                    action="bootstrap.admin_role.repair",
                    severity="critical",
                    actor_username="local_startup",
                    field="role",
                    new_value=admin_role.name,
                    metadata={
                        "target_user_id": admin.id,
                        "role_name": admin_role.name,
                    },
                )
                authority_changed = True

        service._session.commit()
    except Exception:
        service._session.rollback()
        raise
    if authority_changed:
        domain_events.auth_changed.emit(admin.id)
    return admin


__all__ = ["bootstrap_defaults", "bootstrap_policy_catalog"]
