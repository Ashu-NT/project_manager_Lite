from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_timesheets_desktop_api,
)
from src.core.modules.project_management.domain.enums import (
    CostType,
    ProjectStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment
from src.core.platform.time.application import TimesheetReviewDetail
from src.core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus


def test_project_management_timesheets_desktop_api_supports_assignment_periods_and_review() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    task_service = _FakeTaskService()
    task = task_service.create_task(
        project_id=project.id,
        name="Cable Pull",
        description="Primary feeder cable installation.",
        start_date=date(2026, 5, 3),
        duration_days=4,
    )
    resource_service = _FakeResourceService()
    resource = resource_service.create_resource(
        name="Electrical Crew",
        role="Lead Technician",
        hourly_rate=95.0,
        is_active=True,
        cost_type=CostType.LABOR,
        currency_code="eur",
        capacity_percent=110.0,
        address="Site Office",
        contact="crew@example.com",
        worker_type=WorkerType.EXTERNAL,
        employee_id=None,
    )
    assignment = task_service.create_assignment(
        task_id=task.id,
        resource_id=resource.id,
        allocation_percent=100.0,
    )
    timesheet_service = _FakeTimesheetService(
        task_service=task_service,
        resource_service=resource_service,
    )
    api = build_project_management_timesheets_desktop_api(
        project_service=project_service,
        task_service=task_service,
        resource_service=resource_service,
        timesheet_service=timesheet_service,
    )

    assert api.list_projects()[0].label == "Plant Upgrade"
    assert api.list_queue_statuses()[1].value == "OPEN"
    assert api.list_assignments(project_id=project.id)[0].label == (
        "Plant Upgrade | Cable Pull | Electrical Crew"
    )

    created_entry = api.add_time_entry(
        SimpleNamespace(
            assignment_id=assignment.id,
            entry_date=date(2026, 5, 3),
            hours=8.0,
            note="Cable tray installation",
        )
    )
    api.add_time_entry(
        SimpleNamespace(
            assignment_id=assignment.id,
            entry_date=date(2026, 5, 4),
            hours=6.5,
            note="Termination prep",
        )
    )
    updated_entry = api.update_time_entry(
        SimpleNamespace(
            entry_id=created_entry.entry_id,
            entry_date=date(2026, 5, 3),
            hours=7.5,
            note="Cable tray installation revised",
        )
    )
    snapshot = api.build_assignment_snapshot(assignment.id)
    submitted_period = api.submit_period(
        resource_id=resource.id,
        period_start=date(2026, 5, 1),
        note="Submitted for supervisor review.",
    )
    review_queue = api.list_review_queue()
    review_detail = api.get_review_detail(submitted_period.period_id)
    approved_period = api.approve_period(
        submitted_period.period_id,
        note="Approved after weekly close review.",
    )
    locked_period = api.lock_period(
        resource_id=resource.id,
        period_start=date(2026, 5, 1),
        note="Month-end payroll lock.",
    )
    unlocked_period = api.unlock_period(
        locked_period.period_id,
        note="Reopened for correction.",
    )
    api.delete_time_entry(created_entry.entry_id)

    assert updated_entry.hours_label == "7.50h"
    assert snapshot.assignment.resource_name == "Electrical Crew"
    assert snapshot.entries[0].entry_id == created_entry.entry_id
    assert snapshot.resource_period_total_hours_label == "14.00h"
    assert submitted_period.status == "SUBMITTED"
    assert review_queue[0].entry_count == 2
    assert review_detail.summary.resource_name == "Electrical Crew"
    assert review_detail.entries[0].task_name == "Cable Pull"
    assert approved_period.status == "APPROVED"
    assert locked_period.status == "LOCKED"
    assert unlocked_period.status == "OPEN"
    assert [entry.entry_id for entry in api.build_assignment_snapshot(assignment.id).entries] != [
        created_entry.entry_id
    ]


def test_project_management_desktop_api_does_not_import_qml_or_infra() -> None:
    api_root = Path("src/core/modules/project_management/api/desktop")
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in api_root.rglob("*.py")
        if "__pycache__" not in path.parts
    )

    assert "src.ui_qml" not in source_text
    assert "ui_qml" not in source_text
    assert "infrastructure.persistence" not in source_text


class _FakeProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._next_id = 1

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def create_project(
        self,
        *,
        name: str,
        description: str = "",
        status: "ProjectStatus | None" = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        planned_budget: float | None = None,
        currency: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Project:
        project = Project(
            id=f"proj-{self._next_id}",
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status=status if status is not None else ProjectStatus.PLANNED,
            client_name=client_name,
            client_contact=client_contact,
            planned_budget=planned_budget,
            currency=(currency or "").strip().upper() or None,
            version=1,
        )
        self._next_id += 1
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)


class _FakeEmployeeService:
    def __init__(self) -> None:
        self._employees: list[SimpleNamespace] = []

    def get_employee(self, employee_id: str) -> SimpleNamespace | None:
        return next((e for e in self._employees if e.id == employee_id), None)

    def list_employees(self, *, active_only: bool | None = None) -> list[SimpleNamespace]:
        return list(self._employees)


class _FakeResourceService:
    def __init__(self) -> None:
        self._resources: dict[str, SimpleNamespace] = {}
        self._next_id = 1
        self._employee_service = _FakeEmployeeService()

    def list_resources(self) -> list[SimpleNamespace]:
        return list(self._resources.values())

    def create_resource(
        self,
        *,
        name: str,
        role: str = "",
        hourly_rate: float = 0.0,
        is_active: bool = True,
        cost_type: CostType = CostType.LABOR,
        currency_code: str | None = None,
        capacity_percent: float = 100.0,
        address: str = "",
        contact: str = "",
        worker_type: WorkerType = WorkerType.EXTERNAL,
        employee_id: str | None = None,
        code: str = "",
    ) -> SimpleNamespace:
        employee = self._employee_service.get_employee(employee_id) if employee_id else None
        resource = SimpleNamespace(
            id=f"res-{self._next_id}",
            name=employee.full_name if employee is not None else name,
            role=employee.title if employee is not None else role,
            code=code or f"RES-{self._next_id:04d}",
            hourly_rate=hourly_rate,
            is_active=is_active,
            cost_type=cost_type,
            currency_code=(currency_code or "").strip().upper() or None,
            version=1,
            capacity_percent=capacity_percent,
            address=address,
            contact=(employee.email or employee.phone or "") if employee is not None else contact,
            worker_type=worker_type,
            employee_id=employee_id,
        )
        self._next_id += 1
        self._resources[resource.id] = resource
        return resource

    def get_resource(self, resource_id: str) -> SimpleNamespace:
        return self._resources[resource_id]

    def list_resources_by_ids(self, resource_ids: list[str]) -> list[SimpleNamespace]:
        return [r for r in self._resources.values() if r.id in set(resource_ids)]


class _FakeTaskService:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._assignments: dict[str, TaskAssignment] = {}
        self._next_id = 1

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return [task for task in self._tasks.values() if task.project_id == project_id]

    def create_task(
        self,
        *,
        project_id: str,
        name: str,
        code: str = "",
        description: str = "",
        start_date: date | None = None,
        duration_days: int | None = None,
        priority: int = 0,
        deadline: date | None = None,
    ) -> Task:
        task = Task(
            id=f"task-{self._next_id}",
            project_id=project_id,
            name=name,
            code=code,
            description=description,
            start_date=start_date,
            end_date=_derive_end_date(start_date, duration_days),
            duration_days=duration_days,
            priority=priority,
            deadline=deadline,
        )
        self._next_id += 1
        self._tasks[task.id] = task
        return task

    def create_assignment(
        self,
        *,
        task_id: str,
        resource_id: str,
        allocation_percent: float = 100.0,
        hours_logged: float = 0.0,
    ) -> TaskAssignment:
        assignment = TaskAssignment(
            id=f"assign-{len(self._assignments) + 1}",
            task_id=task_id,
            resource_id=resource_id,
            allocation_percent=allocation_percent,
            hours_logged=hours_logged,
        )
        self._assignments[assignment.id] = assignment
        return assignment

    def list_assignments_for_task(self, task_id: str) -> list[TaskAssignment]:
        return [a for a in self._assignments.values() if a.task_id == task_id]

    def list_assignments_for_tasks(self, task_ids: list[str]) -> list[TaskAssignment]:
        task_id_set = {str(tid) for tid in task_ids}
        return [a for a in self._assignments.values() if a.task_id in task_id_set]

    def get_assignment(self, assignment_id: str) -> TaskAssignment | None:
        return self._assignments.get(assignment_id)

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)


class _FakeTimesheetService:
    def __init__(
        self,
        *,
        task_service: _FakeTaskService,
        resource_service: _FakeResourceService,
    ) -> None:
        self._task_service = task_service
        self._resource_service = resource_service
        self._entries: dict[str, TimeEntry] = {}
        self._periods: dict[tuple[str, date], TimesheetPeriod] = {}

    def list_time_entries_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        return [e for e in self._entries.values() if e.assignment_id == assignment_id]

    def list_time_entries_for_assignment_period(
        self,
        assignment_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        return [
            e for e in self.list_time_entries_for_assignment(assignment_id)
            if e.entry_date.year == period_start.year and e.entry_date.month == period_start.month
        ]

    def list_time_entries_for_resource_period(
        self,
        resource_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        return [
            e for e in self._entries.values()
            if self._resource_id_for_entry(e) == resource_id
            and e.entry_date.year == period_start.year
            and e.entry_date.month == period_start.month
        ]

    def list_timesheet_periods_for_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        return [
            period
            for (current_resource_id, _), period in self._periods.items()
            if current_resource_id == resource_id
        ]

    def get_timesheet_period(self, resource_id: str, *, period_start: date) -> TimesheetPeriod:
        return self._ensure_period(resource_id, period_start)

    def add_time_entry(
        self,
        assignment_id: str,
        *,
        entry_date: date,
        hours: float,
        note: str = "",
    ) -> TimeEntry:
        assignment = self._task_service.get_assignment(assignment_id)
        task = self._task_service.get_task(assignment.task_id) if assignment is not None else None
        entry = TimeEntry(
            id=f"entry-{len(self._entries) + 1}",
            work_allocation_id=assignment_id,
            assignment_id=assignment_id,
            entry_date=entry_date,
            hours=float(hours),
            note=note,
            author_username="alex",
            owner_type="task_assignment",
            owner_id=getattr(task, "id", None),
            owner_label=getattr(task, "name", assignment_id),
            scope_type="project",
            scope_id=getattr(task, "project_id", None),
        )
        self._entries[entry.id] = entry
        self._ensure_period(assignment.resource_id, entry_date.replace(day=1))
        return entry

    def update_time_entry(
        self,
        entry_id: str,
        *,
        entry_date: date | None = None,
        hours: float | None = None,
        note: str | None = None,
    ) -> TimeEntry:
        entry = self._entries[entry_id]
        if entry_date is not None:
            entry.entry_date = entry_date
        if hours is not None:
            entry.hours = float(hours)
        if note is not None:
            entry.note = note
        return entry

    def delete_time_entry(self, entry_id: str) -> None:
        del self._entries[entry_id]

    def submit_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriod:
        period = self._ensure_period(resource_id, period_start)
        period.status = TimesheetPeriodStatus.SUBMITTED
        period.submitted_at = datetime(2026, 5, 4, 17, 0)
        period.submitted_by_username = "alex"
        period.decision_note = note
        return period

    def approve_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        period = self._period_by_id(period_id)
        period.status = TimesheetPeriodStatus.APPROVED
        period.decided_at = datetime(2026, 5, 5, 9, 0)
        period.decided_by_username = "jamie"
        period.decision_note = note
        return period

    def reject_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        period = self._period_by_id(period_id)
        period.status = TimesheetPeriodStatus.REJECTED
        period.decided_at = datetime(2026, 5, 5, 9, 0)
        period.decided_by_username = "jamie"
        period.decision_note = note
        return period

    def lock_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriod:
        period = self._ensure_period(resource_id, period_start)
        period.status = TimesheetPeriodStatus.LOCKED
        period.locked_at = datetime(2026, 5, 6, 18, 0)
        period.decision_note = note
        return period

    def unlock_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        period = self._period_by_id(period_id)
        period.status = TimesheetPeriodStatus.OPEN
        period.decision_note = note
        period.locked_at = None
        return period

    def list_timesheet_review_queue(
        self,
        *,
        status: TimesheetPeriodStatus | None = TimesheetPeriodStatus.SUBMITTED,
        limit: int = 200,
    ) -> list[SimpleNamespace]:
        rows: list[SimpleNamespace] = []
        for period in self._periods.values():
            if status is not None and period.status != status:
                continue
            rows.append(self._build_review_summary(period))
        return rows[:limit]

    def get_timesheet_review_detail(self, period_id: str) -> SimpleNamespace:
        period = self._period_by_id(period_id)
        summary = self._build_review_summary(period)
        entries = self.list_time_entries_for_resource_period(
            period.resource_id,
            period_start=period.period_start,
        )
        review_entries = []
        for entry in entries:
            assignment = self._task_service.get_assignment(entry.assignment_id or "")
            task = self._task_service.get_task(assignment.task_id) if assignment is not None else None
            review_entries.append(
                SimpleNamespace(
                    entry_id=entry.id,
                    entry_date=entry.entry_date,
                    hours=float(entry.hours or 0.0),
                    note=entry.note or "",
                    author_username=entry.author_username,
                    task_name=getattr(task, "name", entry.owner_label or ""),
                    project_id=getattr(task, "project_id", None),
                )
            )
        return SimpleNamespace(summary=summary, entries=tuple(review_entries))

    def _build_review_summary(self, period: TimesheetPeriod) -> SimpleNamespace:
        entries = self.list_time_entries_for_resource_period(
            period.resource_id,
            period_start=period.period_start,
        )
        resource = self._resource_service.get_resource(period.resource_id)
        project_ids = sorted(
            {
                entry.scope_id
                for entry in entries
                if getattr(entry, "scope_type", None) == "project" and getattr(entry, "scope_id", None)
            }
        )
        return SimpleNamespace(
            period_id=period.id,
            resource_id=period.resource_id,
            resource_name=getattr(resource, "name", period.resource_id),
            period_start=period.period_start,
            period_end=period.period_end,
            status=period.status,
            submitted_at=period.submitted_at,
            submitted_by_username=period.submitted_by_username,
            decided_at=period.decided_at,
            decided_by_username=period.decided_by_username,
            decision_note=period.decision_note,
            entry_count=len(entries),
            total_hours=sum(float(entry.hours or 0.0) for entry in entries),
            project_ids=tuple(project_ids),
        )

    def _ensure_period(self, resource_id: str, period_start: date) -> TimesheetPeriod:
        key = (resource_id, period_start)
        if key not in self._periods:
            self._periods[key] = TimesheetPeriod(
                id=f"period-{len(self._periods) + 1}",
                resource_id=resource_id,
                period_start=period_start,
                period_end=_test_period_end(period_start),
            )
        return self._periods[key]

    def _period_by_id(self, period_id: str) -> TimesheetPeriod:
        for period in self._periods.values():
            if period.id == period_id:
                return period
        raise KeyError(period_id)

    def _resource_id_for_entry(self, entry: TimeEntry) -> str | None:
        assignment = self._task_service.get_assignment(entry.assignment_id or "")
        return assignment.resource_id if assignment is not None else None


def _test_period_end(period_start: date) -> date:
    if period_start.month == 12:
        return date.fromordinal(date(period_start.year + 1, 1, 1).toordinal() - 1)
    return date.fromordinal(date(period_start.year, period_start.month + 1, 1).toordinal() - 1)


def _derive_end_date(start_date: date | None, duration_days: int | None) -> date | None:
    if start_date is None or duration_days is None:
        return None
    return start_date + timedelta(days=max(duration_days - 1, 0))
