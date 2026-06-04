"""ProjectManagementSchedulingDesktopApi — thin scheduling desktop facade."""

from __future__ import annotations
from datetime import date
from types import SimpleNamespace

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import BaselineService
from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import ScheduleChangeImpactService
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.infrastructure.reporting import ReportingService

from src.core.modules.project_management.api.desktop.scheduling.models import (
    SchedulingBaselineComparisonRowDto,
    SchedulingBaselineOptionDescriptor,
    SchedulingBaselineRowDto,
    SchedulingBaselineVarianceRowDto,
    SchedulingCalendarOptionDescriptor,
    SchedulingCalendarSnapshotDto,
    SchedulingChangeImpactDto,
    SchedulingConstraintViolationDto,
    SchedulingDependencyDto,
    SchedulingDependencyTypeDescriptor,
    SchedulingHolidayDto,
    SchedulingProjectDependencyDto,
    SchedulingProjectOptionDescriptor,
    SchedulingResourceLoadDto,
    SchedulingTaskDto,
    SchedulingWorkingDayCalculationDto,
)
from src.core.modules.project_management.api.desktop.scheduling.commands.dependency_commands import (
    SchedulingDependencyCreateCommand,
    SchedulingDependencyUpdateCommand,
)
from src.core.modules.project_management.api.desktop.scheduling.commands.baseline_commands import (
    SchedulingBaselineApproveCommand,
    SchedulingBaselineCreateCommand,
    SchedulingBaselineRejectCommand,
    SchedulingBaselineSubmitCommand,
)
from src.core.modules.project_management.api.desktop.scheduling.commands.calendar_commands import (
    SchedulingCalendarUpdateCommand,
    SchedulingHolidayCreateCommand,
)
from src.core.modules.project_management.api.desktop.scheduling.commands.working_day_commands import (
    SchedulingWorkingDayCalculationCommand,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.project_options_builder import build_project_options
from src.core.modules.project_management.api.desktop.scheduling.builders.activity_options_builder import build_activity_options
from src.core.modules.project_management.api.desktop.scheduling.builders.calendar_snapshot_builder import (
    build_calendar_options,
    build_calendar_snapshot,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.baseline_builder import (
    build_baseline_options,
    build_baseline_rows,
    build_variance_rows,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.resource_load_builder import build_resource_load
from src.core.modules.project_management.api.desktop.scheduling.builders.constraint_builder import build_constraint_violations
from src.core.modules.project_management.api.desktop.scheduling.builders.change_impact_builder import build_change_impact
from src.core.modules.project_management.api.desktop.scheduling.serializers.dependency_serializer import serialize_dependency
from src.core.modules.project_management.api.desktop.scheduling.services.calendar_adapter_service import unwrap_platform_calendar_result
from src.core.modules.project_management.api.desktop.scheduling.services.dependency_resolution_service import (
    build_tasks_by_id,
    get_task_method,
    require_task_method,
)
from src.core.modules.project_management.api.desktop.scheduling.services.scheduling_facade_service import (
    build_schedule_from_engine,
    build_schedule_from_tasks,
)
from src.core.modules.project_management.api.desktop.scheduling.formatters.dependency_formatter import dependency_type_label
from src.core.modules.project_management.api.desktop.scheduling.utils.dependency_utils import (
    coerce_dependency_direction,
    coerce_dependency_type,
    dependency_direction,
)


class ProjectManagementSchedulingDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        scheduling_engine: SchedulingEngine | None = None,
        platform_calendar_api: object | None = None,
        work_calendar_service=None,
        work_calendar_engine: CalendarProtocol | None = None,
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

    # ── Project / Activity options ────────────────────────────────────────────

    def list_projects(self) -> tuple[SchedulingProjectOptionDescriptor, ...]:
        return build_project_options(self._project_service)

    def list_activity_options(
        self, project_id: str, *, exclude_task_id: str | None = None
    ) -> tuple[SchedulingProjectOptionDescriptor, ...]:
        return build_activity_options(project_id, self._task_service, exclude_task_id=exclude_task_id)

    # ── Calendar ──────────────────────────────────────────────────────────────

    def list_calendars(self) -> tuple[SchedulingCalendarOptionDescriptor, ...]:
        return build_calendar_options(self._platform_calendar_api, self._work_calendar_service)

    def get_calendar_snapshot(self) -> SchedulingCalendarSnapshotDto:
        return build_calendar_snapshot(self._platform_calendar_api, self._work_calendar_service)

    def update_calendar(self, command: SchedulingCalendarUpdateCommand) -> SchedulingCalendarSnapshotDto:
        # Calendar editing moved to Platform Admin → Calendar Management.
        # Stub kept for QML compatibility during transition.
        return self.get_calendar_snapshot()

    def add_holiday(self, command: SchedulingHolidayCreateCommand) -> SchedulingHolidayDto:
        # Holiday management moved to Platform Admin → Calendar Management.
        from datetime import datetime as _dt
        return SchedulingHolidayDto(
            id="",
            date=command.holiday_date if hasattr(command, "holiday_date") else _dt.today().date(),
            name=getattr(command, "name", ""),
        )

    def delete_holiday(self, holiday_id: str) -> None:
        pass  # Holiday management moved to Platform Admin → Calendar Management.

    def calculate_working_days(self, command: SchedulingWorkingDayCalculationCommand) -> SchedulingWorkingDayCalculationDto:
        if self._platform_calendar_api is not None:
            result = unwrap_platform_calendar_result(
                self._platform_calendar_api.calculate_working_day(
                    SimpleNamespace(start_date=command.start_date, working_days=command.working_days)
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
        skipped = sum(
            1 for cursor in _date_range(command.start_date, result_date)
            if not engine.is_working_day(cursor)
        )
        return SchedulingWorkingDayCalculationDto(
            start_date=command.start_date,
            working_days=command.working_days,
            result_date=result_date,
            skipped_non_working_days=skipped,
        )

    # ── Dependencies ──────────────────────────────────────────────────────────

    def list_dependency_types(self) -> tuple[SchedulingDependencyTypeDescriptor, ...]:
        return tuple(
            SchedulingDependencyTypeDescriptor(value=dt.value, label=dependency_type_label(dt))
            for dt in DependencyType
        )

    def list_project_dependencies(self, project_id: str) -> tuple[SchedulingProjectDependencyDto, ...]:
        normalized_id = (project_id or "").strip()
        if not normalized_id:
            return ()
        list_tasks = get_task_method(self._task_service, "list_tasks_for_project")
        list_deps = get_task_method(self._task_service, "list_dependencies_for_task")
        if list_tasks is None or list_deps is None:
            return ()
        tasks_by_id = {t.id: t for t in list_tasks(normalized_id)}
        dependencies_by_id: dict[str, object] = {}
        for task_id in tasks_by_id:
            for dep in list_deps(task_id):
                dependencies_by_id[dep.id] = dep
        rows = [
            SchedulingProjectDependencyDto(
                id=dep.id,
                predecessor_task_id=dep.predecessor_task_id,
                predecessor_task_name=str(getattr(tasks_by_id.get(dep.predecessor_task_id), "name", "") or dep.predecessor_task_id),
                successor_task_id=dep.successor_task_id,
                successor_task_name=str(getattr(tasks_by_id.get(dep.successor_task_id), "name", "") or dep.successor_task_id),
                dependency_type=dep.dependency_type.value,
                dependency_type_label=dependency_type_label(dep.dependency_type),
                lag_days=int(getattr(dep, "lag_days", 0) or 0),
            )
            for dep in dependencies_by_id.values()
        ]
        rows.sort(key=lambda r: (r.predecessor_task_name.casefold(), r.successor_task_name.casefold(), r.dependency_type_label))
        return tuple(rows)

    def list_dependencies(self, task_id: str) -> tuple[SchedulingDependencyDto, ...]:
        normalized_id = (task_id or "").strip()
        if not normalized_id:
            return ()
        get_task = get_task_method(self._task_service, "get_task")
        list_tasks = get_task_method(self._task_service, "list_tasks_for_project")
        list_deps = get_task_method(self._task_service, "list_dependencies_for_task")
        if not all([get_task, list_tasks, list_deps]):
            return ()
        current = get_task(normalized_id)
        if current is None:
            return ()
        tasks_by_id = {t.id: t for t in list_tasks(current.project_id)}
        rows = [
            serialize_dependency(dep, current_task_id=current.id, tasks_by_id=tasks_by_id)
            for dep in list_deps(normalized_id)
            if dependency_direction(current.id, dep)[0]
        ]
        rows.sort(key=lambda r: (r.direction != "PREDECESSOR", r.related_activity_name.casefold()))
        return tuple(rows)

    def create_dependency(self, command: SchedulingDependencyCreateCommand) -> SchedulingDependencyDto:
        direction = coerce_dependency_direction(command.relationship_direction)
        predecessor_id = command.related_activity_id if direction == "PREDECESSOR" else command.task_id
        successor_id = command.task_id if direction == "PREDECESSOR" else command.related_activity_id
        dependency = require_task_method(self._task_service, "add_dependency")(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=coerce_dependency_type(command.dependency_type),
            lag_days=command.lag_days,
        )
        current = require_task_method(self._task_service, "get_task")(command.task_id)
        tasks_by_id = build_tasks_by_id(self._task_service, current.project_id if current else "")
        return serialize_dependency(dependency, current_task_id=command.task_id, tasks_by_id=tasks_by_id)

    def update_dependency(self, command: SchedulingDependencyUpdateCommand, *, current_task_id: str) -> SchedulingDependencyDto:
        dependency = require_task_method(self._task_service, "update_dependency")(
            command.dependency_id,
            dependency_type=coerce_dependency_type(command.dependency_type),
            lag_days=command.lag_days,
        )
        current = require_task_method(self._task_service, "get_task")(current_task_id)
        tasks_by_id = build_tasks_by_id(self._task_service, current.project_id if current else "")
        return serialize_dependency(dependency, current_task_id=current_task_id, tasks_by_id=tasks_by_id)

    def delete_dependency(self, dependency_id: str) -> None:
        require_task_method(self._task_service, "remove_dependency")(str(dependency_id or "").strip())

    # ── Schedule ──────────────────────────────────────────────────────────────

    def list_schedule(self, project_id: str) -> tuple[SchedulingTaskDto, ...]:
        normalized_id = (project_id or "").strip()
        if not normalized_id:
            return ()
        if self._scheduling_engine is None:
            return build_schedule_from_tasks(normalized_id, self._task_service)
        return build_schedule_from_engine(normalized_id, self._scheduling_engine, persist=False)

    def recalculate_schedule(self, project_id: str) -> tuple[SchedulingTaskDto, ...]:
        normalized_id = (project_id or "").strip()
        if not normalized_id:
            raise ValueError("Select a project before recalculating the schedule.")
        return build_schedule_from_engine(normalized_id, self._require_scheduling_engine(), persist=True)

    # ── Baselines ─────────────────────────────────────────────────────────────

    def list_baselines(self, project_id: str) -> tuple[SchedulingBaselineOptionDescriptor, ...]:
        return build_baseline_options((project_id or "").strip(), self._baseline_service)

    def list_baseline_rows(self, project_id: str) -> tuple[SchedulingBaselineRowDto, ...]:
        return build_baseline_rows((project_id or "").strip(), self._baseline_service)

    def create_baseline(self, command: SchedulingBaselineCreateCommand) -> SchedulingBaselineOptionDescriptor:
        baseline = self._require_baseline_service().create_baseline(command.project_id, command.name)
        return SchedulingBaselineOptionDescriptor(
            value=baseline.id, label=f"{baseline.name} ({baseline.created_at.isoformat()})"
        )

    def submit_baseline(self, command: SchedulingBaselineSubmitCommand) -> None:
        self._require_baseline_service().submit_baseline(command.baseline_id, command.submitted_by, command.notes)

    def approve_baseline(self, command: SchedulingBaselineApproveCommand) -> None:
        self._require_baseline_service().approve_baseline(command.baseline_id, command.approved_by, command.notes)

    def reject_baseline(self, command: SchedulingBaselineRejectCommand) -> None:
        self._require_baseline_service().reject_baseline(command.baseline_id, command.notes)

    def delete_baseline(self, baseline_id: str) -> None:
        self._require_baseline_service().delete_baseline(baseline_id)

    def list_baseline_variance_records(self, baseline_id: str) -> tuple[SchedulingBaselineVarianceRowDto, ...]:
        return build_variance_rows((baseline_id or "").strip(), self._baseline_service)

    def compare_baselines(
        self, *, project_id: str, baseline_a_id: str, baseline_b_id: str, include_unchanged: bool = False
    ) -> tuple[SchedulingBaselineComparisonRowDto, ...]:
        result = self._require_reporting_service().compare_baselines(
            project_id=project_id, baseline_a_id=baseline_a_id,
            baseline_b_id=baseline_b_id, include_unchanged=include_unchanged,
        )
        return tuple(
            SchedulingBaselineComparisonRowDto(
                task_id=row.task_id, task_name=row.task_name, change_type=row.change_type,
                baseline_a_start=row.baseline_a_start, baseline_a_finish=row.baseline_a_finish,
                baseline_b_start=row.baseline_b_start, baseline_b_finish=row.baseline_b_finish,
                start_shift_days=row.start_shift_days, finish_shift_days=row.finish_shift_days,
                duration_delta_days=row.duration_delta_days,
                planned_cost_delta=float(row.planned_cost_delta or 0.0),
            )
            for row in result.rows
        )

    # ── Resources ─────────────────────────────────────────────────────────────

    def list_resource_load(self, project_id: str) -> tuple[SchedulingResourceLoadDto, ...]:
        return build_resource_load((project_id or "").strip(), self._reporting_service)

    # ── Constraints ───────────────────────────────────────────────────────────

    def list_constraint_violations(self, project_id: str) -> tuple[SchedulingConstraintViolationDto, ...]:
        return build_constraint_violations(
            (project_id or "").strip(),
            scheduling_engine=self._scheduling_engine,
            task_service=self._task_service,
            work_calendar_engine=self._work_calendar_engine,
        )

    # ── Change impact ─────────────────────────────────────────────────────────

    def analyse_change_impact(
        self,
        project_id: str,
        task_id: str,
        proposed_start: date | None = None,
        proposed_finish: date | None = None,
        proposed_duration_days: int | None = None,
    ) -> SchedulingChangeImpactDto | None:
        return build_change_impact(
            project_id, task_id,
            proposed_start, proposed_finish, proposed_duration_days,
            change_impact_service=self._change_impact_service,
            baseline_service=self._baseline_service,
        )

    # ── Internal guards ───────────────────────────────────────────────────────

    def _require_scheduling_engine(self) -> SchedulingEngine:
        if self._scheduling_engine is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._scheduling_engine

    def _require_work_calendar_engine(self) -> CalendarProtocol:
        if self._work_calendar_engine is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._work_calendar_engine

    def _require_baseline_service(self) -> BaselineService:
        if self._baseline_service is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._baseline_service

    def _require_reporting_service(self) -> ReportingService:
        if self._reporting_service is None:
            raise RuntimeError("Project management scheduling desktop API is not connected.")
        return self._reporting_service


def _date_range(start: date, end: date):
    cursor = start
    while cursor <= end:
        yield cursor
        cursor = date.fromordinal(cursor.toordinal() + 1)


__all__ = ["ProjectManagementSchedulingDesktopApi"]
