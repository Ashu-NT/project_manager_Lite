from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.application.time_management.time.time_service import TimeService
from src.core.platform.domain.time_management.time import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus


class _FakeSession:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.flush_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        return None

    def flush(self) -> None:
        self.flush_calls += 1


@dataclass
class _FakePrincipal:
    user_id: str
    username: str


class _FakeUserSession:
    def __init__(self) -> None:
        self.principal = _FakePrincipal(user_id="user-1", username="ada")


@dataclass
class _FakeWorkAllocation:
    id: str
    resource_id: str
    hours_logged: float = 0.0
    owner_type: str = "task_assignment"
    owner_id: str | None = None
    owner_label: str = ""
    scope_type: str | None = None
    scope_id: str | None = None
    task_id: str | None = None
    work_owner_id: str | None = "owner-1"


@dataclass
class _FakeWorkOwner:
    id: str
    name: str
    scope_type: str | None = "project"
    scope_id: str | None = "project-1"
    project_id: str | None = "project-1"
    start_date: date | None = date(2026, 7, 1)
    actual_start: date | None = None


@dataclass
class _FakeResource:
    id: str
    name: str
    employee_id: str | None = "employee-1"


@dataclass
class _FakeEmployee:
    id: str
    department_id: str | None = "dept-1"
    department: str = "Engineering"
    site_id: str | None = "site-1"
    site_name: str = "Berlin Hub"


class _FakeWorkAllocationRepo:
    def __init__(self, allocation: _FakeWorkAllocation) -> None:
        self._rows = {allocation.id: allocation}

    def get(self, work_allocation_id: str) -> _FakeWorkAllocation | None:
        return self._rows.get(work_allocation_id)

    def list_by_resource(self, resource_id: str) -> list[_FakeWorkAllocation]:
        return [row for row in self._rows.values() if row.resource_id == resource_id]

    def update(self, work_allocation: _FakeWorkAllocation) -> None:
        self._rows[work_allocation.id] = work_allocation


class _FakeWorkOwnerRepo:
    def __init__(self, owner: _FakeWorkOwner) -> None:
        self._rows = {owner.id: owner}

    def get(self, owner_id: str) -> _FakeWorkOwner | None:
        return self._rows.get(owner_id)


class _FakeResourceRepo:
    def __init__(self, resource: _FakeResource) -> None:
        self._rows = {resource.id: resource}

    def get(self, resource_id: str) -> _FakeResource | None:
        return self._rows.get(resource_id)


class _FakeEmployeeRepo:
    def __init__(self, employee: _FakeEmployee) -> None:
        self._rows = {employee.id: employee}

    def get(self, employee_id: str) -> _FakeEmployee | None:
        return self._rows.get(employee_id)


class _FakeTimeEntryRepo:
    def __init__(self) -> None:
        self._rows: dict[str, TimeEntry] = {}

    def add(self, entry: TimeEntry) -> None:
        self._rows[entry.id] = entry

    def get(self, entry_id: str) -> TimeEntry | None:
        return self._rows.get(entry_id)

    def update(self, entry: TimeEntry, *, expected_version: int) -> TimeEntry:
        assert self._rows[entry.id].version == expected_version
        entry.version += 1
        self._rows[entry.id] = entry
        return entry

    def delete(self, entry_id: str, *, expected_version: int) -> None:
        assert self._rows[entry_id].version == expected_version
        self._rows.pop(entry_id, None)

    def list_by_work_allocation(self, work_allocation_id: str) -> list[TimeEntry]:
        return sorted(
            [row for row in self._rows.values() if row.work_allocation_id == work_allocation_id],
            key=lambda row: row.entry_date,
        )

    def delete_by_work_allocation(self, work_allocation_id: str) -> None:
        for entry_id in [row.id for row in self.list_by_work_allocation(work_allocation_id)]:
            self.delete(entry_id)


class _FakeTimesheetPeriodRepo:
    def __init__(self) -> None:
        self._rows: dict[str, TimesheetPeriod] = {}

    def add(self, period: TimesheetPeriod) -> None:
        self._rows[period.id] = period

    def get(self, period_id: str) -> TimesheetPeriod | None:
        return self._rows.get(period_id)

    def update(self, period: TimesheetPeriod) -> None:
        self._rows[period.id] = period

    def transition(
        self,
        period: TimesheetPeriod,
        *,
        expected_status: TimesheetPeriodStatus,
        expected_version: int,
    ) -> TimesheetPeriod:
        del expected_status
        if period.version != expected_version:
            raise AssertionError("stale test period")
        period.version += 1
        self._rows[period.id] = period
        return period

    def get_by_resource_period(self, resource_id: str, period_start: date) -> TimesheetPeriod | None:
        for row in self._rows.values():
            if row.resource_id == resource_id and row.period_start == period_start:
                return row
        return None

    def list_by_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        return sorted(
            [row for row in self._rows.values() if row.resource_id == resource_id],
            key=lambda row: row.period_start,
        )

    def list_review_candidates(
        self,
        *,
        organization_id: str | None = None,
        status: TimesheetPeriodStatus | None = None,
        limit: int | None = None,
    ) -> list[TimesheetPeriod]:
        rows = list(self._rows.values())
        if organization_id is not None:
            rows = [row for row in rows if row.organization_id == organization_id]
        if status is not None:
            rows = [row for row in rows if row.status == status]
        rows.sort(key=lambda row: row.period_start)
        if limit is not None:
            rows = rows[:limit]
        return rows


def _make_time_service(monkeypatch: pytest.MonkeyPatch) -> tuple[TimeService, _FakeWorkAllocation]:
    monkeypatch.setattr(
        "src.core.platform.application.time_management.time.timesheet_support.require_any_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.platform.application.time_management.time.timesheet_periods.require_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.platform.application.time_management.time.timesheet_entries.record_audit_entry",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.platform.application.time_management.time.timesheet_periods.record_audit_entry",
        lambda *args, **kwargs: None,
    )

    allocation = _FakeWorkAllocation(id="alloc-1", resource_id="resource-1")
    service = TimeService(
        session=_FakeSession(),
        assignment_repo=_FakeWorkAllocationRepo(allocation),
        task_repo=_FakeWorkOwnerRepo(_FakeWorkOwner(id="owner-1", name="Task Alpha")),
        resource_repo=_FakeResourceRepo(_FakeResource(id="resource-1", name="Alice Admin")),
        employee_repo=_FakeEmployeeRepo(_FakeEmployee(id="employee-1")),
        time_entry_repo=_FakeTimeEntryRepo(),
        timesheet_period_repo=_FakeTimesheetPeriodRepo(),
        user_session=_FakeUserSession(),
    )
    return service, allocation


def test_time_entry_dto_normalizes_and_validates_fields():
    entry = TimeEntry.create(
        "  alloc-1  ",
        entry_date=date(2026, 7, 10),
        hours="4.5",
        organization_id="  org-1  ",
        assignment_id="",
        note="  Daily work  ",
        author_user_id="  user-1  ",
        author_username="  ada  ",
        owner_type="  task_assignment  ",
        owner_id="",
        owner_label="  Task Alpha  ",
        scope_type="  project  ",
        scope_id="  project-1  ",
        employee_id="  employee-1  ",
        department_id="  dept-1  ",
        department_name="  Engineering  ",
        site_id="  site-1  ",
        site_name="  Berlin Hub  ",
    )

    assert entry.work_allocation_id == "alloc-1"
    assert entry.hours == 4.5
    assert entry.organization_id == "org-1"
    assert entry.assignment_id == "alloc-1"
    assert entry.note == "Daily work"
    assert entry.author_user_id == "user-1"
    assert entry.author_username == "ada"
    assert entry.owner_type == "task_assignment"
    assert entry.owner_id == "alloc-1"
    assert entry.owner_label == "Task Alpha"
    assert entry.scope_type == "project"
    assert entry.scope_id == "project-1"
    assert entry.employee_id == "employee-1"
    assert entry.department_id == "dept-1"
    assert entry.department_name == "Engineering"
    assert entry.site_id == "site-1"
    assert entry.site_name == "Berlin Hub"

    with pytest.raises(ValidationError) as exc_hours:
        TimeEntry.create(
            "alloc-1",
            entry_date=date(2026, 7, 10),
            hours=0,
        )
    assert exc_hours.value.code == "TIME_ENTRY_HOURS_INVALID"


def test_timesheet_period_dto_normalizes_and_validates_fields():
    period = TimesheetPeriod(
        id="period-1",
        resource_id="  resource-1  ",
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
        organization_id="  org-1  ",
        status="submitted",
        submitted_by_user_id="  user-1  ",
        submitted_by_username="  ada  ",
        decision_note="  Ready for review  ",
    )

    assert period.resource_id == "resource-1"
    assert period.organization_id == "org-1"
    assert period.status is TimesheetPeriodStatus.SUBMITTED
    assert period.submitted_by_user_id == "user-1"
    assert period.submitted_by_username == "ada"
    assert period.decision_note == "Ready for review"

    with pytest.raises(ValidationError) as exc_range:
        TimesheetPeriod(
            id="period-2",
            resource_id="resource-1",
            period_start=date(2026, 7, 31),
            period_end=date(2026, 7, 1),
        )
    assert exc_range.value.code == "TIMESHEET_PERIOD_RANGE_INVALID"


def test_time_service_uses_entity_validation_for_entries_and_periods(monkeypatch: pytest.MonkeyPatch):
    service, allocation = _make_time_service(monkeypatch)

    entry = service.add_work_entry(
        "alloc-1",
        entry_date=date(2026, 7, 10),
        hours="4.0",
        note="  Initial work  ",
    )

    assert entry.hours == 4.0
    assert entry.note == "Initial work"
    assert entry.owner_type == "task_assignment"
    assert entry.owner_label == "Task Alpha"
    assert entry.scope_type == "project"
    assert entry.scope_id == "project-1"
    assert entry.department_name == "Engineering"
    assert entry.site_name == "Berlin Hub"
    assert allocation.hours_logged == 4.0

    updated = service.update_time_entry(
        entry.id,
        expected_version=entry.version,
        hours="5.5",
        note="  Revised work  ",
    )

    assert updated.hours == 5.5
    assert updated.note == "Revised work"
    assert allocation.hours_logged == 5.5

    submitted = service.submit_timesheet_period(
        "resource-1",
        period_start=date(2026, 7, 5),
        note="  Submitted for approval  ",
    )

    assert submitted.status is TimesheetPeriodStatus.SUBMITTED
    assert submitted.period_start == date(2026, 7, 1)
    assert submitted.period_end == date(2026, 7, 31)
    assert submitted.submitted_by_user_id == "user-1"
    assert submitted.submitted_by_username == "ada"
    assert submitted.decision_note == "Submitted for approval"

    approved = service.approve_timesheet_period(
        submitted.period_id,
        expected_version=submitted.version,
        note="  Approved  ",
    )

    assert approved.status is TimesheetPeriodStatus.APPROVED
    assert approved.decided_by_user_id == "user-1"
    assert approved.decided_by_username == "ada"
    assert approved.decision_note == "Approved"
    assert approved.locked_at is None
