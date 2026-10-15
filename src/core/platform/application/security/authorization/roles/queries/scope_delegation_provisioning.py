from __future__ import annotations

from src.core.platform.application.security.authorization.roles._scope_delegation import (
    DEFAULT_SCOPE_DELEGATIONS,
    _catalog_hash,
)
from src.core.platform.application.security.authorization.roles.dto.responses.scope_delegation import (
    ScopeDelegationPlan,
    ScopeDelegationPlanEntry,
)
from src.core.platform.contract.repositories.security.auth import (
    RoleDelegationPolicyRepository,
    RoleRepository,
)


class ScopeDelegationProvisioningQueryHandler:
    """Read-only preview of the reviewed scope delegation catalog."""

    def __init__(
        self,
        *,
        role_repo: RoleRepository,
        delegation_repo: RoleDelegationPolicyRepository,
    ) -> None:
        self._role_repo = role_repo
        self._delegation_repo = delegation_repo

    def preview(
        self,
        catalog: tuple[tuple[str, str, str], ...] = DEFAULT_SCOPE_DELEGATIONS,
    ) -> ScopeDelegationPlan:
        entries: list[ScopeDelegationPlanEntry] = []
        missing_role_names: set[str] = set()
        for actor_role_name, assignable_role_name, target_scope_type in catalog:
            actor_role = self._role_repo.get_by_name(actor_role_name)
            assignable_role = self._role_repo.get_by_name(assignable_role_name)
            if actor_role is None:
                missing_role_names.add(actor_role_name)
            if assignable_role is None:
                missing_role_names.add(assignable_role_name)
            exists = False
            if actor_role is not None and assignable_role is not None:
                existing = self._delegation_repo.get_active_exact(
                    actor_role_id=actor_role.id,
                    assignable_role_id=assignable_role.id,
                    tenant_id=None,
                    target_scope_type=target_scope_type,
                )
                exists = existing is not None
            entries.append(
                ScopeDelegationPlanEntry(
                    actor_role_name=actor_role_name,
                    assignable_role_name=assignable_role_name,
                    target_scope_type=target_scope_type,
                    exists=exists,
                )
            )
        return ScopeDelegationPlan(
            catalog_hash=_catalog_hash(catalog),
            entries=tuple(entries),
            missing_role_names=frozenset(missing_role_names),
        )
