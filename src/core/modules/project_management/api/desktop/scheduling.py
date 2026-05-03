from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.scheduling import (
    SchedulingEngine,
    WorkCalendarEngine,
    WorkCalendarService,
)
from src.core.modules.project_management.application.scheduling.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.modules.project_management.domain.scheduling.calendar import Holiday, WorkingCalendar


_DAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(frozen=True)
class SchedulingProjectOptionDescriptor:
    value: str
    label: str


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
    status: str
    status_label: str
    start_date: date | None
    finish_date: date | None
    latest_start: date | None
    latest_finish: date | None
    total_float_days: int | None
    is_critical: bool
    deadline: date | None
    late_by_days: int | None
    percent_complete: float


@dataclass(frozen=True)
class SchedulingBaselineOptionDescriptor:
    value: str
    label: str


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


class ProjectManagementSchedulingDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        scheduling_engine: SchedulingEngine | None = None,
        work_calendar_service: WorkCalendarService | None = None,
        work_calendar_engine: WorkCalendarEngine | None = None,
        baseline_service: BaselineService | None = None,
        reporting_service: ReportingService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._scheduling_engine = scheduling_engine
        self._work_calendar_service = work_calendar_service
        self._work_calendar_engine = work_calendar_engine
        self._baseline_service = baseline_service
        self._reporting_service = reporting_service

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

    def get_calendar_snapshot(self) -> SchedulingCalendarSnapshotDto:
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
        self._require_work_calendar_service().delete_holiday(holiday_id)

    def calculate_working_days(
        self,
        command: SchedulingWorkingDayCalculationCommand,
    ) -> SchedulingWorkingDayCalculationDto:
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
                status=task.status.value,
                status_label=task.status.value.replace("_", " ").title(),
                start_date=task.start_date,
                finish_date=task.end_date,
                latest_start=None,
                latest_finish=None,
                total_float_days=None,
                is_critical=False,
                deadline=task.deadline,
                late_by_days=None,
                percent_complete=float(task.percent_complete or 0.0),
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
            status=task.status.value,
            status_label=task.status.value.replace("_", " ").title(),
            start_date=item.earliest_start,
            finish_date=item.earliest_finish,
            latest_start=item.latest_start,
            latest_finish=item.latest_finish,
            total_float_days=item.total_float_days,
            is_critical=item.is_critical,
            deadline=item.deadline,
            late_by_days=item.late_by_days,
            percent_complete=float(task.percent_complete or 0.0),
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

    def _require_scheduling_engine(self) -> SchedulingEngine:
        if self._scheduling_engine is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._scheduling_engine

    def _require_baseline_service(self) -> BaselineService:
        if self._baseline_service is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._baseline_service

    def _require_reporting_service(self) -> ReportingService:
        if self._reporting_service is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._reporting_service


def build_project_management_scheduling_desktop_api(
    *,
    project_service: ProjectService | None = None,
    task_service: TaskService | None = None,
    scheduling_engine: SchedulingEngine | None = None,
    work_calendar_service: WorkCalendarService | None = None,
    work_calendar_engine: WorkCalendarEngine | None = None,
    baseline_service: BaselineService | None = None,
    reporting_service: ReportingService | None = None,
) -> ProjectManagementSchedulingDesktopApi:
    return ProjectManagementSchedulingDesktopApi(
        project_service=project_service,
        task_service=task_service,
        scheduling_engine=scheduling_engine,
        work_calendar_service=work_calendar_service,
        work_calendar_engine=work_calendar_engine,
        baseline_service=baseline_service,
        reporting_service=reporting_service,
    )


__all__ = [
    "ProjectManagementSchedulingDesktopApi",
    "SchedulingBaselineComparisonRowDto",
    "SchedulingBaselineCreateCommand",
    "SchedulingBaselineOptionDescriptor",
    "SchedulingCalendarSnapshotDto",
    "SchedulingCalendarUpdateCommand",
    "SchedulingDayDescriptor",
    "SchedulingHolidayCreateCommand",
    "SchedulingHolidayDto",
    "SchedulingProjectOptionDescriptor",
    "SchedulingTaskDto",
    "SchedulingWorkingDayCalculationCommand",
    "SchedulingWorkingDayCalculationDto",
    "build_project_management_scheduling_desktop_api",
]
