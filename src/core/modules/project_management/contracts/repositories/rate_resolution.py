"""Rate-resolution read contracts — ADR-PF-005.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from src.core.modules.project_management.domain.financials.rate_cards import (
    RateCardLine,
    RateSelectionSnapshot,
    RateType,
)


@dataclass(frozen=True, slots=True)
class ResourceRateContext:
    """Everything ``classify_line()`` needs about one resource — one
    entry per resource, not a separate resource-fetch plus a separate
    skill-fetch stitched together by the caller."""

    resource_id: str
    role: str | None
    department_id: str | None
    skill_codes: frozenset[str]


@dataclass(frozen=True, slots=True)
class RateResolutionCandidate:
    """A line already paired with its own card's scope/version — no
    per-line follow-up query to learn whether the card is project-scoped
    or what version it's on."""

    line: RateCardLine
    card_project_id: str | None
    card_version: int


class RateResolutionReader(Protocol):
    def list_resource_contexts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_ids: tuple[str, ...],
    ) -> tuple[ResourceRateContext, ...]: ...

    def list_candidates(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str | None,
        rate_type: RateType,
        unit: str,
        as_of: date,
    ) -> tuple[RateResolutionCandidate, ...]: ...


@dataclass(frozen=True, slots=True)
class UnresolvedLaborRate:
    resource_id: str
    project_id: str | None
    as_of: date
    reason_code: str
    detail: str


@dataclass(frozen=True, slots=True)
class ResolvedLaborRate:
    resource_id: str
    snapshot: RateSelectionSnapshot


@dataclass(frozen=True, slots=True)
class RateResolutionBatch:
    resolved: tuple[ResolvedLaborRate, ...]
    unresolved: tuple[UnresolvedLaborRate, ...]

    @property
    def is_complete(self) -> bool:
        return not self.unresolved

    def snapshot_for(self, resource_id: str) -> RateSelectionSnapshot | None:
        for entry in self.resolved:
            if entry.resource_id == resource_id:
                return entry.snapshot
        return None


class LaborRateResolver(Protocol):
    def resolve_many(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str | None,
        resource_ids: tuple[str, ...],
        rate_type: RateType,
        as_of: date,
        unit: str,
    ) -> RateResolutionBatch: ...


__all__ = [
    "LaborRateResolver",
    "RateResolutionBatch",
    "RateResolutionCandidate",
    "RateResolutionReader",
    "ResolvedLaborRate",
    "ResourceRateContext",
    "UnresolvedLaborRate",
]
