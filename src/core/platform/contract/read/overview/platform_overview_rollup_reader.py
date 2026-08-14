"""Platform Overview rollup read contract.

A cohesive, overview-specific reader for the cross-entity counts
``PlatformAdminWorkspacePresenter.build_overview()`` needs -- replacing the
prior pattern of calling each entity's ``list_X(active_only=None)`` and
summing/``len()``-ing over every fully-hydrated row in Python just to
produce a handful of integers (plus, for Sites, three sampled names).

Employees keeps its own dedicated ``EmployeeHeadcountReader`` (P6)
unchanged. Users is deliberately NOT covered here: ``list_users()`` has
caller-type branching (platform operator vs. tenant user) and a
platform-role exclusion computed via per-user role lookups that a naive
``COUNT`` would not safely replicate -- left as a separate, later phase.

Each method takes ``tenant_id``/``organization_id`` explicitly rather than
resolving them from ambient session state, matching the existing
``EmployeeHeadcountReader`` precedent. ``get_site_summary`` additionally
accepts an optional ``allowed_site_ids`` filter: ``SiteService.list_sites()``
applies row-level scope restriction on top of its permission check
(``filter_scope_rows``), which the other four entities do not -- callers
that are scope-restricted for the "site" scope type must pass the caller's
allowed site ids so counts/samples reflect the same restricted view
``list_sites()`` would have shown, not the full organization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SiteRollupSummary:
    total: int
    active: int
    sample_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DepartmentRollupSummary:
    total: int
    active: int


@dataclass(frozen=True, slots=True)
class PartyRollupSummary:
    total: int
    active: int


@dataclass(frozen=True, slots=True)
class DocumentRollupSummary:
    total: int
    current: int


class PlatformOverviewRollupReader(Protocol):
    def get_organization_count(self, *, tenant_id: str) -> int: ...

    def get_site_summary(
        self,
        *,
        organization_id: str,
        tenant_id: str,
        allowed_site_ids: frozenset[str] | None = None,
    ) -> SiteRollupSummary: ...

    def get_department_summary(self, *, organization_id: str, tenant_id: str) -> DepartmentRollupSummary: ...

    def get_party_summary(self, *, organization_id: str, tenant_id: str) -> PartyRollupSummary: ...

    def get_document_summary(self, *, organization_id: str, tenant_id: str) -> DocumentRollupSummary: ...


__all__ = [
    "DepartmentRollupSummary",
    "DocumentRollupSummary",
    "PartyRollupSummary",
    "PlatformOverviewRollupReader",
    "SiteRollupSummary",
]
