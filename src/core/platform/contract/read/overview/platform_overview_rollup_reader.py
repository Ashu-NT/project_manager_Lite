
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


@dataclass(frozen=True, slots=True)
class UserRollupSummary:
    total: int
    active: int
    locked: int


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

    def get_user_summary(self, *, tenant_id: str | None) -> UserRollupSummary: ...


__all__ = [
    "DepartmentRollupSummary",
    "DocumentRollupSummary",
    "PartyRollupSummary",
    "PlatformOverviewRollupReader",
    "SiteRollupSummary",
    "UserRollupSummary",
]
