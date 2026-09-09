from __future__ import annotations

import os
from types import SimpleNamespace
from typing import TYPE_CHECKING

from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_PLATFORM,
    RoleBindingPlatformScope,
)
from src.core.platform.common.exceptions import BusinessRuleError

from .default_seed_service import (
    ensure_auth_policy_definitions,
    ensure_auth_policy_defaults,
    resolve_bootstrap_admin_password,
)
from .registration_service import _register_bootstrap_user
from src.core.platform.application.security.authorization.roles.role_binding_mutation_participant import (
    create_role_binding_using,
)

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount

    from src.core.platform.application.security.auth.auth_service import AuthService


def bootstrap_policy_catalog(service: AuthService) -> None:
    """Initialize definitions without mutating reviewed role permissions. Deliberately its own
    transaction, separate from `bootstrap_defaults` below: both are independently idempotent, so
    a crash between the two self-heals on the next startup with no duplicate-insert or
    partial-account risk. Do not merge them into one transaction."""
    with service._uow() as uow:
        ensure_auth_policy_definitions(service)
        uow.commit()


def bootstrap_defaults(service: AuthService) -> UserAccount:
    with service._uow() as uow:
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
                uow=uow,
            )
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
                # A real, actual repair (the admin account already exists but is missing its
                # RoleBinding row) -- records the exact fact for the change that actually
                # happened (a new RoleBinding), never a fabricated "account created" fact.
                create_role_binding_using(
                    role_bindings_repo=service._role_binding_repo,
                    audit_repo=service._security_audit_repo,
                    clock=service._clock,
                    record_event=uow.record_event,
                    principal_id=admin.id,
                    role_id=admin_role.id,
                    tenant_id=None,
                    scope_type=ROLE_SCOPE_PLATFORM,
                    scope_id=None,
                    domain_scope=RoleBindingPlatformScope(),
                    actor=SimpleNamespace(user_id=None, username="local_startup"),
                    audit_action="bootstrap.admin_role.repair",
                )
        uow.commit()
    return admin


__all__ = ["bootstrap_defaults", "bootstrap_policy_catalog"]
