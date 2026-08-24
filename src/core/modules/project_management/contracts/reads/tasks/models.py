from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from src.core.modules.project_management.contracts.reads.sorting import ReadSort


@dataclass(frozen=True, slots=True)
class TaskWorkspaceCondition:
    field: str
    operator: str
    value: str


@dataclass(frozen=True, slots=True)
class TaskWorkspaceCriteria:
    project_id: str | None = None
    search_terms: tuple[str, ...] = ()
    conditions: tuple[TaskWorkspaceCondition, ...] = ()
    status: str = "all"
    priority: str = "all"
    schedule: str = "all"
    milestones_only: bool = False
    as_of: date | None = None


@dataclass(frozen=True, slots=True)
class TaskWorkspaceReadItem:
    id: str
    project_id: str
    project_name: str
    name: str
    code: str
    description: str
    status: str
    start_date: date | None
    end_date: date | None
    duration_days: int | None
    priority: int
    percent_complete: float
    actual_start: date | None
    actual_end: date | None
    deadline: date | None
    version: int
    parent_task_id: str | None
    wbs_code: str
    sort_order: int
    is_summary: bool
    hierarchy_depth: int
    child_count: int
    is_milestone: bool = False


@dataclass(frozen=True, slots=True)
class TaskWorkspaceSummary:
    total: int = 0
    in_progress: int = 0
    blocked: int = 0
    done: int = 0
    overdue: int = 0


@dataclass(frozen=True, slots=True)
class TaskAssignmentReadItem:
    assignment_id: str
    resource_id: str
    resource_code: str
    resource_name: str
    role: str
    allocation_percent: Decimal
    planned_hours: Decimal
    actual_hours: Decimal
    response_status: str
    project_resource_id: str | None
    version: int


@dataclass(frozen=True, slots=True)
class TaskAssignmentReadPage:
    items: tuple[TaskAssignmentReadItem, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("resourceName")


@dataclass(frozen=True, slots=True)
class TaskDependencyReadItem:
    dependency_id: str
    direction: str
    linked_task_id: str
    linked_task_code: str
    linked_task_name: str
    linked_task_status: str
    linked_task_start: date | None
    linked_task_end: date | None
    dependency_type: str
    lag_days: int
    version: int


@dataclass(frozen=True, slots=True)
class TaskDependencyReadPage:
    items: tuple[TaskDependencyReadItem, ...] = ()
    filtered_total: int = 0
    predecessor_total: int = 0
    successor_total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("linkedTask")


@dataclass(frozen=True, slots=True)
class TaskActivityFact:
    activity_id: str
    occurred_at: datetime
    actor_id: str | None
    action: str
    entity_type: str
    summary: str
    details: dict[str, object]


@dataclass(frozen=True, slots=True)
class TaskActivityPage:
    items: tuple[TaskActivityFact, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("occurredAt")


@dataclass(frozen=True, slots=True)
class TaskWorkspaceReadPage:
    items: tuple[TaskWorkspaceReadItem, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    summary: TaskWorkspaceSummary = TaskWorkspaceSummary()
    sort: ReadSort = ReadSort("wbsCode")


@dataclass(frozen=True, slots=True)
class TaskResourceTimeBreakdownRow:
    """One TaskAssignment's planned-vs-actual row for the Task Detail ->
    Time -> Overview resource breakdown (docs §44 Time redesign). Every
    figure here is the SAME authoritative TaskAssignment field the
    Assignment section already renders -- this is a read-model
    aggregation, not a new calculation."""

    assignment_id: str
    resource_id: str
    resource_name: str
    planned_hours: Decimal
    actual_hours: Decimal
    remaining_hours: Decimal
    overrun_hours: Decimal
    burn_status: str


@dataclass(frozen=True, slots=True)
class TaskTimeSummaryFact:
    """Task-scoped (never resource-wide) planned/actual/remaining/overrun
    totals across every TaskAssignment on this task, plus the per-resource
    breakdown that explains where those totals come from. Reuses the same
    `burn_status`/`planned_burn_percent` authority already established for
    the ProjectResource envelope (application/common/
    project_resource_envelope_policy.py) -- one vocabulary for "how does
    actual compare to plan," not two."""

    task_id: str
    planned_hours: Decimal
    actual_hours: Decimal
    remaining_hours: Decimal
    overrun_hours: Decimal
    burn_status: str
    assignment_count: int
    resource_breakdown: tuple[TaskResourceTimeBreakdownRow, ...] = ()


@dataclass(frozen=True, slots=True)
class TaskTimeEntryRow:
    """One TimeEntry plus the resource it was logged against -- TimeEntry
    itself carries only `work_allocation_id`, so this pairs it with the
    resource_id resolved from that TaskAssignment (docs §44 Time
    redesign's task-scoped, all-assignments Time Entries list)."""

    entry_id: str
    work_allocation_id: str
    resource_id: str
    entry_date: date
    hours: float
    note: str
    author_username: str | None


@dataclass(frozen=True, slots=True)
class TaskTimeEntriesPage:
    items: tuple[TaskTimeEntryRow, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25


__all__ = [
    "TaskResourceTimeBreakdownRow",
    "TaskActivityFact",
    "TaskActivityPage",
    "TaskAssignmentReadItem",
    "TaskAssignmentReadPage",
    "TaskDependencyReadItem",
    "TaskDependencyReadPage",
    "TaskTimeEntriesPage",
    "TaskTimeEntryRow",
    "TaskTimeSummaryFact",
    "TaskWorkspaceCondition",
    "TaskWorkspaceCriteria",
    "TaskWorkspaceReadItem",
    "TaskWorkspaceReadPage",
    "TaskWorkspaceSummary",
]
