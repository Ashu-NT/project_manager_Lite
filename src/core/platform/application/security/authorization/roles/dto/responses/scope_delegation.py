from __future__ import annotations

from dataclasses import dataclass


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
