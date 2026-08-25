from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from src.core.modules.project_management.contracts.reads.sorting import (
    ReadSort,
    ReadSortDirection,
)
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


@dataclass(frozen=True, slots=True)
class OwnerTimesheetIdentityFact:
    user_id: str
    employee_id: str
    resource_id: str
    resource_name: str
    resource_code: str


@dataclass(frozen=True, slots=True)
class OwnerTimesheetPeriodFact:
    period_id: str
    resource_id: str
    resource_name: str
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


@dataclass(frozen=True, slots=True)
class OwnerTimesheetEntryCriteria:
    period_start: date
    search_text: str = ""
    project_id: str | None = None
    task_id: str | None = None
    work_date_from: date | None = None
    work_date_to: date | None = None
    sort: ReadSort = ReadSort("date", ReadSortDirection.DESCENDING)


@dataclass(frozen=True, slots=True)
class OwnerTimesheetEntryFact:
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
class OwnerTimesheetEntryReadPage:
    items: tuple[OwnerTimesheetEntryFact, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("date", ReadSortDirection.DESCENDING)


@dataclass(frozen=True, slots=True)
class OwnerTimesheetHistoryCriteria:
    status: TimesheetPeriodStatus | None = None
    sort: ReadSort = ReadSort("period", ReadSortDirection.DESCENDING)


@dataclass(frozen=True, slots=True)
class OwnerTimesheetHistoryReadPage:
    items: tuple[OwnerTimesheetPeriodFact, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 12
    sort: ReadSort = ReadSort("period", ReadSortDirection.DESCENDING)


class OwnerTimesheetReader(Protocol):
    def resolve_identity(
        self,
        *,
        user_id: str,
        tenant_id: str,
        organization_id: str,
    ) -> OwnerTimesheetIdentityFact | None: ...

    def read_period(
        self,
        *,
        identity: OwnerTimesheetIdentityFact,
        tenant_id: str,
        organization_id: str,
        period_start: date,
        allowed_project_ids: tuple[str, ...] | None,
    ) -> OwnerTimesheetPeriodFact: ...

    def read_entries(
        self,
        *,
        identity: OwnerTimesheetIdentityFact,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        criteria: OwnerTimesheetEntryCriteria,
        page: int,
        page_size: int,
    ) -> OwnerTimesheetEntryReadPage: ...

    def read_history(
        self,
        *,
        identity: OwnerTimesheetIdentityFact,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        criteria: OwnerTimesheetHistoryCriteria,
        page: int,
        page_size: int,
    ) -> OwnerTimesheetHistoryReadPage: ...


__all__ = [
    "OwnerTimesheetEntryCriteria",
    "OwnerTimesheetEntryFact",
    "OwnerTimesheetEntryReadPage",
    "OwnerTimesheetHistoryCriteria",
    "OwnerTimesheetHistoryReadPage",
    "OwnerTimesheetIdentityFact",
    "OwnerTimesheetPeriodFact",
    "OwnerTimesheetReader",
]
