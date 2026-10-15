from __future__ import annotations

from src.core.platform.application.security.authorization.roles._scope_delegation import (
    DEFAULT_SCOPE_DELEGATIONS,
)
from src.core.platform.application.security.authorization.roles.commands.role_governance import (
    RoleGovernanceCommandHandler,
)
from src.core.platform.application.security.authorization.roles.dto.responses.scope_delegation import (
    ScopeDelegationApplyResult,
    ScopeDelegationPlanEntry,
)
from src.core.platform.application.security.authorization.roles.queries.scope_delegation_provisioning import (
    ScopeDelegationProvisioningQueryHandler,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.repositories.security.auth import RoleRepository


class ScopeDelegationProvisioningCommandHandler:
    """Deliberate, reviewed provisioning of resource-scope delegation policies.

    `RoleGovernanceCommandHandler.assign_role` denies any assignment lacking an
    active `RoleDelegationPolicy`. Nothing seeds those policies at ordinary
    startup, by design: expanding what a role may delegate is a security
    decision, not an additive convenience. This service previews the
    code-owned catalog against current state and applies only the reviewed,
    hash-pinned change-set.
    """

    def __init__(
        self,
        *,
        role_repo: RoleRepository,
        queries: ScopeDelegationProvisioningQueryHandler,
        role_governance_commands: RoleGovernanceCommandHandler,
    ) -> None:
        self._role_repo = role_repo
        self._queries = queries
        self._role_governance_commands = role_governance_commands

    def apply(
        self,
        *,
        expected_catalog_hash: str,
        catalog: tuple[tuple[str, str, str], ...] = DEFAULT_SCOPE_DELEGATIONS,
    ) -> ScopeDelegationApplyResult:
        plan = self._queries.preview(catalog)
        if plan.catalog_hash != expected_catalog_hash:
            raise BusinessRuleError(
                "The scope delegation catalog changed since the reviewed preview.",
                code="SCOPE_DELEGATION_CATALOG_HASH_MISMATCH",
            )
        if plan.missing_role_names:
            raise BusinessRuleError(
                "Cannot provision delegation policies for undefined roles.",
                code="SCOPE_DELEGATION_ROLE_MISSING",
            )
        created: list[ScopeDelegationPlanEntry] = []
        for entry in plan.pending_entries:
            actor_role = self._role_repo.get_by_name(entry.actor_role_name)
            assignable_role = self._role_repo.get_by_name(entry.assignable_role_name)
            if actor_role is None or assignable_role is None:
                raise BusinessRuleError(
                    "A catalog role was removed between preview and apply.",
                    code="SCOPE_DELEGATION_ROLE_MISSING",
                )
            self._role_governance_commands.create_delegation_policy(
                actor_role_id=actor_role.id,
                assignable_role_id=assignable_role.id,
                target_scope_type=entry.target_scope_type,
                tenant_id=None,
            )
            created.append(entry)
        return ScopeDelegationApplyResult(
            catalog_hash=plan.catalog_hash,
            created=tuple(created),
        )
