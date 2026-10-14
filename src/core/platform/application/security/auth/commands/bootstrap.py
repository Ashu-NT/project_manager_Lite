from __future__ import annotations

import os
from types import SimpleNamespace
from typing import TYPE_CHECKING

from src.core.platform.application.security.auth.auth_transaction_scope import (
    AuthTransactionScope,
)
from src.core.platform.application.security.auth.commands.registration import (
    UserRegistrationHandler,
)
from src.core.platform.application.security.auth.provisioning.default_seed_service import (
    AuthPolicySeeder,
    resolve_bootstrap_admin_password,
)
from src.core.platform.application.security.authorization.roles.role_binding_mutation_participant import (
    create_role_binding_using,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.repositories.history.audit.contracts import (
    AuditRepository,
)
from src.core.platform.contract.repositories.security.auth import (
    RoleBindingRepository,
    UserRepository,
)
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_PLATFORM,
    RoleBindingPlatformScope,
)
from src.core.shared.time.clock import Clock

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount


class AuthBootstrapHandler:
    """First-run bootstrap: seeds the policy catalog and the default administrator."""

    def __init__(
        self,
        *,
        tx: AuthTransactionScope,
        clock: Clock,
        user_repo: UserRepository,
        role_binding_repo: RoleBindingRepository | None,
        security_audit_repo: AuditRepository | None,
        seeder: AuthPolicySeeder,
        registration: UserRegistrationHandler,
    ) -> None:
        self._tx = tx
        self._clock = clock
        self._user_repo = user_repo
        self._role_binding_repo = role_binding_repo
        self._security_audit_repo = security_audit_repo
        self._seeder = seeder
        self._registration = registration

    def bootstrap_policy_catalog(self) -> None:
        """Initialize definitions without mutating reviewed role permissions. Deliberately its own
        transaction, separate from `bootstrap_defaults` below: both are independently idempotent, so
        a crash between the two self-heals on the next startup with no duplicate-insert or
        partial-account risk. Do not merge them into one transaction."""
        with self._tx.uow() as uow:
            self._seeder.ensure_auth_policy_definitions()
            uow.commit()

    def bootstrap_defaults(self) -> UserAccount:
        with self._tx.uow() as uow:
            role_map = self._seeder.ensure_auth_policy_defaults()

            admin_username = (
                os.getenv("PM_ADMIN_USERNAME", "admin").strip() or "admin"
            ).lower()
            admin = self._user_repo.get_by_username(admin_username)
            if admin is None:
                admin_password = resolve_bootstrap_admin_password()
                admin = self._registration.register_bootstrap_user(
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
                if admin_role and self._role_binding_repo is None:
                    raise BusinessRuleError(
                        "Canonical role-binding persistence is not configured.",
                        code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
                    )
                existing_admin_binding = (
                    self._role_binding_repo.get_active_for_assignment(
                        principal_id=admin.id,
                        role_id=admin_role.id,
                        tenant_id=None,
                        actual_scope_type=ROLE_SCOPE_PLATFORM,
                        actual_scope_id=None,
                    )
                    if admin_role is not None and self._role_binding_repo is not None
                    else None
                )
                if admin_role and existing_admin_binding is None:
                    # A real, actual repair (the admin account already exists but is missing its
                    # RoleBinding row) -- records the exact fact for the change that actually
                    # happened (a new RoleBinding), never a fabricated "account created" fact.
                    create_role_binding_using(
                        role_bindings_repo=self._role_binding_repo,
                        audit_repo=self._security_audit_repo,
                        clock=self._clock,
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


__all__ = ["AuthBootstrapHandler"]
