from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from datetime import date
from typing import Dict, List, Optional

from core.interfaces import DependencyRepository, TaskRepository
from core.models import DependencyType, Task, TaskDependency
from core.services.scheduling.graph import build_project_dependency_graph
from core.services.scheduling.models import CPMTaskInfo
from core.services.scheduling.passes import run_backward_pass, run_forward_pass
from core.services.scheduling.results import build_schedule_result
from core.services.work_calendar.engine import WorkCalendarEngine


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


class TaskDependencyDiagnosticsMixin:
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository
    _work_calendar_engine: WorkCalendarEngine

    def get_dependency_diagnostics(
        self,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
        include_impact: bool = True,
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
            )

        project_id = predecessor.project_id
        deps = self._dependency_repo.list_by_project(project_id)
        if any(
            dep.predecessor_task_id == predecessor_id and dep.successor_task_id == successor_id
            for dep in deps
        ):
            return self._invalid_diagnostic(
                code="DEPENDENCY_DUPLICATE",
                summary="Dependency already exists.",
                detail="The selected predecessor->successor relationship already exists.",
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                dependency_type=dependency_type,
                lag_days=lag_days,
            )

        tasks = self._task_repo.list_by_project(project_id)
        task_name_by_id = {task.id: task.name for task in tasks}

        cycle_path_ids = self._find_cycle_path_ids(
            deps=deps,
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
            )

        proposed = TaskDependency.create(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )
        current_schedule = self._simulate_schedule(tasks=tasks, deps=deps)
        projected_schedule = self._simulate_schedule(tasks=tasks, deps=[*deps, proposed])
        impact_rows = self._build_impact_rows(
            current_schedule=current_schedule,
            projected_schedule=projected_schedule,
            deps=[*deps, proposed],
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
            )

        max_delay = max(
            max(abs(row.start_shift_days or 0), abs(row.finish_shift_days or 0))
            for row in impact_rows
        )
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
        )

    def _find_cycle_path_ids(
        self,
        deps: list[TaskDependency],
        predecessor_id: str,
        successor_id: str,
    ) -> list[str] | None:
        graph: dict[str, list[str]] = {}
        for dep in deps:
            graph.setdefault(dep.predecessor_task_id, []).append(dep.successor_task_id)

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
        tasks_by_id: Dict[str, Task] = {task.id: replace(task) for task in tasks}

        topo_order, deps_by_successor, deps_by_predecessor = build_project_dependency_graph(
            tasks_by_id=tasks_by_id,
            deps=deps,
            priority_value=self._priority_value_for_preview,
        )

        es, ef, project_early_finish = run_forward_pass(
            tasks_by_id=tasks_by_id,
            topo_order=topo_order,
            deps_by_successor=deps_by_successor,
            compute_task_dates=self._compute_task_dates_for_preview,
        )
        ls, lf = run_backward_pass(
            tasks_by_id=tasks_by_id,
            topo_order=topo_order,
            deps_by_predecessor=deps_by_predecessor,
            es=es,
            ef=ef,
            project_early_finish=project_early_finish,
            calendar=self._work_calendar_engine,
        )
        return build_schedule_result(
            tasks_by_id=tasks_by_id,
            es=es,
            ef=ef,
            ls=ls,
            lf=lf,
            calendar=self._work_calendar_engine,
        )

    def _compute_task_dates_for_preview(
        self,
        task: Task,
        incoming_deps: List[TaskDependency],
        es: Dict[str, Optional[date]],
        ef: Dict[str, Optional[date]],
    ) -> tuple[Optional[date], Optional[date]]:
        duration = int(task.duration_days or 0)
        if duration <= 0:
            est, eft = self._compute_dates_milestone(task, incoming_deps, es, ef)
        else:
            est, eft = self._compute_dates_with_duration(task, incoming_deps, es, ef, duration)
        return self._apply_actual_constraints(task, est, eft, duration)

    def _compute_dates_milestone(
        self,
        task: Task,
        incoming_deps: List[TaskDependency],
        es: Dict[str, Optional[date]],
        ef: Dict[str, Optional[date]],
    ) -> tuple[Optional[date], Optional[date]]:
        if not incoming_deps:
            return (task.start_date, task.start_date) if task.start_date else (None, None)
        candidates: List[date] = []
        for dep in incoming_deps:
            pred_es = es.get(dep.predecessor_task_id)
            pred_ef = ef.get(dep.predecessor_task_id)
            if pred_es is None and pred_ef is None:
                continue
            if dep.dependency_type == DependencyType.FINISH_TO_START and pred_ef:
                candidates.append(self._work_calendar_engine.add_working_days(pred_ef, dep.lag_days + 2))
            elif dep.dependency_type == DependencyType.START_TO_START and pred_es:
                candidates.append(self._work_calendar_engine.add_working_days(pred_es, dep.lag_days))
            elif dep.dependency_type == DependencyType.FINISH_TO_FINISH and pred_ef:
                candidates.append(self._work_calendar_engine.add_working_days(pred_ef, dep.lag_days))
            elif dep.dependency_type == DependencyType.START_TO_FINISH and pred_es:
                candidates.append(self._work_calendar_engine.add_working_days(pred_es, dep.lag_days))
        if not candidates:
            return (task.start_date, task.start_date) if task.start_date else (None, None)
        est = max(candidates)
        return est, est

    def _compute_dates_with_duration(
        self,
        task: Task,
        incoming_deps: List[TaskDependency],
        es: Dict[str, Optional[date]],
        ef: Dict[str, Optional[date]],
        duration: int,
    ) -> tuple[Optional[date], Optional[date]]:
        if not incoming_deps:
            if not task.start_date:
                return None, None
            est = task.start_date
            eft = self._work_calendar_engine.add_working_days(est, duration)
            return est, eft

        candidate_es: List[date] = []
        for dep in incoming_deps:
            pred_es = es.get(dep.predecessor_task_id)
            pred_ef = ef.get(dep.predecessor_task_id)
            if pred_es is None and pred_ef is None:
                continue
            if dep.dependency_type == DependencyType.FINISH_TO_START and pred_ef:
                candidate_es.append(self._work_calendar_engine.add_working_days(pred_ef, dep.lag_days + 2))
            elif dep.dependency_type == DependencyType.START_TO_START and pred_es:
                candidate_es.append(self._work_calendar_engine.add_working_days(pred_es, dep.lag_days))
            elif dep.dependency_type == DependencyType.FINISH_TO_FINISH and pred_ef:
                ef_s = self._work_calendar_engine.add_working_days(pred_ef, dep.lag_days)
                candidate_es.append(self._work_calendar_engine.add_working_days(ef_s, -(duration - 1)))
            elif dep.dependency_type == DependencyType.START_TO_FINISH and pred_es:
                ef_s = self._work_calendar_engine.add_working_days(pred_es, dep.lag_days)
                candidate_es.append(self._work_calendar_engine.add_working_days(ef_s, -(duration - 1)))

        if not candidate_es:
            if not task.start_date:
                return None, None
            est = task.start_date
            eft = self._work_calendar_engine.add_working_days(est, duration)
            return est, eft

        est = max(candidate_es)
        eft = self._work_calendar_engine.add_working_days(est, duration)
        return est, eft

    def _apply_actual_constraints(
        self,
        task: Task,
        est: Optional[date],
        eft: Optional[date],
        duration_days: int,
    ) -> tuple[Optional[date], Optional[date]]:
        a_start = getattr(task, "actual_start", None)
        a_end = getattr(task, "actual_end", None)
        if a_end is not None:
            fixed_ef = a_end
            if a_start is not None:
                fixed_es = a_start
            elif duration_days > 0:
                fixed_es = self._work_calendar_engine.add_working_days(fixed_ef, -(duration_days - 1))
            else:
                fixed_es = fixed_ef
            return fixed_es, fixed_ef
        if a_start is not None and (est is None or a_start > est):
            est = a_start
            eft = est if duration_days <= 0 else self._work_calendar_engine.add_working_days(est, duration_days)
        return est, eft

    @staticmethod
    def _priority_value_for_preview(task: Task) -> int:
        value = getattr(task, "priority", None)
        if value is None:
            return 50
        if hasattr(value, "value"):
            value = value.value
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            normalized = value.strip().upper()
            if normalized in {"HIGH", "H"}:
                return 10
            if normalized in {"LOW", "L"}:
                return 90
        return 50

    def _build_impact_rows(
        self,
        current_schedule: dict[str, CPMTaskInfo],
        projected_schedule: dict[str, CPMTaskInfo],
        deps: list[TaskDependency],
        predecessor_id: str,
        successor_id: str,
    ) -> list[DependencyImpactRow]:
        adjacency: dict[str, list[str]] = {}
        for dep in deps:
            adjacency.setdefault(dep.predecessor_task_id, []).append(dep.successor_task_id)
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


__all__ = ["DependencyImpactRow", "DependencyDiagnostic", "TaskDependencyDiagnosticsMixin"]
