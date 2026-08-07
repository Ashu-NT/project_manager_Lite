from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from src.core.platform.contract.security.auth import RoleDelegationPolicyRepository, RoleRepository
from src.core.platform.common.exceptions import BusinessRuleError

from src.core.platform.application.security.authorization.roles.role_governance_service import RoleGovernanceService


DEFAULT_SCOPE_DELEGATIONS: tuple[tuple[str, str, str], ...] = (
    ("access_admin", "project_viewer", "project"),
    ("access_admin", "project_contributor", "project"),
    ("access_admin", "project_lead", "project"),
    ("access_admin", "project_owner", "project"),
    ("access_admin", "site_viewer", "site"),
    ("access_admin", "site_operator", "site"),
    ("access_admin", "site_manager", "site"),
    ("access_admin", "storeroom_viewer", "storeroom"),
    ("access_admin", "storeroom_operator", "storeroom"),
    ("access_admin", "storeroom_manager", "storeroom"),
    ("access_admin", "maintenance_viewer", "maintenance"),
    ("access_admin", "maintenance_operator", "maintenance"),
    ("access_admin", "maintenance_scope_manager", "maintenance"),
)


@dataclass(frozen=True)
class ScopeDelegationPlanEntry:
    actor_role_name: str
    assignable_role_name: str
    target_scope_type: str
    exists: bool


@dataclass(frozen=True)
class ScopeDelegationPlan:
    catalog_hash: str
    entries: tuple[ScopeDelegationPlanEntry, ...]
    missing_role_names: frozenset[str]

    @property
    def pending_entries(self) -> tuple[ScopeDelegationPlanEntry, ...]:
        return tuple(entry for entry in self.entries if not entry.exists)

    @property
    def has_changes(self) -> bool:
        return bool(self.pending_entries)


@dataclass(frozen=True)
class ScopeDelegationApplyResult:
    catalog_hash: str
    created: tuple[ScopeDelegationPlanEntry, ...]


def _catalog_hash(catalog: tuple[tuple[str, str, str], ...]) -> str:
    canonical = json.dumps(list(catalog), separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ScopeDelegationProvisioningService:
    """Deliberate, reviewed provisioning of resource-scope delegation policies.

    `RoleGovernanceService.assign_role` denies any assignment lacking an
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
        delegation_repo: RoleDelegationPolicyRepository,
        role_governance_service: RoleGovernanceService,
    ) -> None:
        self._role_repo = role_repo
        self._delegation_repo = delegation_repo
        self._role_governance_service = role_governance_service

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

    def apply(
        self,
        *,
        expected_catalog_hash: str,
        catalog: tuple[tuple[str, str, str], ...] = DEFAULT_SCOPE_DELEGATIONS,
    ) -> ScopeDelegationApplyResult:
        plan = self.preview(catalog)
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
            self._role_governance_service.create_delegation_policy(
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


__all__ = [
    "DEFAULT_SCOPE_DELEGATIONS",
    "ScopeDelegationApplyResult",
    "ScopeDelegationPlan",
    "ScopeDelegationPlanEntry",
    "ScopeDelegationProvisioningService",
]
