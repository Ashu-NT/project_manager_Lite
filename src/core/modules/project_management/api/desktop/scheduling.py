from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.scheduling import (
    SchedulingEngine,
)
from src.core.modules.project_management.application.scheduling.constraint_validator import (
    ConstraintValidator,
)
from src.core.modules.project_management.application.scheduling.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.scheduling.schedule_change_impact_service import (
    ScheduleChangeImpactService,
)
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.platform.calendar import WorkCalendarEngine, WorkCalendarService
from src.core.platform.calendar.domain import Holiday, WorkingCalendar


_DAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(frozen=True)
class SchedulingProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class SchedulingCalendarOptionDescriptor:
    value: str
    label: str
    summary_label: str


@dataclass(frozen=True)
class SchedulingDayDescriptor:
    index: int
    label: str
    checked: bool


@dataclass(frozen=True)
class SchedulingHolidayDto:
    id: str
    date: date
    name: str


@dataclass(frozen=True)
class SchedulingTaskDto:
    id: str
    project_id: str
    name: str
    description: str
    status: str
    status_label: str
    start_date: date | None
    finish_date: date | None
    latest_start: date | None
    latest_finish: date | None
    duration_days: int | None
    remaining_duration_days: int | None
    total_float_days: int | None
    is_critical: bool
    deadline: date | None
    late_by_days: int | None
    percent_complete: float
    actual_start: date | None
    actual_end: date | None
    priority: int | None


@dataclass(frozen=True)
class SchedulingDependencyTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class SchedulingProjectDependencyDto:
    id: str
    predecessor_task_id: str
    predecessor_task_name: str
    successor_task_id: str
    successor_task_name: str
    dependency_type: str
    dependency_type_label: str
    lag_days: int


@dataclass(frozen=True)
class SchedulingDependencyDto:
    id: str
    direction: str
    direction_label: str
    related_activity_id: str
    related_activity_name: str
    dependency_type: str
    dependency_type_label: str
    lag_days: int
    relationship_label: str
    status_label: str


@dataclass(frozen=True)
class SchedulingDependencyCreateCommand:
    task_id: str
    related_activity_id: str
    relationship_direction: str
    dependency_type: str = DependencyType.FINISH_TO_START.value
    lag_days: int = 0


@dataclass(frozen=True)
class SchedulingDependencyUpdateCommand:
    dependency_id: str
    dependency_type: str = DependencyType.FINISH_TO_START.value
    lag_days: int = 0


@dataclass(frozen=True)
class SchedulingBaselineOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class SchedulingBaselineRowDto:
    id: str
    name: str
    created_at: date | None
    created_at_label: str
    approved_by_label: str
    variance_state_label: str
    status: str
    status_label: str
    can_submit: bool
    can_approve: bool
    can_reject: bool


@dataclass(frozen=True)
class SchedulingConstraintViolationDto:
    task_id: str
    task_name: str
    constraint_type: str
    constraint_type_label: str
    constraint_date: date | None
    constraint_date_label: str
    computed_date: date | None
    computed_date_label: str
    overrun_working_days: int
    message: str
    severity: str
    severity_label: str


@dataclass(frozen=True)
class SchedulingBaselineSubmitCommand:
    baseline_id: str
    submitted_by: str = "system"
    notes: str = ""


@dataclass(frozen=True)
class SchedulingBaselineApproveCommand:
    baseline_id: str
    approved_by: str = "system"
    notes: str = ""


@dataclass(frozen=True)
class SchedulingBaselineRejectCommand:
    baseline_id: str
    notes: str = ""


@dataclass(frozen=True)
class SchedulingBaselineComparisonRowDto:
    task_id: str
    task_name: str
    change_type: str
    baseline_a_start: date | None
    baseline_a_finish: date | None
    baseline_b_start: date | None
    baseline_b_finish: date | None
    start_shift_days: int | None
    finish_shift_days: int | None
    duration_delta_days: int | None
    planned_cost_delta: float


@dataclass(frozen=True)
class SchedulingBaselineVarianceRowDto:
    id: str
    project_id: str
    new_baseline_id: str
    superseded_baseline_id: str
    task_id: str
    task_name: str
    start_variance_days: int
    finish_variance_days: int
    cost_variance: float
    created_at: date | None


@dataclass(frozen=True)
class SchedulingCalendarSnapshotDto:
    working_days: tuple[SchedulingDayDescriptor, ...]
    hours_per_day: float
    holidays: tuple[SchedulingHolidayDto, ...]


@dataclass(frozen=True)
class SchedulingWorkingDayCalculationDto:
    start_date: date
    working_days: int
    result_date: date
    skipped_non_working_days: int


@dataclass(frozen=True)
class SchedulingCalendarUpdateCommand:
    working_days: tuple[int, ...]
    hours_per_day: float


@dataclass(frozen=True)
class SchedulingHolidayCreateCommand:
    holiday_date: date
    name: str = ""


@dataclass(frozen=True)
class SchedulingWorkingDayCalculationCommand:
    start_date: date
    working_days: int


@dataclass(frozen=True)
class SchedulingBaselineCreateCommand:
    project_id: str
    name: str = "Baseline"


@dataclass(frozen=True)
class SchedulingResourceLoadDto:
    resource_id: str
    resource_name: str
    total_allocation_percent: float
    total_allocation_label: str
    capacity_percent: float
    capacity_label: str
    utilization_percent: float
    utilization_label: str
    tasks_count: int
    status_label: str


@dataclass(frozen=True)
class SchedulingChangeImpactAffectedTaskDto:
    task_id: str
    task_name: str
    start_shift_days: int
    finish_shift_days: int
    is_critical: bool


@dataclass(frozen=True)
class SchedulingChangeImpactDto:
    task_id: str
    affected_count: int
    max_project_finish_shift_days: int
    requires_approval: bool
    newly_critical_count: int
    no_longer_critical_count: int
    affected_tasks: tuple[SchedulingChangeImpactAffectedTaskDto, ...]


class ProjectManagementSchedulingDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        scheduling_engine: SchedulingEngine | None = None,
        platform_calendar_api: object | None = None,
        work_calendar_service: WorkCalendarService | None = None,
        work_calendar_engine: WorkCalendarEngine | None = None,
        baseline_service: BaselineService | None = None,
        reporting_service: ReportingService | None = None,
        change_impact_service: ScheduleChangeImpactService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._scheduling_engine = scheduling_engine
        self._platform_calendar_api = platform_calendar_api
        self._work_calendar_service = work_calendar_service
        self._work_calendar_engine = work_calendar_engine
        self._baseline_service = baseline_service
        self._reporting_service = reporting_service
        self._change_impact_service = change_impact_service

    def list_projects(self) -> tuple[SchedulingProjectOptionDescriptor, ...]:
        if self._project_service is None:
            return ()
        projects = sorted(
            self._project_service.list_projects(),
            key=lambda project: (project.name or "").casefold(),
        )
        return tuple(
            SchedulingProjectOptionDescriptor(value=project.id, label=project.name)
            for project in projects
        )

    def list_calendars(self) -> tuple[SchedulingCalendarOptionDescriptor, ...]:
        if self._platform_calendar_api is not None:
            options = self._unwrap_platform_calendar_result(
                self._platform_calendar_api.list_calendars()
            ) or ()
            return tuple(
                SchedulingCalendarOptionDescriptor(
                    value=option.value,
                    label=option.label,
                    summary_label=option.summary_label,
                )
                for option in options
            )
        calendar = self._get_calendar()
        working_days = set(calendar.working_days or {0, 1, 2, 3, 4})
        active_labels = [
            _DAY_LABELS[index]
            for index in range(7)
            if index in working_days
        ]
        return (
            SchedulingCalendarOptionDescriptor(
                value=str(getattr(calendar, "id", "") or "default"),
                label=str(getattr(calendar, "name", "") or "Default Calendar").strip(),
                summary_label=(
                    f"{', '.join(active_labels) or 'No days'} | "
                    f"{float(calendar.hours_per_day or 8.0):g}h/day"
                ),
            ),
        )

    def get_calendar_snapshot(self) -> SchedulingCalendarSnapshotDto:
        if self._platform_calendar_api is not None:
            snapshot = self._unwrap_platform_calendar_result(
                self._platform_calendar_api.get_calendar_snapshot()
            )
            return SchedulingCalendarSnapshotDto(
                working_days=tuple(
                    SchedulingDayDescriptor(
                        index=day.index,
                        label=day.label,
                        checked=day.checked,
                    )
                    for day in snapshot.working_days
                ),
                hours_per_day=float(snapshot.hours_per_day or 8.0),
                holidays=tuple(
                    SchedulingHolidayDto(
                        id=holiday.id,
                        date=holiday.date,
                        name=holiday.name or "",
                    )
                    for holiday in snapshot.holidays
                ),
            )
        calendar = self._get_calendar()
        holidays = self._list_holidays()
        working_days = set(calendar.working_days or {0, 1, 2, 3, 4})
        return SchedulingCalendarSnapshotDto(
            working_days=tuple(
                SchedulingDayDescriptor(
                    index=day_index,
                    label=_DAY_LABELS[day_index],
                    checked=day_index in working_days,
                )
                for day_index in range(7)
            ),
            hours_per_day=float(calendar.hours_per_day or 8.0),
            holidays=tuple(
                SchedulingHolidayDto(
                    id=holiday.id,
                    date=holiday.date,
                    name=holiday.name or "",
                )
                for holiday in sorted(holidays, key=lambda item: item.date)
            ),
        )

    def update_calendar(
        self,
        command: SchedulingCalendarUpdateCommand,
    ) -> SchedulingCalendarSnapshotDto:
        if self._platform_calendar_api is not None:
            snapshot = self._unwrap_platform_calendar_result(
                self._platform_calendar_api.update_calendar(
                    SimpleNamespace(
                        working_days=command.working_days,
                        hours_per_day=command.hours_per_day,
                    )
                )
            )
            return SchedulingCalendarSnapshotDto(
                working_days=tuple(
                    SchedulingDayDescriptor(
                        index=day.index,
                        label=day.label,
                        checked=day.checked,
                    )
                    for day in snapshot.working_days
                ),
                hours_per_day=float(snapshot.hours_per_day or 8.0),
                holidays=tuple(
                    SchedulingHolidayDto(
                        id=holiday.id,
                        date=holiday.date,
                        name=holiday.name or "",
                    )
                    for holiday in snapshot.holidays
                ),
            )
        service = self._require_work_calendar_service()
        service.set_working_days(
            set(command.working_days),
            hours_per_day=command.hours_per_day,
        )
        return self.get_calendar_snapshot()

    def add_holiday(
        self,
        command: SchedulingHolidayCreateCommand,
    ) -> SchedulingHolidayDto:
        if self._platform_calendar_api is not None:
            holiday = self._unwrap_platform_calendar_result(
                self._platform_calendar_api.add_holiday(
                    SimpleNamespace(
                        holiday_date=command.holiday_date,
                        name=command.name,
                    )
                )
            )
            return SchedulingHolidayDto(
                id=holiday.id,
                date=holiday.date,
                name=holiday.name or "",
            )
        holiday = self._require_work_calendar_service().add_holiday(
            command.holiday_date,
            command.name,
        )
        return SchedulingHolidayDto(
            id=holiday.id,
            date=holiday.date,
            name=holiday.name or "",
        )

    def delete_holiday(self, holiday_id: str) -> None:
        if self._platform_calendar_api is not None:
            self._unwrap_platform_calendar_result(
                self._platform_calendar_api.delete_holiday(holiday_id)
            )
            return
        self._require_work_calendar_service().delete_holiday(holiday_id)

    def calculate_working_days(
        self,
        command: SchedulingWorkingDayCalculationCommand,
    ) -> SchedulingWorkingDayCalculationDto:
        if self._platform_calendar_api is not None:
            result = self._unwrap_platform_calendar_result(
                self._platform_calendar_api.calculate_working_day(
                    SimpleNamespace(
                        start_date=command.start_date,
                        working_days=command.working_days,
                    )
                )
            )
            return SchedulingWorkingDayCalculationDto(
                start_date=result.start_date,
                working_days=result.working_days,
                result_date=result.result_date,
                skipped_non_working_days=result.skipped_non_working_days,
            )
        engine = self._require_work_calendar_engine()
        result_date = engine.add_working_days(command.start_date, command.working_days)
        skipped_non_working = 0
        cursor = command.start_date
        while cursor <= result_date:
            if not engine.is_working_day(cursor):
                skipped_non_working += 1
            cursor = date.fromordinal(cursor.toordinal() + 1)
        return SchedulingWorkingDayCalculationDto(
            start_date=command.start_date,
            working_days=command.working_days,
            result_date=result_date,
            skipped_non_working_days=skipped_non_working,
        )

    def list_dependency_types(self) -> tuple[SchedulingDependencyTypeDescriptor, ...]:
        return tuple(
            SchedulingDependencyTypeDescriptor(
                value=dependency_type.value,
                label=_dependency_type_label(dependency_type),
            )
            for dependency_type in DependencyType
        )

    def list_activity_options(
        self,
        project_id: str,
        *,
        exclude_task_id: str | None = None,
    ) -> tuple[SchedulingProjectOptionDescriptor, ...]:
        normalized_project_id = (project_id or "").strip()
        if not normalized_project_id or self._task_service is None:
            return ()
        excluded = (exclude_task_id or "").strip()
        tasks = sorted(
            self._task_service.list_tasks_for_project(normalized_project_id),
            key=lambda task: (
                task.start_date or date.max,
                (task.name or "").casefold(),
            ),
        )
        return tuple(
            SchedulingProjectOptionDescriptor(value=task.id, label=task.name)
            for task in tasks
            if task.id != excluded
        )

    def list_schedule(self, project_id: str) -> tuple[SchedulingTaskDto, ...]:
        normalized_project_id = (project_id or "").strip()
        if not normalized_project_id:
            return ()
        if self._scheduling_engine is None:
            return self._list_schedule_from_tasks(normalized_project_id)
        schedule = self._scheduling_engine.recalculate_project_schedule(
            normalized_project_id,
            persist=False,
        )
        items = sorted(
            schedule.values(),
            key=lambda info: (
                info.earliest_start or date.max,
                0 if info.is_critical else 1,
                (info.task.name or "").casefold(),
            ),
        )
        return tuple(self._serialize_schedule_item(item) for item in items)

    def recalculate_schedule(self, project_id: str) -> tuple[SchedulingTaskDto, ...]:
        normalized_project_id = (project_id or "").strip()
        if not normalized_project_id:
            raise ValueError("Select a project before recalculating the schedule.")
        engine = self._require_scheduling_engine()
        schedule = engine.recalculate_project_schedule(normalized_project_id, persist=True)
        items = sorted(
            schedule.values(),
            key=lambda info: (
                info.earliest_start or date.max,
                0 if info.is_critical else 1,
                (info.task.name or "").casefold(),
            ),
        )
        return tuple(self._serialize_schedule_item(item) for item in items)

    def list_project_dependencies(
        self,
        project_id: str,
    ) -> tuple[SchedulingProjectDependencyDto, ...]:
        normalized_project_id = (project_id or "").strip()
        if not normalized_project_id:
            return ()
        list_tasks_for_project = self._get_task_method("list_tasks_for_project")
        list_dependencies_for_task = self._get_task_method("list_dependencies_for_task")
        if list_tasks_for_project is None or list_dependencies_for_task is None:
            return ()
        tasks_by_id = {
            task.id: task
            for task in list_tasks_for_project(normalized_project_id)
        }
        dependencies_by_id: dict[str, object] = {}
        for task_id in tasks_by_id:
            for dependency in list_dependencies_for_task(task_id):
                dependencies_by_id[dependency.id] = dependency
        rows = [
            SchedulingProjectDependencyDto(
                id=dependency.id,
                predecessor_task_id=dependency.predecessor_task_id,
                predecessor_task_name=str(
                    getattr(tasks_by_id.get(dependency.predecessor_task_id), "name", "")
                    or dependency.predecessor_task_id
                ),
                successor_task_id=dependency.successor_task_id,
                successor_task_name=str(
                    getattr(tasks_by_id.get(dependency.successor_task_id), "name", "")
                    or dependency.successor_task_id
                ),
                dependency_type=dependency.dependency_type.value,
                dependency_type_label=_dependency_type_label(dependency.dependency_type),
                lag_days=int(getattr(dependency, "lag_days", 0) or 0),
            )
            for dependency in dependencies_by_id.values()
        ]
        rows.sort(
            key=lambda row: (
                row.predecessor_task_name.casefold(),
                row.successor_task_name.casefold(),
                row.dependency_type_label,
            )
        )
        return tuple(rows)

    def list_dependencies(self, task_id: str) -> tuple[SchedulingDependencyDto, ...]:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            return ()
        get_task = self._get_task_method("get_task")
        list_tasks_for_project = self._get_task_method("list_tasks_for_project")
        list_dependencies_for_task = self._get_task_method("list_dependencies_for_task")
        if (
            get_task is None
            or list_tasks_for_project is None
            or list_dependencies_for_task is None
        ):
            return ()
        current_task = get_task(normalized_task_id)
        if current_task is None:
            return ()
        tasks_by_id = {
            task.id: task
            for task in list_tasks_for_project(current_task.project_id)
        }
        rows = [
            self._serialize_dependency(
                dependency,
                current_task_id=current_task.id,
                tasks_by_id=tasks_by_id,
            )
            for dependency in list_dependencies_for_task(normalized_task_id)
            if _dependency_direction(current_task.id, dependency)[0]
        ]
        rows.sort(
            key=lambda row: (
                row.direction != "PREDECESSOR",
                row.related_activity_name.casefold(),
            )
        )
        return tuple(rows)

    def create_dependency(
        self,
        command: SchedulingDependencyCreateCommand,
    ) -> SchedulingDependencyDto:
        relationship_direction = _coerce_dependency_direction(command.relationship_direction)
        predecessor_id = (
            command.related_activity_id
            if relationship_direction == "PREDECESSOR"
            else command.task_id
        )
        successor_id = (
            command.task_id
            if relationship_direction == "PREDECESSOR"
            else command.related_activity_id
        )
        dependency = self._require_task_method("add_dependency")(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=_coerce_dependency_type(command.dependency_type),
            lag_days=command.lag_days,
        )
        current_task = self._require_task_method("get_task")(command.task_id)
        tasks_by_id: dict[str, object] = {}
        if current_task is not None:
            tasks_by_id = {
                task.id: task
                for task in self._require_task_method("list_tasks_for_project")(current_task.project_id)
            }
        return self._serialize_dependency(
            dependency,
            current_task_id=command.task_id,
            tasks_by_id=tasks_by_id,
        )

    def update_dependency(
        self,
        command: SchedulingDependencyUpdateCommand,
        *,
        current_task_id: str,
    ) -> SchedulingDependencyDto:
        dependency = self._require_task_method("update_dependency")(
            command.dependency_id,
            dependency_type=_coerce_dependency_type(command.dependency_type),
            lag_days=command.lag_days,
        )
        current_task = self._require_task_method("get_task")(current_task_id)
        project_id = current_task.project_id if current_task is not None else ""
        tasks_by_id: dict[str, object] = {}
        if project_id:
            tasks_by_id = {
                task.id: task
                for task in self._require_task_method("list_tasks_for_project")(project_id)
            }
        return self._serialize_dependency(
            dependency,
            current_task_id=current_task_id,
            tasks_by_id=tasks_by_id,
        )

    def delete_dependency(self, dependency_id: str) -> None:
        self._require_task_method("remove_dependency")(str(dependency_id or "").strip())

    def list_baselines(
        self,
        project_id: str,
    ) -> tuple[SchedulingBaselineOptionDescriptor, ...]:
        normalized_project_id = (project_id or "").strip()
        if not normalized_project_id or self._baseline_service is None:
            return ()
        baselines = self._baseline_service.list_baselines(normalized_project_id)
        return tuple(
            SchedulingBaselineOptionDescriptor(
                value=baseline.id,
                label=f"{baseline.name} ({baseline.created_at.isoformat()})",
            )
            for baseline in baselines
        )

    def list_baseline_rows(
        self,
        project_id: str,
    ) -> tuple[SchedulingBaselineRowDto, ...]:
        normalized_project_id = (project_id or "").strip()
        if not normalized_project_id or self._baseline_service is None:
            return ()
        baselines = list(self._baseline_service.list_baselines(normalized_project_id))
        baselines.sort(key=lambda baseline: baseline.created_at, reverse=True)
        return tuple(
            _serialize_baseline_row(baseline, index)
            for index, baseline in enumerate(baselines)
        )

    def submit_baseline(self, command: SchedulingBaselineSubmitCommand) -> None:
        self._require_baseline_service().submit_baseline(
            command.baseline_id,
            command.submitted_by,
            command.notes,
        )

    def approve_baseline(self, command: SchedulingBaselineApproveCommand) -> None:
        self._require_baseline_service().approve_baseline(
            command.baseline_id,
            command.approved_by,
            command.notes,
        )

    def reject_baseline(self, command: SchedulingBaselineRejectCommand) -> None:
        self._require_baseline_service().reject_baseline(
            command.baseline_id,
            command.notes,
        )

    def create_baseline(
        self,
        command: SchedulingBaselineCreateCommand,
    ) -> SchedulingBaselineOptionDescriptor:
        baseline = self._require_baseline_service().create_baseline(
            command.project_id,
            command.name,
        )
        return SchedulingBaselineOptionDescriptor(
            value=baseline.id,
            label=f"{baseline.name} ({baseline.created_at.isoformat()})",
        )

    def list_baseline_variance_records(
        self,
        baseline_id: str,
    ) -> tuple[SchedulingBaselineVarianceRowDto, ...]:
        normalized_id = (baseline_id or "").strip()
        if not normalized_id or self._baseline_service is None:
            return ()
        try:
            records = self._baseline_service.list_variance_records(normalized_id)
        except Exception:
            return ()
        return tuple(
            SchedulingBaselineVarianceRowDto(
                id=str(getattr(rec, "id", "") or ""),
                project_id=str(getattr(rec, "project_id", "") or ""),
                new_baseline_id=str(getattr(rec, "new_baseline_id", "") or ""),
                superseded_baseline_id=str(getattr(rec, "superseded_baseline_id", "") or ""),
                task_id=str(getattr(rec, "task_id", "") or ""),
                task_name=str(getattr(rec, "task_name", "") or getattr(rec, "task_id", "")),
                start_variance_days=int(getattr(rec, "start_variance_days", 0) or 0),
                finish_variance_days=int(getattr(rec, "finish_variance_days", 0) or 0),
                cost_variance=float(getattr(rec, "cost_variance", 0.0) or 0.0),
                created_at=(
                    rec.created_at.date()
                    if hasattr(rec.created_at, "date")
                    else getattr(rec, "created_at", None)
                ),
            )
            for rec in records
        )

    def delete_baseline(self, baseline_id: str) -> None:
        self._require_baseline_service().delete_baseline(baseline_id)

    def compare_baselines(
        self,
        *,
        project_id: str,
        baseline_a_id: str,
        baseline_b_id: str,
        include_unchanged: bool = False,
    ) -> tuple[SchedulingBaselineComparisonRowDto, ...]:
        result = self._require_reporting_service().compare_baselines(
            project_id=project_id,
            baseline_a_id=baseline_a_id,
            baseline_b_id=baseline_b_id,
            include_unchanged=include_unchanged,
        )
        return tuple(
            SchedulingBaselineComparisonRowDto(
                task_id=row.task_id,
                task_name=row.task_name,
                change_type=row.change_type,
                baseline_a_start=row.baseline_a_start,
                baseline_a_finish=row.baseline_a_finish,
                baseline_b_start=row.baseline_b_start,
                baseline_b_finish=row.baseline_b_finish,
                start_shift_days=row.start_shift_days,
                finish_shift_days=row.finish_shift_days,
                duration_delta_days=row.duration_delta_days,
                planned_cost_delta=float(row.planned_cost_delta or 0.0),
            )
            for row in result.rows
        )

    def list_resource_load(
        self,
        project_id: str,
    ) -> tuple[SchedulingResourceLoadDto, ...]:
        normalized_project_id = (project_id or "").strip()
        if not normalized_project_id or self._reporting_service is None:
            return ()
        get_resource_load_summary = getattr(
            self._reporting_service,
            "get_resource_load_summary",
            None,
        )
        if not callable(get_resource_load_summary):
            return ()
        rows = get_resource_load_summary(normalized_project_id)
        return tuple(
            SchedulingResourceLoadDto(
                resource_id=row.resource_id,
                resource_name=row.resource_name,
                total_allocation_percent=float(row.total_allocation_percent or 0.0),
                total_allocation_label=f"{float(row.total_allocation_percent or 0.0):.1f}%",
                capacity_percent=float(getattr(row, "capacity_percent", 100.0) or 100.0),
                capacity_label=f"{float(getattr(row, 'capacity_percent', 100.0) or 100.0):.1f}%",
                utilization_percent=float(getattr(row, "utilization_percent", row.total_allocation_percent) or 0.0),
                utilization_label=f"{float(getattr(row, 'utilization_percent', row.total_allocation_percent) or 0.0):.1f}%",
                tasks_count=int(getattr(row, "tasks_count", 0) or 0),
                status_label=_resource_load_status_label(
                    float(getattr(row, "utilization_percent", row.total_allocation_percent) or 0.0)
                ),
            )
            for row in rows
        )

    def list_constraint_violations(
        self,
        project_id: str,
    ) -> tuple[SchedulingConstraintViolationDto, ...]:
        normalized_project_id = (project_id or "").strip()
        if (
            not normalized_project_id
            or self._scheduling_engine is None
            or self._task_service is None
            or self._work_calendar_engine is None
        ):
            return ()
        try:
            schedule = self._scheduling_engine.recalculate_project_schedule(
                normalized_project_id, persist=False
            )
            tasks = self._task_service.list_tasks_for_project(normalized_project_id)
            tasks_by_id = {task.id: task for task in tasks}
            validator = ConstraintValidator(calendar=self._work_calendar_engine)
            result = validator.validate(tasks_by_id, schedule)
            hard_pairs = {
                (v.task_id, v.constraint_type) for v in result.hard_violations
            }
            return tuple(
                SchedulingConstraintViolationDto(
                    task_id=v.task_id,
                    task_name=v.task_name,
                    constraint_type=str(getattr(v.constraint_type, "value", v.constraint_type)),
                    constraint_type_label=str(
                        getattr(v.constraint_type, "value", v.constraint_type)
                    ).replace("_", " ").title(),
                    constraint_date=v.constraint_date,
                    constraint_date_label=(
                        v.constraint_date.isoformat() if v.constraint_date else "-"
                    ),
                    computed_date=v.computed_date,
                    computed_date_label=(
                        v.computed_date.isoformat() if v.computed_date else "-"
                    ),
                    overrun_working_days=int(v.overrun_working_days or 0),
                    message=v.message,
                    severity="hard" if (v.task_id, v.constraint_type) in hard_pairs else "soft",
                    severity_label=(
                        "Hard Constraint"
                        if (v.task_id, v.constraint_type) in hard_pairs
                        else "Soft Constraint"
                    ),
                )
                for v in result.violations
            )
        except Exception:
            return ()

    def _list_schedule_from_tasks(
        self,
        project_id: str,
    ) -> tuple[SchedulingTaskDto, ...]:
        if self._task_service is None:
            return ()
        tasks = sorted(
            self._task_service.list_tasks_for_project(project_id),
            key=lambda task: (
                task.start_date or date.max,
                (task.name or "").casefold(),
            ),
        )
        return tuple(
            SchedulingTaskDto(
                id=task.id,
                project_id=task.project_id,
                name=task.name,
                description=getattr(task, "description", "") or "",
                status=task.status.value,
                status_label=task.status.value.replace("_", " ").title(),
                start_date=task.start_date,
                finish_date=task.end_date,
                latest_start=None,
                latest_finish=None,
                duration_days=getattr(task, "duration_days", None),
                remaining_duration_days=_remaining_duration_days(
                    getattr(task, "duration_days", None),
                    float(task.percent_complete or 0.0),
                ),
                total_float_days=None,
                is_critical=False,
                deadline=getattr(task, "deadline", None),
                late_by_days=None,
                percent_complete=float(task.percent_complete or 0.0),
                actual_start=getattr(task, "actual_start", None),
                actual_end=getattr(task, "actual_end", None),
                priority=getattr(task, "priority", None),
            )
            for task in tasks
        )

    @staticmethod
    def _serialize_schedule_item(item) -> SchedulingTaskDto:
        task = item.task
        return SchedulingTaskDto(
            id=task.id,
            project_id=task.project_id,
            name=task.name,
            description=getattr(task, "description", "") or "",
            status=task.status.value,
            status_label=task.status.value.replace("_", " ").title(),
            start_date=item.earliest_start,
            finish_date=item.earliest_finish,
            latest_start=item.latest_start,
            latest_finish=item.latest_finish,
            duration_days=getattr(task, "duration_days", None),
            remaining_duration_days=_remaining_duration_days(
                getattr(task, "duration_days", None),
                float(task.percent_complete or 0.0),
            ),
            total_float_days=item.total_float_days,
            is_critical=item.is_critical,
            deadline=item.deadline,
            late_by_days=item.late_by_days,
            percent_complete=float(task.percent_complete or 0.0),
            actual_start=getattr(task, "actual_start", None),
            actual_end=getattr(task, "actual_end", None),
            priority=getattr(task, "priority", None),
        )

    def _get_calendar(self) -> WorkingCalendar:
        if self._work_calendar_service is not None:
            return self._work_calendar_service.get_calendar()
        return WorkingCalendar.create_default()

    def _list_holidays(self) -> list[Holiday]:
        if self._work_calendar_service is None:
            return []
        return self._work_calendar_service.list_holidays()

    def _require_work_calendar_service(self) -> WorkCalendarService:
        if self._work_calendar_service is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._work_calendar_service

    def _require_work_calendar_engine(self) -> WorkCalendarEngine:
        if self._work_calendar_engine is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._work_calendar_engine

    @staticmethod
    def _unwrap_platform_calendar_result(result):
        if bool(getattr(result, "ok", False)):
            return getattr(result, "data", None)
        error = getattr(result, "error", None)
        category = str(getattr(error, "category", "") or "").strip().lower()
        message = str(getattr(error, "message", "") or "Platform calendar operation failed.")
        if category == "validation":
            raise ValueError(message)
        if category == "permission":
            raise PermissionError(message)
        if message:
            raise RuntimeError(message)
        raise RuntimeError("Platform calendar operation failed.")

    def _require_scheduling_engine(self) -> SchedulingEngine:
        if self._scheduling_engine is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._scheduling_engine

    def _require_task_service(self) -> TaskService:
        if self._task_service is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._task_service

    def _require_task_method(self, method_name: str):
        service = self._require_task_service()
        method = getattr(service, method_name, None)
        if not callable(method):
            raise RuntimeError(
                f"Project management scheduling desktop API does not support {method_name}."
            )
        return method

    def _get_task_method(self, method_name: str):
        if self._task_service is None:
            return None
        method = getattr(self._task_service, method_name, None)
        if not callable(method):
            return None
        return method

    def _require_baseline_service(self) -> BaselineService:
        if self._baseline_service is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._baseline_service

    def _require_reporting_service(self) -> ReportingService:
        if self._reporting_service is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._reporting_service

    @staticmethod
    def _serialize_dependency(
        dependency,
        *,
        current_task_id: str,
        tasks_by_id: dict[str, object],
    ) -> SchedulingDependencyDto:
        direction, related_activity_id = _dependency_direction(current_task_id, dependency)
        predecessor = tasks_by_id.get(dependency.predecessor_task_id)
        successor = tasks_by_id.get(dependency.successor_task_id)
        predecessor_name = str(
            getattr(predecessor, "name", "") or dependency.predecessor_task_id
        )
        successor_name = str(
            getattr(successor, "name", "") or dependency.successor_task_id
        )
        related_name = str(
            getattr(tasks_by_id.get(related_activity_id), "name", "") or related_activity_id
        )
        return SchedulingDependencyDto(
            id=dependency.id,
            direction=direction,
            direction_label="Predecessor" if direction == "PREDECESSOR" else "Successor",
            related_activity_id=related_activity_id,
            related_activity_name=related_name,
            dependency_type=dependency.dependency_type.value,
            dependency_type_label=_dependency_type_label(dependency.dependency_type),
            lag_days=int(getattr(dependency, "lag_days", 0) or 0),
            relationship_label=f"{predecessor_name} -> {successor_name}",
            status_label="Linked",
        )


    def analyse_change_impact(
        self,
        project_id: str,
        task_id: str,
        proposed_start: "date | None" = None,
        proposed_finish: "date | None" = None,
        proposed_duration_days: "int | None" = None,
    ) -> SchedulingChangeImpactDto | None:
        if not task_id or not project_id or self._change_impact_service is None:
            return None
        try:
            has_baseline = False
            if self._baseline_service is not None:
                try:
                    has_baseline = self._baseline_service.get_approved_baseline(project_id) is not None
                except Exception:
                    pass
            report = self._change_impact_service.analyse(
                project_id=project_id,
                changed_task_id=task_id,
                proposed_start=proposed_start,
                proposed_finish=proposed_finish,
                proposed_duration_days=proposed_duration_days,
                has_approved_baseline=has_baseline,
            )
        except Exception:
            return None
        return SchedulingChangeImpactDto(
            task_id=task_id,
            affected_count=int(report.max_project_finish_shift_days != 0) + len(report.affected_tasks),
            max_project_finish_shift_days=int(report.max_project_finish_shift_days or 0),
            requires_approval=bool(report.requires_approval),
            newly_critical_count=len(report.newly_critical_task_ids or []),
            no_longer_critical_count=len(report.no_longer_critical_task_ids or []),
            affected_tasks=tuple(
                SchedulingChangeImpactAffectedTaskDto(
                    task_id=str(t.task_id or ""),
                    task_name=str(getattr(t, "task_name", t.task_id) or t.task_id or "Task"),
                    start_shift_days=int(getattr(t, "start_shift_days", 0) or 0),
                    finish_shift_days=int(getattr(t, "finish_shift_days", 0) or 0),
                    is_critical=bool(getattr(t, "is_critical", False)),
                )
                for t in (report.affected_tasks or [])[:20]
            ),
        )


def build_project_management_scheduling_desktop_api(
    *,
    project_service: ProjectService | None = None,
    task_service: TaskService | None = None,
    scheduling_engine: SchedulingEngine | None = None,
    platform_calendar_api: object | None = None,
    work_calendar_service: WorkCalendarService | None = None,
    work_calendar_engine: WorkCalendarEngine | None = None,
    baseline_service: BaselineService | None = None,
    reporting_service: ReportingService | None = None,
    change_impact_service: ScheduleChangeImpactService | None = None,
) -> ProjectManagementSchedulingDesktopApi:
    return ProjectManagementSchedulingDesktopApi(
        project_service=project_service,
        task_service=task_service,
        scheduling_engine=scheduling_engine,
        platform_calendar_api=platform_calendar_api,
        work_calendar_service=work_calendar_service,
        work_calendar_engine=work_calendar_engine,
        baseline_service=baseline_service,
        reporting_service=reporting_service,
        change_impact_service=change_impact_service,
    )


def _serialize_baseline_row(baseline, index: int) -> SchedulingBaselineRowDto:
    status_val = str(getattr(baseline.status, "value", baseline.status) or "draft")
    status_label = status_val.replace("_", " ").title()
    return SchedulingBaselineRowDto(
        id=baseline.id,
        name=baseline.name,
        created_at=baseline.created_at.date() if hasattr(baseline.created_at, "date") else baseline.created_at,
        created_at_label=baseline.created_at.strftime("%Y-%m-%d %H:%M"),
        approved_by_label=str(getattr(baseline, "approved_by", "") or "System snapshot"),
        variance_state_label="Latest" if index == 0 else "Stored",
        status=status_val,
        status_label=status_label,
        can_submit=status_val == "draft",
        can_approve=status_val == "submitted",
        can_reject=status_val == "submitted",
    )


def _remaining_duration_days(duration_days: int | None, percent_complete: float) -> int | None:
    if duration_days is None:
        return None
    remaining_ratio = max(0.0, 1.0 - (float(percent_complete or 0.0) / 100.0))
    return max(0, int(round(duration_days * remaining_ratio)))


def _coerce_dependency_direction(value: str | None) -> str:
    normalized = str(value or "PREDECESSOR").strip().upper()
    if normalized in {"PREDECESSOR", "SUCCESSOR"}:
        return normalized
    raise ValueError(f"Unsupported dependency direction: {normalized}.")


def _dependency_direction(current_task_id: str, dependency) -> tuple[str, str]:
    if dependency.successor_task_id == current_task_id:
        return "PREDECESSOR", dependency.predecessor_task_id
    if dependency.predecessor_task_id == current_task_id:
        return "SUCCESSOR", dependency.successor_task_id
    return "", ""


def _coerce_dependency_type(value: str | DependencyType | None) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    normalized_value = str(value or DependencyType.FINISH_TO_START.value).strip().upper()
    try:
        return DependencyType(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported dependency type: {normalized_value}.") from exc


def _dependency_type_label(value: DependencyType | str) -> str:
    dependency_type = value if isinstance(value, DependencyType) else _coerce_dependency_type(value)
    mapping = {
        DependencyType.FINISH_TO_START: "Finish -> Start",
        DependencyType.START_TO_START: "Start -> Start",
        DependencyType.FINISH_TO_FINISH: "Finish -> Finish",
        DependencyType.START_TO_FINISH: "Start -> Finish",
    }
    return mapping.get(dependency_type, dependency_type.value)


def _resource_load_status_label(utilization_percent: float) -> str:
    if utilization_percent > 100.0:
        return "Overloaded"
    if utilization_percent >= 85.0:
        return "Hot"
    if utilization_percent > 0.0:
        return "Stable"
    return "Idle"


__all__ = [
    "ProjectManagementSchedulingDesktopApi",
    "SchedulingBaselineApproveCommand",
    "SchedulingBaselineComparisonRowDto",
    "SchedulingBaselineVarianceRowDto",
    "SchedulingBaselineCreateCommand",
    "SchedulingBaselineOptionDescriptor",
    "SchedulingBaselineRejectCommand",
    "SchedulingBaselineRowDto",
    "SchedulingBaselineSubmitCommand",
    "SchedulingConstraintViolationDto",
    "SchedulingCalendarOptionDescriptor",
    "SchedulingCalendarSnapshotDto",
    "SchedulingCalendarUpdateCommand",
    "SchedulingDayDescriptor",
    "SchedulingDependencyCreateCommand",
    "SchedulingDependencyDto",
    "SchedulingDependencyTypeDescriptor",
    "SchedulingDependencyUpdateCommand",
    "SchedulingHolidayCreateCommand",
    "SchedulingHolidayDto",
    "SchedulingProjectOptionDescriptor",
    "SchedulingProjectDependencyDto",
    "SchedulingResourceLoadDto",
    "SchedulingTaskDto",
    "SchedulingWorkingDayCalculationCommand",
    "SchedulingWorkingDayCalculationDto",
    "build_project_management_scheduling_desktop_api",
]
