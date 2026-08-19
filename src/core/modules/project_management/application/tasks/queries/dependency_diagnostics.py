from __future__ import annotations

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol

from collections import deque
from dataclasses import dataclass, replace
from datetime import date

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import run_cpm
from src.core.modules.project_management.application.scheduling.models.cpm import CPMTaskInfo


@dataclass
class DependencyImpactRow:
    task_id: str
    task_name: str
    before_start: date | None
    before_finish: date | None
    after_start: date | None
    after_finish: date | None
    start_shift_days: int | None
    finish_shift_days: int | None
    trace_path: str


@dataclass
class DependencyDiagnostic:
    is_valid: bool
    code: str
    summary: str
    detail: str
    predecessor_task_id: str
    successor_task_id: str
    dependency_type: DependencyType
    lag_days: int
    impact_rows: list[DependencyImpactRow]
    suggestions: list[str]
    risk_level: str = "unknown"


class TaskDependencyDiagnosticsMixin:
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository
    _work_calendar_engine: CalendarProtocol

    def get_dependency_diagnostics(
        self,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
        include_impact: bool = True,
        exclude_dependency_id: str | None = None,
    ) -> DependencyDiagnostic:
        if predecessor_id == successor_id:
            return self._invalid_diagnostic(
                code="DEPENDENCY_SELF",
                summary="A task cannot depend on itself.",
                detail="Select two different tasks for predecessor and successor.",
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                dependency_type=dependency_type,
                lag_days=lag_days,
                suggestions=[
                    "Pick a different predecessor or successor task.",
                    "Use task hierarchy/subtasks instead of self-links for decomposition.",
                ],
            )

        predecessor = self._task_repo.get(predecessor_id)
        successor = self._task_repo.get(successor_id)
        if not predecessor:
            return self._invalid_diagnostic(
                code="TASK_NOT_FOUND",
                summary="Predecessor task not found.",
                detail=f"Task id '{predecessor_id}' does not exist.",
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                dependency_type=dependency_type,
                lag_days=lag_days,
                suggestions=["Refresh task list and reselect predecessor task."],
            )
        if not successor:
            return self._invalid_diagnostic(
                code="TASK_NOT_FOUND",
                summary="Successor task not found.",
                detail=f"Task id '{successor_id}' does not exist.",
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                dependency_type=dependency_type,
                lag_days=lag_days,
                suggestions=["Refresh task list and reselect successor task."],
            )
        if predecessor.project_id != successor.project_id:
            return self._invalid_diagnostic(
                code="DEPENDENCY_CROSS_PROJECT",
                summary="Tasks are in different projects.",
                detail="Dependencies are allowed only between tasks in the same project.",
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                dependency_type=dependency_type,
                lag_days=lag_days,
                suggestions=[
                    "Create dependencies only within the same project plan.",
                    "Use milestone handoff tasks if cross-project coordination is needed.",
                ],
            )

        project_id = predecessor.project_id
        require_project_permission(
            self._user_session,
            project_id,
            "task.read",
            operation_label="preview dependency impact",
        )
        dependencies = self._dependency_repo.list_by_project(project_id)
        if any(
            dependency.predecessor_task_id == predecessor_id
            and dependency.successor_task_id == successor_id
            and dependency.id != exclude_dependency_id
            for dependency in dependencies
        ):
            return self._invalid_diagnostic(
                code="DEPENDENCY_DUPLICATE",
                summary="Dependency already exists.",
                detail="The selected predecessor->successor relationship already exists.",
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                dependency_type=dependency_type,
                lag_days=lag_days,
                suggestions=[
                    "This relationship already exists; update lag/type on existing dependency if needed.",
                    "Use diagnostics to test another direction/type before saving.",
                ],
            )

        tasks = self._task_repo.list_by_project(project_id)
        task_name_by_id = {task.id: task.name for task in tasks}

        cycle_path_ids = self._find_cycle_path_ids(
            deps=dependencies,
            predecessor_id=predecessor_id,
            successor_id=successor_id,
        )
        if cycle_path_ids:
            cycle_names = [task_name_by_id.get(task_id, task_id) for task_id in cycle_path_ids]
            cycle_text = " -> ".join(cycle_names)
            return self._invalid_diagnostic(
                code="DEPENDENCY_CYCLE",
                summary="This link would create a circular dependency.",
                detail=f"Cycle path: {cycle_text}",
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                dependency_type=dependency_type,
                lag_days=lag_days,
                suggestions=[
                    "Reverse the dependency direction if the business flow allows it.",
                    "Insert an intermediate task/milestone to break the loop.",
                ],
            )

        if not include_impact:
            return DependencyDiagnostic(
                is_valid=True,
                code="DEPENDENCY_VALID",
                summary="Dependency is valid.",
                detail="Validation passed: no cycle, no duplicate, and project boundaries are respected.",
                predecessor_task_id=predecessor_id,
                successor_task_id=successor_id,
                dependency_type=dependency_type,
                lag_days=lag_days,
                impact_rows=[],
                suggestions=[],
                risk_level="none",
            )

        proposed = TaskDependency.create(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )
        current_schedule = self._simulate_schedule(tasks=tasks, deps=dependencies)
        projected_schedule = self._simulate_schedule(tasks=tasks, deps=[*dependencies, proposed])
        impact_rows = self._build_impact_rows(
            current_schedule=current_schedule,
            projected_schedule=projected_schedule,
            deps=[*dependencies, proposed],
            predecessor_id=predecessor_id,
            successor_id=successor_id,
        )

        if not impact_rows:
            return DependencyDiagnostic(
                is_valid=True,
                code="DEPENDENCY_VALID",
                summary="Dependency is valid. No schedule shift detected.",
                detail="No task start/finish date changed in the current schedule simulation.",
                predecessor_task_id=predecessor_id,
                successor_task_id=successor_id,
                dependency_type=dependency_type,
                lag_days=lag_days,
                impact_rows=[],
                suggestions=["You can apply this dependency with low scheduling risk."],
                risk_level="none",
            )

        max_delay = max(
            max(abs(row.start_shift_days or 0), abs(row.finish_shift_days or 0))
            for row in impact_rows
        )
        risk_level = self._impact_risk_level(max_delay=max_delay, impacted_count=len(impact_rows))
        top_items = ", ".join(
            f"{row.task_name} ({row.finish_shift_days:+d}d)"
            for row in impact_rows[:3]
            if row.finish_shift_days is not None
        )
        return DependencyDiagnostic(
            is_valid=True,
            code="DEPENDENCY_VALID",
            summary=f"Dependency is valid. {len(impact_rows)} task(s) would shift.",
            detail=(
                f"Maximum predicted shift: {max_delay} day(s)."
                + (f" Most affected: {top_items}." if top_items else "")
            ),
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            impact_rows=impact_rows,
            suggestions=[
                "Review impacted successor chain before saving.",
                "If delay is too high, consider another dependency type or lag adjustment.",
            ],
            risk_level=risk_level,
        )

    def preview_dependency_removal(self, dependency_id: str) -> DependencyDiagnostic:
        """Impact preview for DELETE -- the inverse of the CREATE preview
        above (Phase K). Simulates the schedule WITH the dependency
        (current) vs WITHOUT it (projected), using the exact same
        canonical, non-persisting ``run_cpm`` path ``get_dependency_diagnostics``
        already uses for create/update, so a delete preview can never
        disagree with what actually removing the edge would produce.
        """
        dependency = self._dependency_repo.get(dependency_id)
        if dependency is None:
            return self._invalid_diagnostic(
                code="DEPENDENCY_NOT_FOUND",
                summary="Dependency not found.",
                detail=f"Dependency id '{dependency_id}' does not exist.",
                predecessor_id="",
                successor_id="",
                dependency_type=DependencyType.FINISH_TO_START,
                lag_days=0,
                suggestions=["Refresh and reselect the dependency to remove."],
            )

        predecessor = self._task_repo.get(dependency.predecessor_task_id)
        successor = self._task_repo.get(dependency.successor_task_id)
        project_id = (
            predecessor.project_id if predecessor else (successor.project_id if successor else None)
        )
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "task.read",
                operation_label="preview dependency removal impact",
            )

        if project_id is None:
            return DependencyDiagnostic(
                is_valid=True,
                code="DEPENDENCY_VALID",
                summary="Dependency can be removed. No schedule shift detected.",
                detail="Neither endpoint task could be resolved to a project; no schedule impact to compute.",
                predecessor_task_id=dependency.predecessor_task_id,
                successor_task_id=dependency.successor_task_id,
                dependency_type=dependency.dependency_type,
                lag_days=dependency.lag_days,
                impact_rows=[],
                suggestions=[],
                risk_level="none",
            )

        dependencies = self._dependency_repo.list_by_project(project_id)
        tasks = self._task_repo.list_by_project(project_id)
        remaining = [d for d in dependencies if d.id != dependency_id]

        current_schedule = self._simulate_schedule(tasks=tasks, deps=dependencies)
        projected_schedule = self._simulate_schedule(tasks=tasks, deps=remaining)
        impact_rows = self._build_impact_rows(
            current_schedule=current_schedule,
            projected_schedule=projected_schedule,
            deps=dependencies,
            predecessor_id=dependency.predecessor_task_id,
            successor_id=dependency.successor_task_id,
        )

        if not impact_rows:
            return DependencyDiagnostic(
                is_valid=True,
                code="DEPENDENCY_VALID",
                summary="Dependency can be removed. No schedule shift detected.",
                detail="No task start/finish date changed in the removal simulation.",
                predecessor_task_id=dependency.predecessor_task_id,
                successor_task_id=dependency.successor_task_id,
                dependency_type=dependency.dependency_type,
                lag_days=dependency.lag_days,
                impact_rows=[],
                suggestions=["You can remove this dependency with low scheduling risk."],
                risk_level="none",
            )

        max_delay = max(
            max(abs(row.start_shift_days or 0), abs(row.finish_shift_days or 0))
            for row in impact_rows
        )
        risk_level = self._impact_risk_level(max_delay=max_delay, impacted_count=len(impact_rows))
        top_items = ", ".join(
            f"{row.task_name} ({row.finish_shift_days:+d}d)"
            for row in impact_rows[:3]
            if row.finish_shift_days is not None
        )
        return DependencyDiagnostic(
            is_valid=True,
            code="DEPENDENCY_VALID",
            summary=f"Dependency can be removed. {len(impact_rows)} task(s) would shift.",
            detail=(
                f"Maximum predicted shift: {max_delay} day(s)."
                + (f" Most affected: {top_items}." if top_items else "")
            ),
            predecessor_task_id=dependency.predecessor_task_id,
            successor_task_id=dependency.successor_task_id,
            dependency_type=dependency.dependency_type,
            lag_days=dependency.lag_days,
            impact_rows=impact_rows,
            suggestions=[
                "Review the affected chain before removing this dependency.",
            ],
            risk_level=risk_level,
        )

    def _invalid_diagnostic(
        self,
        code: str,
        summary: str,
        detail: str,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType,
        lag_days: int,
        suggestions: list[str] | None = None,
    ) -> DependencyDiagnostic:
        return DependencyDiagnostic(
            is_valid=False,
            code=code,
            summary=summary,
            detail=detail,
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            impact_rows=[],
            suggestions=suggestions or [],
            risk_level="blocked",
        )

    def _find_cycle_path_ids(
        self,
        deps: list[TaskDependency],
        predecessor_id: str,
        successor_id: str,
    ) -> list[str] | None:
        graph: dict[str, list[str]] = {}
        for dependency in deps:
            graph.setdefault(dependency.predecessor_task_id, []).append(dependency.successor_task_id)

        path = self._find_path(graph, successor_id, predecessor_id)
        if not path:
            return None
        return [predecessor_id, *path]

    @staticmethod
    def _find_path(graph: dict[str, list[str]], start: str, target: str) -> list[str] | None:
        queue = deque([(start, [start])])
        visited: set[str] = set()
        while queue:
            node, path = queue.popleft()
            if node == target:
                return path
            if node in visited:
                continue
            visited.add(node)
            for nxt in graph.get(node, []):
                if nxt not in visited:
                    queue.append((nxt, [*path, nxt]))
        return None

    def _simulate_schedule(
        self,
        tasks: list[Task],
        deps: list[TaskDependency],
    ) -> dict[str, CPMTaskInfo]:
        """Non-persisting preview pass. Uses the exact same canonical CPM
        primitives (``pure_cpm.run_cpm``, which shares its per-task date
        math with the live ``SchedulingEngine``) as the committed schedule,
        so a preview can never disagree with what saving would actually
        produce because of a second, independently-maintained formula --
        see docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
        §11/Phase D/K. Preview and committed schedule still resolve the
        project calendar through the same
        ``resolve_project_calendar_for_preview`` hook (Phase E)."""
        tasks_by_id: dict[str, Task] = {task.id: replace(task) for task in tasks}
        calendar = self._resolve_calendar_for_diagnostics(tasks_by_id)
        return run_cpm(calendar, tasks_by_id, deps).schedule

    def _resolve_calendar_for_diagnostics(self, tasks_by_id: dict[str, Task]) -> CalendarProtocol:
        """Resolve the same project-scoped calendar the live
        ``SchedulingEngine.recalculate_project_schedule`` would bind for
        this project (via its public ``calendar_for_project``), so a
        dependency preview can never silently disagree with the committed
        schedule purely because it consulted a different calendar wrapper
        -- see docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
        §7/Phase E. Falls back to the global work calendar only when no
        scheduling engine is wired (e.g. lightweight test doubles) or the
        task set spans more than one project (diagnostics is always called
        for a single project's graph in practice, but this stays honest
        about that assumption instead of guessing)."""
        scheduling_engine = getattr(self, "_scheduling_engine", None)
        if scheduling_engine is not None:
            project_ids = {task.project_id for task in tasks_by_id.values() if task.project_id}
            if len(project_ids) == 1:
                return scheduling_engine.calendar_for_project(next(iter(project_ids)))
        return self._work_calendar_engine

    def _build_impact_rows(
        self,
        current_schedule: dict[str, CPMTaskInfo],
        projected_schedule: dict[str, CPMTaskInfo],
        deps: list[TaskDependency],
        predecessor_id: str,
        successor_id: str,
    ) -> list[DependencyImpactRow]:
        adjacency: dict[str, list[str]] = {}
        for dependency in deps:
            adjacency.setdefault(dependency.predecessor_task_id, []).append(dependency.successor_task_id)
        trace_map = self._trace_paths_from_source(adjacency, successor_id)

        rows: list[DependencyImpactRow] = []
        for task_id, before in current_schedule.items():
            after = projected_schedule.get(task_id)
            if after is None:
                continue
            before_start = before.earliest_start
            before_finish = before.earliest_finish
            after_start = after.earliest_start
            after_finish = after.earliest_finish

            start_shift = (after_start - before_start).days if (before_start and after_start) else None
            finish_shift = (after_finish - before_finish).days if (before_finish and after_finish) else None
            changed = (
                before_start != after_start
                or before_finish != after_finish
                or (start_shift not in (None, 0))
                or (finish_shift not in (None, 0))
            )
            if not changed:
                continue

            trace_ids = trace_map.get(task_id)
            if task_id == predecessor_id:
                trace_path = "Predecessor task context"
            elif trace_ids:
                trace_path = " -> ".join(
                    projected_schedule[tid].task.name if tid in projected_schedule else tid
                    for tid in trace_ids
                )
            else:
                trace_path = projected_schedule[task_id].task.name

            rows.append(
                DependencyImpactRow(
                    task_id=task_id,
                    task_name=after.task.name,
                    before_start=before_start,
                    before_finish=before_finish,
                    after_start=after_start,
                    after_finish=after_finish,
                    start_shift_days=start_shift,
                    finish_shift_days=finish_shift,
                    trace_path=trace_path,
                )
            )

        rows.sort(
            key=lambda row: (
                -max(abs(row.start_shift_days or 0), abs(row.finish_shift_days or 0)),
                row.task_name.lower(),
            )
        )
        return rows

    @staticmethod
    def _trace_paths_from_source(graph: dict[str, list[str]], source: str) -> dict[str, list[str]]:
        if source is None:
            return {}
        paths: dict[str, list[str]] = {source: [source]}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            current_path = paths[current]
            for nxt in graph.get(current, []):
                if nxt in paths:
                    continue
                paths[nxt] = [*current_path, nxt]
                queue.append(nxt)
        return paths

    @staticmethod
    def _impact_risk_level(max_delay: int, impacted_count: int) -> str:
        if max_delay <= 1 and impacted_count <= 2:
            return "low"
        if max_delay <= 3 and impacted_count <= 5:
            return "medium"
        return "high"


__all__ = ["DependencyDiagnostic", "DependencyImpactRow", "TaskDependencyDiagnosticsMixin"]
