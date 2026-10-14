from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from src.core.platform.common.pydantic import validated_dataclass


@validated_dataclass(frozen=True)
class RolePermissionChange:
    role_name: str
    permission_code: str


@validated_dataclass(frozen=True)
class RolePolicyReconciliationPlan:
    policy_name: str
    current_version: int
    target_version: int
    additions: tuple[RolePermissionChange, ...]
    removals: tuple[RolePermissionChange, ...]
    affected_user_ids: tuple[str, ...]
    active_session_ids: tuple[str, ...]
    missing_role_names: tuple[str, ...]
    missing_permission_codes: tuple[str, ...]
    change_set_hash: str
    rollback_json: str

    @property
    def has_changes(self) -> bool:
        return bool(self.additions or self.removals)


@validated_dataclass(frozen=True)
class RolePolicyReconciliationResult:
    plan: RolePolicyReconciliationPlan
    applied: bool
    revoked_session_count: int


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
