from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ResourceService,
    TimesheetService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.platform.time.application import TimesheetReviewDetail
from src.core.platform.time.domain import TimesheetPeriodStatus


@dataclass(frozen=True)
class TimesheetOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TimesheetProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TimesheetAssignmentOptionDescriptor:
    value: str
    label: str
    project_id: str
    project_name: str
    task_id: str
    task_name: str
    resource_id: str
    resource_name: str


@dataclass(frozen=True)
class TimesheetPeriodOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TimesheetEntryDesktopDto:
    entry_id: str
    assignment_id: str
    entry_date: date
    entry_date_label: str
    hours: float
    hours_label: str
    note: str
    author_username: str


@dataclass(frozen=True)
class TimesheetPeriodSummaryDesktopDto:
    period_id: str
    resource_id: str
    resource_name: str
    period_start: date
    period_start_label: str
    period_end_label: str
    status: str
    status_label: str
    submitted_by_username: str
    submitted_at_label: str
    decided_by_username: str
    decided_at_label: str
    decision_note: str
    entry_count: int
    total_hours: float
    total_hours_label: str
    project_names: tuple[str, ...]


@dataclass(frozen=True)
class TimesheetReviewEntryDesktopDto:
    entry_id: str
    entry_date_label: str
    project_name: str
    task_name: str
    hours_label: str
    author_username: str
    note: str


@dataclass(frozen=True)
class TimesheetReviewDetailDesktopDto:
    summary: TimesheetPeriodSummaryDesktopDto
    entries: tuple[TimesheetReviewEntryDesktopDto, ...]


@dataclass(frozen=True)
class TimesheetAssignmentSnapshotDesktopDto:
    assignment: TimesheetAssignmentOptionDescriptor
    period_options: tuple[TimesheetPeriodOptionDescriptor, ...]
    selected_period_start: str
    period_summary: TimesheetPeriodSummaryDesktopDto
    entries: tuple[TimesheetEntryDesktopDto, ...]
    resource_period_total_hours_label: str
    scope_summary: str


@dataclass(frozen=True)
class TimesheetEntryCreateCommand:
    assignment_id: str
    entry_date: date
    hours: float
    note: str = ""


@dataclass(frozen=True)
class TimesheetEntryUpdateCommand:
    entry_id: str
    entry_date: date | None = None
    hours: float | None = None
    note: str | None = None


class ProjectManagementTimesheetsDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        resource_service: ResourceService | None = None,
        timesheet_service: TimesheetService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._resource_service = resource_service
        self._timesheet_service = timesheet_service

    def list_projects(self) -> tuple[TimesheetProjectOptionDescriptor, ...]:
        if self._project_service is None:
            return ()
        projects = sorted(
            self._project_service.list_projects(),
            key=lambda project: (project.name or "").casefold(),
        )
        return tuple(
            TimesheetProjectOptionDescriptor(value=project.id, label=project.name)
            for project in projects
        )

    def list_queue_statuses(self) -> tuple[TimesheetOptionDescriptor, ...]:
        return (
            TimesheetOptionDescriptor(value="all", label="All statuses"),
            *(
                TimesheetOptionDescriptor(
                    value=status.value,
                    label=status.value.replace("_", " ").title(),
                )
                for status in TimesheetPeriodStatus
            ),
        )

    def list_assignments(
        self,
        *,
        project_id: str | None = None,
    ) -> tuple[TimesheetAssignmentOptionDescriptor, ...]:
        if self._task_service is None or self._project_service is None:
            return ()
        project_lookup = {
            project.id: project
            for project in self._project_service.list_projects()
        }
        project_ids = (
            [str(project_id or "").strip()]
            if str(project_id or "").strip()
            else [project.id for project in project_lookup.values()]
        )
        options: list[TimesheetAssignmentOptionDescriptor] = []
        for current_project_id in project_ids:
            if current_project_id not in project_lookup:
                continue
            tasks = self._task_service.list_tasks_for_project(current_project_id)
            if not tasks:
                continue
            assignments = self._task_service.list_assignments_for_tasks(
                [task.id for task in tasks]
            )
            task_lookup = {task.id: task for task in tasks}
            for assignment in assignments:
                task = task_lookup.get(assignment.task_id)
                if task is None:
                    continue
                resource = (
                    self._resource_service.get_resource(assignment.resource_id)
                    if self._resource_service is not None
                    else None
                )
                project = project_lookup[current_project_id]
                resource_name = getattr(resource, "name", assignment.resource_id)
                label = f"{project.name} | {task.name} | {resource_name}"
                options.append(
                    TimesheetAssignmentOptionDescriptor(
                        value=assignment.id,
                        label=label,
                        project_id=current_project_id,
                        project_name=project.name,
                        task_id=task.id,
                        task_name=task.name,
                        resource_id=assignment.resource_id,
                        resource_name=resource_name,
                    )
                )
        options.sort(key=lambda option: option.label.casefold())
        return tuple(options)

    def build_assignment_snapshot(
        self,
        assignment_id: str,
        *,
        period_start: date | None = None,
    ) -> TimesheetAssignmentSnapshotDesktopDto:
        assignment = self._require_task_service().get_assignment(
            str(assignment_id or "").strip()
        )
        if assignment is None:
            raise RuntimeError("The selected task assignment could not be found.")
        task = self._require_task_service().get_task(assignment.task_id)
        if task is None:
            raise RuntimeError("The selected assignment task could not be found.")
        project = (
            self._project_service.get_project(task.project_id)
            if self._project_service is not None
            else None
        )
        resource = (
            self._resource_service.get_resource(assignment.resource_id)
            if self._resource_service is not None
            else None
        )
        assignment_option = TimesheetAssignmentOptionDescriptor(
            value=assignment.id,
            label=" | ".join(
                value
                for value in (
                    getattr(project, "name", task.project_id),
                    task.name,
                    getattr(resource, "name", assignment.resource_id),
                )
                if value
            ),
            project_id=task.project_id,
            project_name=getattr(project, "name", task.project_id),
            task_id=task.id,
            task_name=task.name,
            resource_id=assignment.resource_id,
            resource_name=getattr(resource, "name", assignment.resource_id),
        )
        selected_period_start = period_start or self._default_period_start(assignment.id)
        period_options = self._build_period_options(
            assignment.id,
            resource_id=assignment.resource_id,
        )
        if not period_options:
            period_options = (
                TimesheetPeriodOptionDescriptor(
                    value=selected_period_start.isoformat(),
                    label=_period_label(selected_period_start),
                ),
            )
        if not any(option.value == selected_period_start.isoformat() for option in period_options):
            selected_period_start = date.fromisoformat(period_options[0].value)
        task_entries = self._require_timesheet_service().list_time_entries_for_assignment_period(
            assignment.id,
            period_start=selected_period_start,
        )
        resource_entries = self._require_timesheet_service().list_time_entries_for_resource_period(
            assignment.resource_id,
            period_start=selected_period_start,
        )
        period = self._require_timesheet_service().get_timesheet_period(
            assignment.resource_id,
            period_start=selected_period_start,
        )
        period_summary = self._serialize_period_summary(
            period=period,
            resource_id=assignment.resource_id,
            resource_name=assignment_option.resource_name,
            period_start=selected_period_start,
            entries=resource_entries,
            project_names=(
                assignment_option.project_name,
            ),
        )
        return TimesheetAssignmentSnapshotDesktopDto(
            assignment=assignment_option,
            period_options=period_options,
            selected_period_start=selected_period_start.isoformat(),
            period_summary=period_summary,
            entries=tuple(self._serialize_entry(entry, assignment.id) for entry in task_entries),
            resource_period_total_hours_label=_format_hours(
                sum(float(entry.hours or 0.0) for entry in resource_entries)
            ),
            scope_summary=(
                f"Task period entries: {len(task_entries)} | Resource month total: "
                f"{_format_hours(sum(float(entry.hours or 0.0) for entry in resource_entries))}"
            ),
        )

    def list_review_queue(
        self,
        *,
        status: str = TimesheetPeriodStatus.SUBMITTED.value,
    ) -> tuple[TimesheetPeriodSummaryDesktopDto, ...]:
        service = self._timesheet_service
        if service is None:
            return ()
        normalized_status = _coerce_queue_status(status)
        rows = service.list_timesheet_review_queue(status=normalized_status, limit=200)
        return tuple(self._serialize_review_summary(row) for row in rows)

    def get_review_detail(self, period_id: str) -> TimesheetReviewDetailDesktopDto:
        detail = self._require_timesheet_service().get_timesheet_review_detail(
            str(period_id or "").strip()
        )
        return self._serialize_review_detail(detail)

    def add_time_entry(self, command: TimesheetEntryCreateCommand) -> TimesheetEntryDesktopDto:
        entry = self._require_timesheet_service().add_time_entry(
            str(command.assignment_id or "").strip(),
            entry_date=command.entry_date,
            hours=float(command.hours),
            note=command.note,
        )
        return self._serialize_entry(entry, str(command.assignment_id or "").strip())

    def update_time_entry(self, command: TimesheetEntryUpdateCommand) -> TimesheetEntryDesktopDto:
        entry = self._require_timesheet_service().update_time_entry(
            str(command.entry_id or "").strip(),
            entry_date=command.entry_date,
            hours=command.hours,
            note=command.note,
        )
        return self._serialize_entry(
            entry,
            str(getattr(entry, "assignment_id", "") or getattr(entry, "work_allocation_id", "")),
        )

    def delete_time_entry(self, entry_id: str) -> None:
        self._require_timesheet_service().delete_time_entry(str(entry_id or "").strip())

    def submit_period(
        self,
        *,
        resource_id: str,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        period = self._require_timesheet_service().submit_timesheet_period(
            str(resource_id or "").strip(),
            period_start=period_start,
            note=note,
        )
        return self._serialize_period_from_service(period)

    def approve_period(
        self,
        period_id: str,
        *,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        period = self._require_timesheet_service().approve_timesheet_period(
            str(period_id or "").strip(),
            note=note,
        )
        return self._serialize_period_from_service(period)

    def reject_period(
        self,
        period_id: str,
        *,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        period = self._require_timesheet_service().reject_timesheet_period(
            str(period_id or "").strip(),
            note=note,
        )
        return self._serialize_period_from_service(period)

    def lock_period(
        self,
        *,
        resource_id: str,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        period = self._require_timesheet_service().lock_timesheet_period(
            str(resource_id or "").strip(),
            period_start=period_start,
            note=note,
        )
        return self._serialize_period_from_service(period)

    def unlock_period(
        self,
        period_id: str,
        *,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        period = self._require_timesheet_service().unlock_timesheet_period(
            str(period_id or "").strip(),
            note=note,
        )
        return self._serialize_period_from_service(period)

    def _build_period_options(
        self,
        assignment_id: str,
        *,
        resource_id: str,
    ) -> tuple[TimesheetPeriodOptionDescriptor, ...]:
        entries = self._require_timesheet_service().list_time_entries_for_assignment(assignment_id)
        known_periods = {
            _period_start(entry.entry_date)
            for entry in entries
        }
        known_periods.update(
            period.period_start
            for period in self._require_timesheet_service().list_timesheet_periods_for_resource(
                resource_id
            )
        )
        ordered_periods = sorted(known_periods, reverse=True)
        return tuple(
            TimesheetPeriodOptionDescriptor(
                value=period_start.isoformat(),
                label=_period_label(period_start),
            )
            for period_start in ordered_periods
        )

    def _default_period_start(self, assignment_id: str) -> date:
        entries = self._require_timesheet_service().list_time_entries_for_assignment(
            assignment_id
        )
        target_date = max((entry.entry_date for entry in entries), default=date.today())
        return _period_start(target_date)

    def _serialize_period_from_service(self, period) -> TimesheetPeriodSummaryDesktopDto:
        resource_entries = self._require_timesheet_service().list_time_entries_for_resource_period(
            period.resource_id,
            period_start=period.period_start,
        )
        resource = (
            self._resource_service.get_resource(period.resource_id)
            if self._resource_service is not None
            else None
        )
        project_names = tuple(self._project_names_for_entries(resource_entries))
        return self._serialize_period_summary(
            period=period,
            resource_id=period.resource_id,
            resource_name=getattr(resource, "name", period.resource_id),
            period_start=period.period_start,
            entries=resource_entries,
            project_names=project_names,
        )

    def _serialize_review_summary(self, row) -> TimesheetPeriodSummaryDesktopDto:
        return TimesheetPeriodSummaryDesktopDto(
            period_id=row.period_id,
            resource_id=row.resource_id,
            resource_name=row.resource_name,
            period_start=row.period_start,
            period_start_label=_period_label(row.period_start),
            period_end_label=row.period_end.isoformat(),
            status=row.status.value,
            status_label=row.status.value.replace("_", " ").title(),
            submitted_by_username=row.submitted_by_username or "-",
            submitted_at_label=_format_datetime(row.submitted_at),
            decided_by_username=row.decided_by_username or "-",
            decided_at_label=_format_datetime(row.decided_at),
            decision_note=row.decision_note or "",
            entry_count=int(row.entry_count or 0),
            total_hours=float(row.total_hours or 0.0),
            total_hours_label=_format_hours(row.total_hours),
            project_names=tuple(self._project_names_from_ids(row.project_ids)),
        )

    def _serialize_review_detail(
        self,
        detail: TimesheetReviewDetail,
    ) -> TimesheetReviewDetailDesktopDto:
        return TimesheetReviewDetailDesktopDto(
            summary=self._serialize_review_summary(detail.summary),
            entries=tuple(
                TimesheetReviewEntryDesktopDto(
                    entry_id=entry.entry_id,
                    entry_date_label=entry.entry_date.isoformat(),
                    project_name=self._project_name_for_id(entry.project_id),
                    task_name=entry.task_name or "-",
                    hours_label=_format_hours(entry.hours),
                    author_username=entry.author_username or "unknown",
                    note=entry.note or "",
                )
                for entry in detail.entries
            ),
        )

    def _serialize_period_summary(
        self,
        *,
        period,
        resource_id: str,
        resource_name: str,
        period_start: date,
        entries,
        project_names: tuple[str, ...],
    ) -> TimesheetPeriodSummaryDesktopDto:
        if period is None:
            status = TimesheetPeriodStatus.OPEN
            period_id = ""
            submitted_by_username = "-"
            submitted_at_label = "-"
            decided_by_username = "-"
            decided_at_label = "-"
            decision_note = ""
            period_end_label = _period_end(period_start).isoformat()
        else:
            status = period.status
            period_id = period.id
            submitted_by_username = period.submitted_by_username or "-"
            submitted_at_label = _format_datetime(period.submitted_at)
            decided_by_username = period.decided_by_username or "-"
            decided_at_label = _format_datetime(period.decided_at)
            decision_note = period.decision_note or ""
            period_end_label = period.period_end.isoformat()
        return TimesheetPeriodSummaryDesktopDto(
            period_id=period_id,
            resource_id=resource_id,
            resource_name=resource_name,
            period_start=period_start,
            period_start_label=_period_label(period_start),
            period_end_label=period_end_label,
            status=status.value,
            status_label=status.value.replace("_", " ").title(),
            submitted_by_username=submitted_by_username,
            submitted_at_label=submitted_at_label,
            decided_by_username=decided_by_username,
            decided_at_label=decided_at_label,
            decision_note=decision_note,
            entry_count=len(entries),
            total_hours=float(sum(float(entry.hours or 0.0) for entry in entries)),
            total_hours_label=_format_hours(sum(float(entry.hours or 0.0) for entry in entries)),
            project_names=tuple(project_names),
        )

    @staticmethod
    def _serialize_entry(entry, assignment_id: str) -> TimesheetEntryDesktopDto:
        return TimesheetEntryDesktopDto(
            entry_id=entry.id,
            assignment_id=assignment_id,
            entry_date=entry.entry_date,
            entry_date_label=entry.entry_date.isoformat(),
            hours=float(entry.hours or 0.0),
            hours_label=_format_hours(entry.hours),
            note=entry.note or "",
            author_username=entry.author_username or "unknown",
        )

    def _project_names_from_ids(self, project_ids) -> tuple[str, ...]:
        names = [self._project_name_for_id(project_id) for project_id in project_ids or ()]
        return tuple(name for name in names if name)

    def _project_names_for_entries(self, entries) -> tuple[str, ...]:
        project_names = {
            self._project_name_for_id(getattr(entry, "scope_id", None))
            for entry in entries
            if getattr(entry, "scope_type", None) == "project"
        }
        return tuple(sorted(name for name in project_names if name))

    def _project_name_for_id(self, project_id: str | None) -> str:
        normalized_id = str(project_id or "").strip()
        if not normalized_id or self._project_service is None:
            return normalized_id
        project = self._project_service.get_project(normalized_id)
        return getattr(project, "name", normalized_id)

    def _require_task_service(self) -> TaskService:
        if self._task_service is None:
            raise RuntimeError("Project management timesheets desktop API is not connected.")
        return self._task_service

    def _require_timesheet_service(self) -> TimesheetService:
        if self._timesheet_service is None:
            raise RuntimeError("Project management timesheets desktop API is not connected.")
        return self._timesheet_service


def build_project_management_timesheets_desktop_api(
    *,
    project_service: ProjectService | None = None,
    task_service: TaskService | None = None,
    resource_service: ResourceService | None = None,
    timesheet_service: TimesheetService | None = None,
) -> ProjectManagementTimesheetsDesktopApi:
    return ProjectManagementTimesheetsDesktopApi(
        project_service=project_service,
        task_service=task_service,
        resource_service=resource_service,
        timesheet_service=timesheet_service,
    )


def _coerce_queue_status(value: str) -> TimesheetPeriodStatus | None:
    normalized_value = str(value or "all").strip().upper()
    if not normalized_value or normalized_value == "ALL":
        return None
    try:
        return TimesheetPeriodStatus(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported timesheet queue status: {normalized_value}.") from exc


def _period_start(target_date: date) -> date:
    return target_date.replace(day=1)


def _period_end(period_start: date) -> date:
    if period_start.month == 12:
        return date.fromordinal(date(period_start.year + 1, 1, 1).toordinal() - 1)
    return date.fromordinal(
        date(period_start.year, period_start.month + 1, 1).toordinal() - 1
    )


def _period_label(period_start: date) -> str:
    return period_start.strftime("%b %Y")


def _format_hours(value: float | None) -> str:
    return f"{float(value or 0.0):.2f}h"


def _format_datetime(value) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


__all__ = [
    "ProjectManagementTimesheetsDesktopApi",
    "TimesheetAssignmentOptionDescriptor",
    "TimesheetAssignmentSnapshotDesktopDto",
    "TimesheetEntryCreateCommand",
    "TimesheetEntryDesktopDto",
    "TimesheetEntryUpdateCommand",
    "TimesheetOptionDescriptor",
    "TimesheetPeriodOptionDescriptor",
    "TimesheetPeriodSummaryDesktopDto",
    "TimesheetProjectOptionDescriptor",
    "TimesheetReviewDetailDesktopDto",
    "TimesheetReviewEntryDesktopDto",
    "build_project_management_timesheets_desktop_api",
]
