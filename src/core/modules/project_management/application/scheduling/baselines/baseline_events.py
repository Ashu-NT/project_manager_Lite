from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectBaselineCreated:
    tenant_id: str
    organization_id: str
    project_id: str
    baseline_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectBaselineSubmitted:
    tenant_id: str
    organization_id: str
    project_id: str
    baseline_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectBaselineApproved:
    """`superseded_baseline_id` is the previously-approved baseline this approval superseded,
    if any -- part of the same approval decision, never a separately-triggerable operation."""

    tenant_id: str
    organization_id: str
    project_id: str
    baseline_id: str
    superseded_baseline_id: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectBaselineRejected:
    tenant_id: str
    organization_id: str
    project_id: str
    baseline_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectBaselineDeleted:
    tenant_id: str
    organization_id: str
    project_id: str
    baseline_id: str
    occurred_at: datetime


__all__ = [
    "ProjectBaselineCreated",
    "ProjectBaselineSubmitted",
    "ProjectBaselineApproved",
    "ProjectBaselineRejected",
    "ProjectBaselineDeleted",
]
