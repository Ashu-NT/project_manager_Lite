"""ProjectManagementSchedulingDesktopApi — thin scheduling desktop facade."""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING, Protocol

from src.core.modules.project_management.application.scheduling.baselines.commands.lifecycle import (
    BaselineCommandHandler,
)
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
    ProjectCalendarAdapter,
)

if TYPE_CHECKING:
    from src.core.modules.project_management.domain.scheduling.baseline import (
        BaselineTask,
    )
    from src.core.platform.application.time_management.calendar.capacity.dto.queries.working_days import (
        WorkingDaysCommand,
    )

logger = logging.getLogger(__name__)

from src.core.modules.project_management.api.desktop.common.dependency_presentation import (
    dependency_type_label,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.activity_options_builder import (
    build_activity_options,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.baseline_builder import (
    build_baseline_options,
    build_baseline_rows,
    build_variance_rows,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.calendar_snapshot_builder import (
    build_calendar_options,
    build_calendar_snapshot,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.change_impact_builder import (
    build_change_impact,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.constraint_builder import (
    build_constraint_violations,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.gantt_builder import (
    build_gantt_baseline_overlay as assemble_gantt_baseline_overlay,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.gantt_builder import (
    build_gantt_projection as assemble_gantt_projection,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.gantt_builder import (
    build_hierarchy_nodes,
)
from src.core.modules.project_management.api.desktop.scheduling.builders.project_options_builder import (
    build_project_options,
)
from src.core.modules.project_management.api.desktop.scheduling.models import (
    GanttProjectionDto,
    SchedulingBaselineOptionDescriptor,
    SchedulingBaselineRowDto,
    SchedulingCalendarOptionDescriptor,
    SchedulingCalendarSnapshotDto,
    SchedulingDependencyTypeDescriptor,
    SchedulingProjectOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.scheduling.models.gantt import (
    GanttBaselineOverlayDto,
)
from src.core.modules.project_management.api.desktop.scheduling.services.dependency_resolution_service import (
    get_task_method,
    require_task_method,
)
from src.core.modules.project_management.application.dashboard.models.report_models import (
    ResourceLoadRow,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.application.reporting import (
    BaselineCompareReportBuilder,
    ProjectKpiReportBuilder,
)
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.scheduling.baselines.queries.catalog import (
    BaselineQueryHandler,
)
from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintValidator,
    ConstraintViolation,
)
from src.core.modules.project_management.application.scheduling.dto.commands.baselines import (
    SchedulingBaselineApproveCommand,
    SchedulingBaselineCreateCommand,
    SchedulingBaselineDeleteCommand,
    SchedulingBaselineRejectCommand,
    SchedulingBaselineSubmitCommand,
)
from src.core.modules.project_management.application.scheduling.dto.commands.dependencies import (
    SchedulingDependencyCreateCommand,
    SchedulingDependencyUpdateCommand,
)
from src.core.modules.project_management.application.scheduling.dto.commands.working_days import (
    SchedulingWorkingDayCalculationCommand,
)
from src.core.modules.project_management.application.scheduling.dto.responses.baselines import (
    SchedulingBaselineComparisonRowDto,
    SchedulingBaselineVarianceRowDto,
)
from src.core.modules.project_management.application.scheduling.dto.responses.change_impact import (
    ScheduleImpactReportDto,
    SchedulingChangeImpactDto,
)
from src.core.modules.project_management.application.scheduling.dto.responses.schedule import (
    SchedulingTaskResponse,
)
from src.core.modules.project_management.application.scheduling.forecasting.queries.change_impact import (
    ScheduleChangeImpactQueryHandler,
)
from src.core.modules.project_management.application.scheduling.models.leveling import (
    LevelingProposal,
)
from src.core.modules.project_management.application.scheduling.queries.dependencies import (
    query_project_dependencies,
)
from src.core.modules.project_management.application.scheduling.queries.schedule import (
    query_schedule_responses,
)
from src.core.modules.project_management.application.tasks import (
    ResourceLevelingCommandHandler,
    TaskDependencyCommandHandler,
    TaskDependencyQueryHandler,
    TaskHierarchyQueryHandler,
    TaskLookupQueryHandler,
)
from src.core.modules.project_management.application.tasks.dto.responses.dependency import (
    TaskDependencyResponseDto,
)
from src.core.modules.project_management.application.tasks.queries.task_detail_page import (
    TaskDetailPageQueryHandler,
)
from src.core.modules.project_management.contracts.reads.tasks import (
    TaskDependencyReadItem,
)
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.application.time_management.calendar.dto.responses.working_calendar import (
    WorkingDayCalculationDto,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConfigurationError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)


class _PlatformWorkingDaysApi(Protocol):
    def calculate_working_days(self, command: WorkingDaysCommand) -> object: ...




class ProjectManagementSchedulingDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectQueryHandler | None = None,
        task_lookup_query: TaskLookupQueryHandler | None = None,
        task_detail_query: TaskDetailPageQueryHandler | None = None,
        task_hierarchy_query: TaskHierarchyQueryHandler | None = None,
        task_dependency_query: TaskDependencyQueryHandler | None = None,
        task_dependency_commands: TaskDependencyCommandHandler | None = None,
        task_leveling_commands: ResourceLevelingCommandHandler | None = None,
        scheduling_engine: SchedulingEngine | None = None,
        platform_calendar_api: _PlatformWorkingDaysApi | None = None,
        work_calendar_service=None,
        work_calendar_engine: CalendarProtocol | None = None,
        project_calendar_adapter: ProjectCalendarAdapter | None = None,
        baseline_query: BaselineQueryHandler | None = None,
        baseline_commands: BaselineCommandHandler | None = None,
        baseline_compare_report: BaselineCompareReportBuilder | None = None,
        project_kpi_report: ProjectKpiReportBuilder | None = None,
        change_impact_service: ScheduleChangeImpactQueryHandler | None = None,
        constraint_validator: ConstraintValidator | None = None,
        tenant_context_service: TenantContextService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_lookup_query = task_lookup_query
        self._task_detail_query = task_detail_query
        self._task_hierarchy_query = task_hierarchy_query
        self._task_dependency_query = task_dependency_query
        self._task_dependency_commands = task_dependency_commands
        self._task_leveling_commands = task_leveling_commands
        self._scheduling_engine = scheduling_engine
        self._platform_calendar_api = platform_calendar_api
        self._work_calendar_service = work_calendar_service
        self._work_calendar_engine = work_calendar_engine
        self._project_calendar_adapter = project_calendar_adapter
        self._baseline_query = baseline_query
        self._baseline_commands = baseline_commands
        self._baseline_compare_report = baseline_compare_report
        self._project_kpi_report = project_kpi_report
        self._change_impact_service = change_impact_service
        self._constraint_validator = constraint_validator
        self._tenant_context_service = tenant_context_service
        # Last-previewed leveling proposal per project, keyed so Apply can
        # hand the EXACT snapshot Preview reasoned about back to
        # apply_resource_leveling_plan without a lossy QML round-trip --
        # Apply still revalidates it against a fresh DB read (R4.4L).
        self._pending_leveling_proposals: dict[str, LevelingProposal] = {}

    # ── Project / Activity options ────────────────────────────────────────────

    def list_projects(self) -> tuple[SchedulingProjectOptionDescriptor, ...]:
        return build_project_options(self._project_service)

    def list_activity_options(
        self, project_id: str, *, exclude_task_id: str | None = None
    ) -> tuple[SchedulingProjectOptionDescriptor, ...]:
        return build_activity_options(project_id, self._task_hierarchy_query, exclude_task_id=exclude_task_id)

    # ── Calendar ──────────────────────────────────────────────────────────────

    def list_calendars(self) -> tuple[SchedulingCalendarOptionDescriptor, ...]:
        return build_calendar_options(self._platform_calendar_api, self._work_calendar_service)

    def get_calendar_snapshot(self, calendar_id: str = "") -> SchedulingCalendarSnapshotDto:
        return build_calendar_snapshot(
            self._platform_calendar_api, self._work_calendar_service, calendar_id
        )

    def calculate_working_days(self, command: SchedulingWorkingDayCalculationCommand) -> WorkingDayCalculationDto:
        if self._project_calendar_adapter is None:
            raise ConfigurationError("Project management calendar query is not connected.")
        return self._project_calendar_adapter.calculate_working_days(command)

    # ── Dependencies ──────────────────────────────────────────────────────────

    def list_dependency_types(self) -> tuple[SchedulingDependencyTypeDescriptor, ...]:
        return tuple(
            SchedulingDependencyTypeDescriptor(value=dt.value, label=dependency_type_label(dt))
            for dt in DependencyType
        )

    def list_project_dependencies(self, project_id: str) -> tuple[TaskDependencyResponseDto, ...]:
        normalized_id = (project_id or "").strip()
        if not normalized_id:
            return ()
        if self._task_lookup_query is None or self._task_dependency_query is None:
            return ()
        return query_project_dependencies(
            normalized_id, self._task_dependency_query, self._task_lookup_query,
        )

    def list_dependencies(self, task_id: str) -> tuple[TaskDependencyReadItem, ...]:
        normalized_id = (task_id or "").strip()
        if not normalized_id:
            return ()
        get_task = get_task_method(self._task_detail_query, "get_task")
        if get_task is None or self._task_dependency_query is None:
            return ()
        current = get_task(normalized_id)
        if current is None:
            return ()
        return self._task_dependency_query.query_dependency_responses(normalized_id)

    def create_dependency(self, command: SchedulingDependencyCreateCommand) -> TaskDependencyResponseDto:
        return require_task_method(self._task_dependency_commands, "add_dependency")(
            command
        )

    def update_dependency(self, command: SchedulingDependencyUpdateCommand) -> TaskDependencyResponseDto:
        return require_task_method(self._task_dependency_commands, "update_dependency")(
            command
        )

    def delete_dependency(self, dependency_id: str) -> None:
        require_task_method(self._task_dependency_commands, "remove_dependency")(str(dependency_id or "").strip())

    # ── Schedule ──────────────────────────────────────────────────────────────

    def list_schedule(self, project_id: str) -> tuple[SchedulingTaskResponse, ...]:
        normalized_id = (project_id or "").strip()
        if not normalized_id:
            return ()
        return query_schedule_responses(normalized_id, self._require_scheduling_engine(), persist=False)

    def recalculate_schedule(self, project_id: str) -> tuple[SchedulingTaskResponse, ...]:
        normalized_id = (project_id or "").strip()
        if not normalized_id:
            raise ValidationError("Select a project before recalculating the schedule.", code="PROJECT_ID_REQUIRED")
        return query_schedule_responses(normalized_id, self._require_scheduling_engine(), persist=True)

    def build_gantt_projection(
        self,
        project_id: str,
        *,
        selected_baseline_id: str | None = None,
    ) -> GanttProjectionDto:
        """Build the canonical complete-project Gantt read projection."""
        normalized_id = str(project_id or "").strip()
        if not normalized_id:
            raise ValidationError("Select a project before loading the Gantt projection.", code="PROJECT_ID_REQUIRED")
        scope, project = self._require_gantt_project_scope(normalized_id)

        schedule = query_schedule_responses(
            normalized_id,
            self._require_scheduling_engine(),
            persist=False,
        )
        list_hierarchy = getattr(self._task_hierarchy_query, "list_task_hierarchy", None)
        if callable(list_hierarchy):
            hierarchy = tuple(list_hierarchy(normalized_id))
        else:
            list_tasks = require_task_method(
                self._task_lookup_query, "list_tasks_for_project"
            )
            task_rows = tuple(list_tasks(normalized_id))
            # Lightweight desktop test adapters may expose canonical schedule
            # DTOs without a hierarchy query. The composed hierarchy query uses the
            # authorized hierarchy method above.
            hierarchy = build_hierarchy_nodes(task_rows or schedule)

        dependencies = self.list_project_dependencies(normalized_id)
        baseline_id = str(selected_baseline_id or "").strip()
        baseline_tasks: tuple[BaselineTask, ...] = ()
        if baseline_id:
            baseline_tasks = tuple(
                self._require_baseline_query().list_baseline_tasks(
                    baseline_id,
                    expected_project_id=normalized_id,
                )
            )
        calendar_for_project = getattr(
            self._scheduling_engine, "calendar_for_project", None
        )
        project_calendar = (
            calendar_for_project(normalized_id)
            if callable(calendar_for_project)
            else self._work_calendar_engine
        )
        return assemble_gantt_projection(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=normalized_id,
            hierarchy_nodes=hierarchy,
            schedule_items=schedule,
            dependency_rows=dependencies,
            baseline_tasks=baseline_tasks,
            selected_baseline_id=baseline_id or None,
            project_start=getattr(project, "start_date", None),
            project_finish=getattr(project, "end_date", None),
            work_calendar=project_calendar,
        )

    def build_gantt_baseline_overlay(
        self,
        project_id: str,
        baseline_id: str,
    ) -> GanttBaselineOverlayDto:
        """Read one authorized baseline snapshot without rebuilding schedule state."""
        normalized_project_id = str(project_id or "").strip()
        normalized_baseline_id = str(baseline_id or "").strip()
        if not normalized_project_id:
            raise ValidationError("Select a project before loading a Gantt baseline.", code="PROJECT_ID_REQUIRED")
        if not normalized_baseline_id:
            raise ValidationError("Select a baseline before loading its Gantt overlay.", code="BASELINE_ID_REQUIRED")
        scope, _project = self._require_gantt_project_scope(normalized_project_id)
        snapshots = self._require_baseline_query().list_baseline_tasks(
            normalized_baseline_id,
            expected_project_id=normalized_project_id,
        )
        return assemble_gantt_baseline_overlay(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=normalized_project_id,
            baseline_id=normalized_baseline_id,
            baseline_tasks=snapshots,
        )

    def _require_gantt_project_scope(self, project_id: str):
        if self._tenant_context_service is None:
            raise ConfigurationError(
                "Project management Gantt API requires TenantContextService."
            )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project Gantt"
        )
        get_project = getattr(self._project_service, "get_project", None)
        project = get_project(project_id) if callable(get_project) else None
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        project_tenant_id = str(getattr(project, "tenant_id", "") or "")
        project_organization_id = str(getattr(project, "organization_id", "") or "")
        if (
            project_tenant_id and project_tenant_id != scope.tenant_id
        ) or (
            project_organization_id and project_organization_id != scope.organization_id
        ):
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        return scope, project

    # ── Baselines ─────────────────────────────────────────────────────────────

    def list_baselines(self, project_id: str) -> tuple[SchedulingBaselineOptionDescriptor, ...]:
        return build_baseline_options((project_id or "").strip(), self._baseline_query)

    def list_baseline_rows(self, project_id: str) -> tuple[SchedulingBaselineRowDto, ...]:
        return build_baseline_rows((project_id or "").strip(), self._baseline_query)

    def create_baseline(self, command: SchedulingBaselineCreateCommand) -> SchedulingBaselineOptionDescriptor:
        baseline = self._require_baseline_commands().create_baseline(command)
        return SchedulingBaselineOptionDescriptor(
            value=baseline.id, label=f"{baseline.name} ({baseline.created_at.isoformat()})"
        )

    def submit_baseline(self, command: SchedulingBaselineSubmitCommand) -> None:
        self._require_baseline_commands().submit_baseline(command)

    def approve_baseline(self, command: SchedulingBaselineApproveCommand) -> None:
        self._require_baseline_commands().approve_baseline(command)

    def reject_baseline(self, command: SchedulingBaselineRejectCommand) -> None:
        self._require_baseline_commands().reject_baseline(command)

    def delete_baseline(self, command: SchedulingBaselineDeleteCommand) -> None:
        self._require_baseline_commands().delete_baseline(command)

    def list_baseline_variance_records(self, baseline_id: str) -> tuple[SchedulingBaselineVarianceRowDto, ...]:
        return build_variance_rows((baseline_id or "").strip(), self._baseline_query)

    def compare_baselines(
        self, *, project_id: str, baseline_a_id: str, baseline_b_id: str, include_unchanged: bool = False
    ) -> tuple[SchedulingBaselineComparisonRowDto, ...]:
        result = self._require_baseline_compare_report().compare_baseline_responses(
            project_id=project_id, baseline_a_id=baseline_a_id,
            baseline_b_id=baseline_b_id, include_unchanged=include_unchanged,
        )
        return result

    # ── Resources ─────────────────────────────────────────────────────────────

    def list_resource_load(self, project_id: str) -> list[ResourceLoadRow]:
        normalized_id = (project_id or "").strip()
        if not normalized_id or self._project_kpi_report is None:
            return []
        return self._project_kpi_report.get_resource_load_summary(normalized_id)

    # ── Resource leveling ─────────────────────────────────────────────────────

    def preview_resource_leveling(self, project_id: str) -> LevelingProposal:
        normalized_id = (project_id or "").strip()
        empty = LevelingProposal(normalized_id, "", True, 0, 0, (), (), None, None, False, (), ())
        if not normalized_id or self._task_leveling_commands is None:
            return empty
        proposal = require_task_method(
            self._task_leveling_commands, "build_resource_leveling_preview"
        )(normalized_id)
        if proposal is None:
            return empty
        # Cached on this instance rather than round-tripped through QML --
        # Apply revalidates it against a fresh DB snapshot anyway (R4.4L),
        # so QML only ever needs the display DTO, not the raw domain moves.
        self._pending_leveling_proposals[normalized_id] = proposal
        return proposal

    def apply_resource_leveling(self, project_id: str) -> tuple[SchedulingTaskResponse, ...]:
        normalized_id = (project_id or "").strip()
        if not normalized_id:
            raise ValidationError("Select a project before applying resource leveling.", code="PROJECT_ID_REQUIRED")
        proposal = self._pending_leveling_proposals.pop(normalized_id, None)
        if proposal is None:
            raise BusinessRuleError("Preview resource leveling before applying it.", code="LEVELING_PREVIEW_REQUIRED")
        require_task_method(self._task_leveling_commands, "apply_resource_leveling_plan")(normalized_id, proposal)
        return self.list_schedule(normalized_id)

    # ── Constraints ───────────────────────────────────────────────────────────

    def list_constraint_violations(self, project_id: str) -> tuple[ConstraintViolation, ...]:
        return build_constraint_violations(
            (project_id or "").strip(),
            scheduling_engine=self._scheduling_engine,
            task_service=self._task_lookup_query,
            constraint_validator=self._constraint_validator,
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
        )

    def preview_task_schedule_impact(
        self,
        task_id: str,
        project_id: str,
        *,
        delay_working_days: int = 1,
    ) -> ScheduleImpactReportDto:
        """Same working-day-delay simulation Task Detail's Schedule Impact
        uses (`ProjectManagementTasksDesktopApi.preview_task_schedule_impact`),
        exposed here so the Gantt Inspector's "Analyze Impact" trigger can
        call the richer, already-existing serialization (critical-path
        change, conflict count, blocked-by-deadline) instead of
        analyse_change_impact's narrower DTO -- same core
        ScheduleChangeImpactQueryHandler, no new schedule-impact math."""
        normalized_task_id = str(task_id or "").strip()
        normalized_project_id = str(project_id or "").strip()
        unavailable = ScheduleImpactReportDto(
            task_id=normalized_task_id,
            project_id=normalized_project_id,
            simulated_delay_days=delay_working_days,
            is_available=False,
            affected_count=0,
            max_project_finish_shift_days=0,
            requires_approval=False,
            affected_tasks=(),
            newly_critical_task_ids=(),
            no_longer_critical_task_ids=(),
        )
        if (
            not normalized_task_id
            or not normalized_project_id
            or self._task_detail_query is None
            or self._change_impact_service is None
        ):
            return unavailable
        try:
            task = self._task_detail_query.get_task(normalized_task_id)
            if task is None or task.start_date is None:
                return unavailable
            report = self._change_impact_service.analyse_working_day_delay(
                project_id=normalized_project_id,
                changed_task_id=normalized_task_id,
                current_start=task.start_date,
                delay_working_days=delay_working_days,
            )
        except Exception:
            logger.exception(
                "preview_task_schedule_impact failed (task_id=%s, project_id=%s, delay_working_days=%s)",
                normalized_task_id,
                normalized_project_id,
                delay_working_days,
            )
            return unavailable
        return report

    # ── Internal guards ───────────────────────────────────────────────────────

    def _require_scheduling_engine(self) -> SchedulingEngine:
        if self._scheduling_engine is None:
            raise ConfigurationError("Project management scheduling desktop API is not connected.")
        return self._scheduling_engine

    def _require_work_calendar_engine(self) -> CalendarProtocol:
        if self._work_calendar_engine is None:
            raise ConfigurationError("Project management scheduling desktop API is not connected.")
        return self._work_calendar_engine

    def _require_baseline_query(self) -> BaselineQueryHandler:
        if self._baseline_query is None:
            raise ConfigurationError("Project management scheduling desktop API is not connected.")
        return self._baseline_query

    def _require_baseline_commands(self) -> BaselineCommandHandler:
        if self._baseline_commands is None:
            raise ConfigurationError("Project management baselines are not connected.")
        return self._baseline_commands

    def _require_baseline_compare_report(self) -> BaselineCompareReportBuilder:
        if self._baseline_compare_report is None:
            raise ConfigurationError("Project management scheduling desktop API is not connected.")
        return self._baseline_compare_report


__all__ = ["ProjectManagementSchedulingDesktopApi"]
