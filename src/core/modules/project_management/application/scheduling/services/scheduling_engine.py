# src/core/modules/project_management/application/scheduling/engine.py
from __future__ import annotations

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import ResourceRepository
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.modules.project_management.application.scheduling.cpm.task_date_math import (
    apply_actual_date_constraints,
    apply_scheduling_constraints,
    compute_duration_dates,
    compute_milestone_dates,
)
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_dependencies, select_leaf_tasks
# CalendarResolver removed — enterprise CalendarResolver handles hierarchy resolution
CalendarResolver = None  # type: ignore[assignment]  # kept for isinstance checks
from src.core.modules.project_management.application.scheduling.cpm.date_compute import (
    compute_task_dates_common,
)
from src.core.modules.project_management.application.scheduling.cpm.graph import (
    build_project_dependency_graph,
)
from src.core.modules.project_management.application.scheduling.leveling.leveling_mixin import (
    ResourceLevelingMixin,
)
from src.core.modules.project_management.application.scheduling.models.cpm import CPMTaskInfo
from src.core.modules.project_management.application.scheduling.cpm.passes import (
    run_backward_pass,
    run_forward_pass,
)
from src.core.modules.project_management.application.scheduling.cpm.results import (
    build_schedule_result,
)
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
    BoundProjectCalendar,
    ProjectCalendarAdapter,
)
from src.core.modules.project_management.application.scheduling.calendars.working_day_snapshot import (
    WorkingDaySnapshotCalendar,
)


class SchedulingEngine(ResourceLevelingMixin):
    """
    CPM-style scheduling engine:
    - Forward pass: ES/EF
    - Backward pass: LS/LF
    - FS, FF, SS, SF with lag_days
    - Scheduling constraints: MSO, MFO, SNET, FNET applied during forward pass
    - Per-resource calendar overrides via CalendarResolver
    """

    def __init__(
        self,
        session: Session,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        calendar: CalendarProtocol,
        assignment_repo: AssignmentRepository | None = None,
        resource_repo: ResourceRepository | None = None,
        calendar_resolver: CalendarResolver | None = None,
        resource_calendar_map: dict[str, CalendarProtocol] | None = None,
        project_calendar_adapter: ProjectCalendarAdapter | None = None,
    ):
        self._session: Session = session
        self._task_repo: TaskRepository = task_repo
        self._dependency_repo: DependencyRepository = dependency_repo
        self._base_calendar: CalendarProtocol = calendar  # never mutated; restored after each run
        self._calendar: CalendarProtocol = calendar
        self._task_calendar: CalendarProtocol = calendar  # per-task override, reset each pass
        self._assignment_repo: AssignmentRepository | None = assignment_repo
        self._resource_repo: ResourceRepository | None = resource_repo
        self._calendar_resolver: CalendarResolver | None = calendar_resolver
        self._resource_calendar_map: dict[str, CalendarProtocol] = resource_calendar_map or {}
        self._task_primary_resource: dict[str, str] = {}  # task_id → resource_id, pre-loaded per run
        self._project_calendar_adapter: ProjectCalendarAdapter | None = project_calendar_adapter
        # task_id -> (dependency-implied ES, EF), captured before any hard
        # constraint override -- reset each run, read by ConstraintValidator
        # via CPMTaskInfo.dependency_implied_start/finish (Phase F).
        self._dependency_implied_dates: dict[str, tuple[date | None, date | None]] = {}

    def calendar_for_project(self, project_id: str) -> CalendarProtocol:
        if self._project_calendar_adapter is not None:
            try:
                calendar = self._project_calendar_adapter.bind_for_project(project_id)
                if calendar is not None:
                    return calendar
            except Exception:
                logger.warning(
                    "Project calendar resolution failed for project_id=%s; "
                    "falling back to the global calendar. Scheduling dates "
                    "computed under this fallback may differ from what the "
                    "project's own enterprise calendar would produce.",
                    project_id,
                    exc_info=True,
                )
        return self._base_calendar

    def recalculate_project_schedule(
        self,
        project_id: str,
        *,
        persist: bool = True,
        commit: bool = True,
    ) -> dict[str, CPMTaskInfo]:
        """
        Full CPM calculation for a project:
        - computes ES/EF (forward) and LS/LF (backward)
        - applies scheduling constraints (MSO/MFO/SNET/FNET) during forward pass
        - applies per-resource calendar overrides when CalendarResolver is wired
        - updates Task.start_date / Task.end_date from ES/EF
        - returns CPMTaskInfo per task
        """
        tasks = select_leaf_tasks(self._task_repo.list_by_project(project_id))
        if not tasks:
            return {}

        tasks_by_id: dict[str, Task] = {t.id: t for t in tasks}
        # Baseline for the changed-tasks-only persist below (Phase L1) --
        # captured before any forward-pass patching (e.g. unanchored-root
        # default-start patching) can replace entries in tasks_by_id.
        original_dates = {t.id: (t.start_date, t.end_date) for t in tasks}
        deps = select_leaf_dependencies(
            self._dependency_repo.list_by_project(project_id),
            tasks,
        )
        self._dependency_implied_dates = {}

        # If a project has an enterprise calendar assignment, bind the adapter so all
        # CPM arithmetic uses that calendar instead of the global WorkCalendarEngine.
        if self._project_calendar_adapter is not None:
            try:
                bound = self._project_calendar_adapter.bind_for_project(project_id)
                if bound is not None:
                    calendar = self._build_working_day_snapshot(
                        bound,
                        tasks=tasks,
                        dependencies=deps,
                    )
                    self._calendar = calendar
                    self._task_calendar = calendar
            except Exception:
                # Fall back to the global calendar -- but this is a real
                # degradation (the computed schedule may differ from what
                # the project's own enterprise calendar would produce), so
                # it must be observable, not silent. See
                # docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
                # §7/Phase E.
                logger.warning(
                    "Project calendar snapshot build failed for project_id=%s; "
                    "recalculating with the global calendar instead.",
                    project_id,
                    exc_info=True,
                )

        # Pre-load task→primary_resource for per-task calendar resolution
        if self._calendar_resolver and self._assignment_repo and self._resource_calendar_map:
            task_ids = list(tasks_by_id)
            assignments = self._assignment_repo.list_by_tasks(task_ids)
            self._task_primary_resource = {}
            for a in assignments:
                if a.task_id not in self._task_primary_resource:
                    self._task_primary_resource[a.task_id] = a.resource_id

        topo_order, deps_by_successor, deps_by_predecessor = build_project_dependency_graph(
            tasks_by_id=tasks_by_id,
            deps=deps,
            priority_value=self._priority_value,
        )

        es, ef, project_early_finish = run_forward_pass(
            tasks_by_id=tasks_by_id,
            topo_order=topo_order,
            deps_by_successor=deps_by_successor,
            compute_task_dates=self._compute_task_dates,
        )
        ls, lf = run_backward_pass(
            tasks_by_id=tasks_by_id,
            topo_order=topo_order,
            deps_by_predecessor=deps_by_predecessor,
            es=es,
            ef=ef,
            project_early_finish=project_early_finish,
            calendar=self._calendar,
        )

        result = build_schedule_result(
            tasks_by_id=tasks_by_id,
            es=es,
            ef=ef,
            ls=ls,
            lf=lf,
            calendar=self._calendar,
            dependency_implied=self._dependency_implied_dates,
        )

        # Reset per-run state — restore base calendar so multi-project calls don't cross-contaminate
        self._task_primary_resource = {}
        self._calendar = self._base_calendar
        self._task_calendar = self._base_calendar
        self._dependency_implied_dates = {}

        if persist:
            try:
                # Phase L1: only write tasks whose persisted schedule
                # fields (start_date/end_date -- the only fields
                # build_schedule_result ever mutates) actually changed.
                # Previously every leaf task in the project was written
                # unconditionally on every single recalculation, correlating
                # DB write volume with project size rather than with how
                # much the schedule actually moved.
                for task_id, info in result.items():
                    if original_dates.get(task_id) == (info.task.start_date, info.task.end_date):
                        continue
                    self._task_repo.update(info.task)
                if commit:
                    self._session.commit()
                else:
                    self._session.flush()
            except Exception:
                if commit:
                    self._session.rollback()
                raise

        return result

    @staticmethod
    def _build_working_day_snapshot(
        calendar: BoundProjectCalendar,
        *,
        tasks: list[Task],
        dependencies: list[TaskDependency],
    ) -> WorkingDaySnapshotCalendar:
        anchors = [
            value
            for task in tasks
            for value in (
                task.start_date,
                task.end_date,
                task.deadline,
                task.constraint_date,
            )
            if value is not None
        ]
        today = date.today()
        earliest = min(anchors, default=today)
        latest = max(anchors, default=today)
        work_span = sum(max(1, int(task.duration_days or 1)) for task in tasks)
        work_span += sum(abs(int(dependency.lag_days or 0)) + 1 for dependency in dependencies)
        padding_days = max(60, min((work_span * 3) + 30, 3_650))
        start = earliest - timedelta(days=padding_days)
        end = latest + timedelta(days=padding_days)
        return WorkingDaySnapshotCalendar(
            start=start,
            end=end,
            working_dates=calendar.working_day_dates_between(start, end),
            fallback=calendar,
        )

    def _compute_task_dates(
        self,
        task: Task,
        incoming_deps: list[TaskDependency],
        es: dict[str, date | None],
        ef: dict[str, date | None],
    ) -> tuple[date | None, date | None]:
        self._task_calendar = self._resolve_task_calendar(task.id)

        def _capture_dependency_implied(dep_est, dep_eft):
            if incoming_deps:
                # Pure dependency-graph result, captured BEFORE actuals or
                # this task's own hard constraints get a chance to override
                # it -- ConstraintValidator compares this against the final
                # result to report a DEPENDENCY_CONSTRAINT_CONFLICT instead
                # of a constraint override being silent (Phase F), and it
                # is also the basis for actual-vs-planned variance
                # reporting (Phase J). Must be captured pre-actual: a task
                # with its own actual_start already folded in would not be
                # a useful basis for asking "did this task's actual
                # execution violate what its dependency graph required."
                self._dependency_implied_dates[task.id] = (dep_est, dep_eft)

        est, eft = compute_task_dates_common(
            task=task,
            incoming_deps=incoming_deps,
            es=es,
            ef=ef,
            compute_milestone=self._compute_dates_milestone,
            compute_with_duration=self._compute_dates_with_duration,
            apply_actual_constraints=self._apply_actual_constraints,
            on_dependency_implied=_capture_dependency_implied,
        )
        return self._apply_scheduling_constraints(task, est, eft)

    def _resolve_task_calendar(self, task_id: str) -> CalendarProtocol:
        """Return the highest-priority calendar for a task's primary resource."""
        if not self._calendar_resolver or not self._resource_calendar_map:
            return self._calendar
        resource_id = self._task_primary_resource.get(task_id)
        if not resource_id:
            return self._calendar
        resource_cal = self._resource_calendar_map.get(resource_id)
        return self._calendar_resolver.resolve_for_resource(
            resource_calendar=resource_cal,
            project_calendar=self._calendar,
        )

    def _apply_scheduling_constraints(
        self,
        task: Task,
        est: date | None,
        eft: date | None,
    ) -> tuple[date | None, date | None]:
        return apply_scheduling_constraints(self._task_calendar, task, est, eft)

    def _compute_dates_milestone(
        self,
        task: Task,
        incoming_deps: list[TaskDependency],
        es: dict[str, date | None],
        ef: dict[str, date | None],
    ) -> tuple[date | None, date | None]:
        return compute_milestone_dates(self._task_calendar, task, incoming_deps, es, ef)

    def _compute_dates_with_duration(
        self,
        task: Task,
        incoming_deps: list[TaskDependency],
        es: dict[str, date | None],
        ef: dict[str, date | None],
        duration: int,
    ) -> tuple[date | None, date | None]:
        return compute_duration_dates(self._task_calendar, task, incoming_deps, es, ef, duration)

    def _apply_actual_constraints(
        self,
        task: Task,
        est: date | None,
        eft: date | None,
        duration_days: int,
    ) -> tuple[date | None, date | None]:
        return apply_actual_date_constraints(self._task_calendar, task, est, eft, duration_days)

    def _priority_value(self, task: Task) -> int:
        from src.core.modules.project_management.application.scheduling.utils.task_priority import get_task_priority_value
        return get_task_priority_value(task)
