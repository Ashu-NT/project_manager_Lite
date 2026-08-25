from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol

from src.core.modules.project_management.contracts.reads.sorting import (
    ReadSort,
    ReadSortDirection,
)
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


class TimesheetScope(str, Enum):
    MINE = "mine"
    TEAM = "team"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class TimesheetResourceFact:
    resource_id: str
    resource_name: str
    resource_code: str
    kind: str
    worker_type: str
    employee_id: str | None = None
    identity_user_id: str | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class TimesheetResourceSelectorCriteria:
    search_text: str = ""
    include_inactive: bool = False
    sort: ReadSort = ReadSort("resource", ReadSortDirection.ASCENDING)


@dataclass(frozen=True, slots=True)
class TimesheetResourceReadPage:
    items: tuple[TimesheetResourceFact, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 20
    sort: ReadSort = ReadSort("resource", ReadSortDirection.ASCENDING)


@dataclass(frozen=True, slots=True)
class TimesheetWorkspaceAccessFact:
    actor_user_id: str
    available_scopes: tuple[TimesheetScope, ...]
    default_scope: TimesheetScope
    mine_resource: TimesheetResourceFact | None = None


@dataclass(frozen=True, slots=True)
class TimesheetPeriodFact:
    period_id: str
    resource_id: str
    resource_name: str
    resource_code: str
    resource_kind: str
    worker_type: str
    period_start: date
    period_end: date
    status: TimesheetPeriodStatus
    version: int
    total_hours: Decimal
    entry_count: int
    project_count: int
    task_count: int
    submitted_at: datetime | None = None
    decided_at: datetime | None = None
    decision_note: str = ""
    locked_at: datetime | None = None
    can_add_entry: bool = False
    can_edit_entry: bool = False
    can_delete_entry: bool = False
    can_submit: bool = False
    can_resubmit: bool = False
    can_view_return_reason: bool = False
    can_view_history: bool = False


@dataclass(frozen=True, slots=True)
class TimesheetEntryCriteria:
    period_start: date
    search_text: str = ""
    project_id: str | None = None
    task_id: str | None = None
    work_date_from: date | None = None
    work_date_to: date | None = None
    sort: ReadSort = ReadSort("date", ReadSortDirection.DESCENDING)


@dataclass(frozen=True, slots=True)
class TimesheetEntryFact:
    entry_id: str
    assignment_id: str
    work_date: date
    hours: Decimal
    description: str
    project_id: str | None
    project_code: str
    project_name: str
    task_id: str | None
    task_code: str
    task_name: str
    activity_type: str
    updated_at: datetime | None
    can_edit: bool = False
    can_delete: bool = False


@dataclass(frozen=True, slots=True)
class TimesheetEntryReadPage:
    items: tuple[TimesheetEntryFact, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("date", ReadSortDirection.DESCENDING)


@dataclass(frozen=True, slots=True)
class TimesheetHistoryCriteria:
    status: TimesheetPeriodStatus | None = None
    sort: ReadSort = ReadSort("period", ReadSortDirection.DESCENDING)


@dataclass(frozen=True, slots=True)
class TimesheetHistoryReadPage:
    items: tuple[TimesheetPeriodFact, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 12
    sort: ReadSort = ReadSort("period", ReadSortDirection.DESCENDING)


class TimesheetWorkspaceReader(Protocol):
    def resolve_mine_resource(
        self,
        *,
        user_id: str,
        tenant_id: str,
        organization_id: str,
    ) -> TimesheetResourceFact | None: ...

    def read_resource_page(
        self,
        *,
        scope: TimesheetScope,
        actor_user_id: str,
        explicit_team_project_ids: tuple[str, ...],
        tenant_id: str,
        organization_id: str,
        criteria: TimesheetResourceSelectorCriteria,
        page: int,
        page_size: int,
    ) -> TimesheetResourceReadPage: ...

    def read_resource_in_scope(
        self,
        *,
        scope: TimesheetScope,
        resource_id: str,
        actor_user_id: str,
        explicit_team_project_ids: tuple[str, ...],
        tenant_id: str,
        organization_id: str,
    ) -> TimesheetResourceFact | None: ...

    def read_period(
        self,
        *,
        resource: TimesheetResourceFact,
        tenant_id: str,
        organization_id: str,
        period_start: date,
    ) -> TimesheetPeriodFact: ...

    def read_entries(
        self,
        *,
        resource: TimesheetResourceFact,
        tenant_id: str,
        organization_id: str,
        visible_project_ids: tuple[str, ...] | None,
        criteria: TimesheetEntryCriteria,
        page: int,
        page_size: int,
    ) -> TimesheetEntryReadPage: ...

    def read_history(
        self,
        *,
        resource: TimesheetResourceFact,
        tenant_id: str,
        organization_id: str,
        criteria: TimesheetHistoryCriteria,
        page: int,
        page_size: int,
    ) -> TimesheetHistoryReadPage: ...


__all__ = [
    "TimesheetEntryCriteria",
    "TimesheetEntryFact",
    "TimesheetEntryReadPage",
    "TimesheetHistoryCriteria",
    "TimesheetHistoryReadPage",
    "TimesheetPeriodFact",
    "TimesheetResourceFact",
    "TimesheetResourceReadPage",
    "TimesheetResourceSelectorCriteria",
    "TimesheetScope",
    "TimesheetWorkspaceReader",
    "TimesheetWorkspaceAccessFact",
]
