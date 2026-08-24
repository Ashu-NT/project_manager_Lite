from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.contracts.reads.sorting import ReadSort


@dataclass(frozen=True, slots=True)
class ProjectCatalogReadItem:
    project: Project
    site_label: str = ""
    financial_currency_code: str = ""
    approved_budget: Decimal | None = None
    approved_budget_currency: str = ""
    approved_budget_visible: bool = False
    client_label: str = ""


@dataclass(frozen=True, slots=True)
class ProjectCatalogSummary:
    total: int = 0
    active: int = 0
    planned: int = 0
    on_hold: int = 0
    completed: int = 0


@dataclass(frozen=True, slots=True)
class ProjectCatalogReadPage:
    items: tuple[ProjectCatalogReadItem, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    summary: ProjectCatalogSummary = ProjectCatalogSummary()
    sort: ReadSort = ReadSort("title")
    approved_budget_visible: bool = False


@dataclass(frozen=True, slots=True)
class ProjectResourceUsageFact:
    """Authoritative reconciliation of one ProjectResource's planned
    envelope against its task-level distribution and actual work.
    ``actual_hours``/``allocated_to_tasks_hours`` are bounded aggregate
    queries over that project_resource's TaskAssignment rows — never a
    client-side sum of a currently-loaded page."""

    project_resource_id: str
    project_id: str
    resource_id: str
    planned_hours: Decimal
    allocated_to_tasks_hours: Decimal
    unallocated_planned_hours: Decimal
    actual_hours: Decimal
    remaining_project_hours: Decimal
    planned_burn_percent: float
    task_assignment_count: int
    envelope_status: str
    burn_status: str
    version: int


@dataclass(frozen=True, slots=True)
class ProjectResourceDetailFact:
    project_resource_id: str
    resource_id: str
    resource_code: str
    resource_name: str
    role: str
    planned_hours: Decimal
    allocated_hours: Decimal
    actual_hours: Decimal
    remaining_hours: Decimal
    is_active: bool
    version: int


@dataclass(frozen=True, slots=True)
class ProjectResourceDetailPage:
    items: tuple[ProjectResourceDetailFact, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("resourceName")


@dataclass(frozen=True, slots=True)
class ProjectActivityFact:
    activity_id: str
    occurred_at: datetime
    actor_id: str | None
    action: str
    entity_type: str
    summary: str
    details: dict[str, object]


@dataclass(frozen=True, slots=True)
class ProjectActivityPage:
    items: tuple[ProjectActivityFact, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("occurredAt")


__all__ = [
    "ProjectCatalogReadItem",
    "ProjectCatalogReadPage",
    "ProjectCatalogSummary",
    "ProjectActivityFact",
    "ProjectActivityPage",
    "ProjectResourceDetailFact",
    "ProjectResourceDetailPage",
    "ProjectResourceUsageFact",
]
