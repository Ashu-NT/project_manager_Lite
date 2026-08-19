from __future__ import annotations

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

from src.core.modules.project_management.contracts.repositories.tasks.task import (
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.domain.tasks.hierarchy import (
    select_leaf_dependencies,
    select_leaf_tasks,
)
from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintValidator,
    DependencyConstraintConflict,
)
from src.core.modules.project_management.application.scheduling.cpm.dependency_schedule_math import (
    normalize_forward,
    shift_working_days,
)
from src.core.modules.project_management.application.scheduling.cpm.dependency_actual_variance import (
    find_dependency_actual_variances,
)
from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import (
    CPMResult,
    run_cpm,
)
from src.core.modules.project_management.application.scheduling.forecasting.task_schedule_overview import (
    TaskScheduleOverview,
    build_schedule_drivers,
    build_successors_by_task_id,
    compute_downstream_exposure,
    compute_free_float_days,
)


@dataclass
class TaskImpact:
    task_id: str
    task_name: str
    original_start: date | None
    original_finish: date | None
    proposed_start: date | None
    proposed_finish: date | None
    start_shift_days: int | None   # positive = later, negative = earlier
    finish_shift_days: int | None
    is_critical: bool
    is_milestone: bool = False


@dataclass
class ScheduleChangeImpactReport:
    """
    Impact analysis for a proposed date change on a single task.

    Lists every downstream task that would shift, the magnitude of shift,
    and which tasks would join or leave the critical path.
    """
    changed_task_id: str
    proposed_start: date | None
    proposed_finish: date | None
    proposed_duration_days: int | None
    affected_tasks: list[TaskImpact]          # tasks that shift (including the changed task)
    newly_critical_task_ids: list[str]        # tasks entering critical path
    no_longer_critical_task_ids: list[str]    # tasks leaving critical path
    max_project_finish_shift_days: int        # positive = project end delayed
    requires_approval: bool                   # true if approved baseline exists and shift > threshold
    critical_path_changed: bool = False
    dependency_conflicts: list[DependencyConstraintConflict] = field(default_factory=list)


class ApprovedBaselineLookup(Protocol):
    def get_approved_baseline(self, project_id: str) -> object | None: ...


class ScheduleChangeImpactService:
    """
    Analyses the downstream impact of a proposed schedule change before persisting.

    Workflow:
        1. Caller proposes a new start/finish/duration for a task.
        2. Service runs a second CPM pass with the proposed values applied.
        3. Diffs original vs proposed CPM results to identify affected tasks.
        4. Returns an impact report the UI or approval router can act on.

    This service never writes to the database.
    """

    APPROVAL_THRESHOLD_DAYS: int = 5  # override via constructor arg

    def __init__(
        self,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        calendar: CalendarProtocol,
        baseline_lookup: ApprovedBaselineLookup,
        approval_threshold_days: int = 5,
    ) -> None:
        self._task_repo = task_repo
        self._dependency_repo = dependency_repo
        self._calendar = calendar
        self._baseline_lookup = baseline_lookup
        self._approval_threshold_days = approval_threshold_days
        # Injectable seam so tests can isolate baseline/threshold logic from
        # real CPM date math without needing a second CPM implementation to
        # stub against -- defaults to the one canonical implementation.
        self._run_cpm = run_cpm

    def analyse(
        self,
        project_id: str,
        changed_task_id: str,
        proposed_start: date | None = None,
        proposed_finish: date | None = None,
        proposed_duration_days: int | None = None,
    ) -> ScheduleChangeImpactReport:
        """
        Run two CPM passes (original vs proposed) and return the delta.

        At least one of proposed_start / proposed_finish / proposed_duration_days
        must be supplied.
        """
        tasks = select_leaf_tasks(self._task_repo.list_by_project(project_id))
        deps = select_leaf_dependencies(
            self._dependency_repo.list_by_project(project_id),
            tasks,
        )

        tasks_by_id: dict[str, Task] = {t.id: t for t in tasks}

        # ── original pass ────────────────────────────────────────────────
        original: CPMResult = self._run_cpm(self._calendar, tasks_by_id, deps)

        # ── proposed pass (copy with the change applied) ─────────────────
        from dataclasses import replace
        proposed_tasks: dict[str, Task] = {tid: replace(t) for tid, t in tasks_by_id.items()}
        changed = proposed_tasks.get(changed_task_id)
        if changed is None:
            return ScheduleChangeImpactReport(
                changed_task_id=changed_task_id,
                proposed_start=proposed_start,
                proposed_finish=proposed_finish,
                proposed_duration_days=proposed_duration_days,
                affected_tasks=[],
                newly_critical_task_ids=[],
                no_longer_critical_task_ids=[],
                max_project_finish_shift_days=0,
                requires_approval=False,
            )
        # Built as one atomic replace() rather than sequential attribute
        # assignments: Task's validated-assignment enforces end >= start on
        # EVERY individual field write, so setting start_date alone while
        # end_date still holds its old value can spuriously fail validation
        # when the proposed start moves past the task's current end (the
        # common case for a "delay by N working days" preview). duration_days
        # is what CPM's own compute_duration_dates actually keys off for a
        # leaf task -- end_date here is kept consistent with it using the
        # exact same start+duration->finish formula that function uses, so
        # this mutation can never silently disagree with what run_cpm itself
        # would derive.
        new_duration = (
            proposed_duration_days if proposed_duration_days is not None else changed.duration_days
        )
        new_start = proposed_start if proposed_start is not None else changed.start_date
        if proposed_finish is not None:
            new_finish = proposed_finish
        elif new_start is not None and new_duration and new_duration > 0:
            new_finish = self._calendar.add_working_days(new_start, new_duration)
        else:
            new_finish = changed.end_date
        proposed_tasks[changed_task_id] = replace(
            changed,
            start_date=new_start,
            end_date=new_finish,
            duration_days=new_duration,
        )

        proposed: CPMResult = self._run_cpm(self._calendar, proposed_tasks, deps)

        # ── diff ─────────────────────────────────────────────────────────
        affected: list[TaskImpact] = []
        orig_critical: set[str] = set(original.critical_path_task_ids)
        prop_critical: set[str] = set(proposed.critical_path_task_ids)

        for task_id in tasks_by_id:
            orig_info = original.schedule.get(task_id)
            prop_info = proposed.schedule.get(task_id)
            if orig_info is None or prop_info is None:
                continue

            orig_s = orig_info.earliest_start
            orig_f = orig_info.earliest_finish
            prop_s = prop_info.earliest_start
            prop_f = prop_info.earliest_finish

            start_shift = self._day_shift(orig_s, prop_s)
            finish_shift = self._day_shift(orig_f, prop_f)

            if start_shift == 0 and finish_shift == 0 and task_id != changed_task_id:
                continue  # unaffected

            affected.append(TaskImpact(
                task_id=task_id,
                task_name=tasks_by_id[task_id].name,
                original_start=orig_s,
                original_finish=orig_f,
                proposed_start=prop_s,
                proposed_finish=prop_f,
                start_shift_days=start_shift,
                finish_shift_days=finish_shift,
                is_critical=(task_id in prop_critical),
                is_milestone=int(getattr(tasks_by_id[task_id], "duration_days", 0) or 0) <= 0,
            ))

        orig_ef = original.project_early_finish
        prop_ef = proposed.project_early_finish
        project_finish_shift = self._day_shift(orig_ef, prop_ef)

        newly_critical = sorted(prop_critical - orig_critical)
        no_longer_critical = sorted(orig_critical - prop_critical)

        requires_approval = (
            self._has_approved_baseline(project_id)
            and abs(project_finish_shift) >= self._approval_threshold_days
        )

        # Dependency/constraint conflicts under the PROPOSED schedule --
        # reuses the canonical ConstraintValidator over the already-computed
        # proposed CPM result, no second implementation (§9/§22).
        dependency_conflicts = ConstraintValidator(self._calendar).validate(
            proposed_tasks, proposed.schedule
        ).dependency_conflicts

        return ScheduleChangeImpactReport(
            changed_task_id=changed_task_id,
            proposed_start=proposed_start,
            proposed_finish=proposed_finish,
            proposed_duration_days=proposed_duration_days,
            affected_tasks=affected,
            newly_critical_task_ids=newly_critical,
            no_longer_critical_task_ids=no_longer_critical,
            critical_path_changed=bool(newly_critical or no_longer_critical),
            dependency_conflicts=dependency_conflicts,
            max_project_finish_shift_days=project_finish_shift,
            requires_approval=requires_approval,
        )

    def analyse_delay(
        self,
        *,
        project_id: str,
        changed_task_id: str,
        current_start: date,
        delay_days: int = 1,
    ) -> ScheduleChangeImpactReport:
        return self.analyse(
            project_id=project_id,
            changed_task_id=changed_task_id,
            proposed_start=current_start + timedelta(days=max(1, delay_days)),
        )

    def analyse_working_day_delay(
        self,
        *,
        project_id: str,
        changed_task_id: str,
        current_start: date,
        delay_working_days: int = 1,
    ) -> ScheduleChangeImpactReport:
        """Task Detail -> Schedule Impact's "Delay by N working days" input
        (§12). Unlike ``analyse_delay`` (calendar-day ``timedelta``, kept
        unchanged for its existing caller), this uses the same
        ``shift_working_days`` primitive every other working-day
        calculation in this pass uses, so "2 working days" means the same
        thing here as it does in the dependency lag/lead math -- weekends
        and holidays are skipped, not counted through."""
        normalized_start = normalize_forward(self._calendar, current_start)
        proposed_start = shift_working_days(
            self._calendar, normalized_start, max(1, delay_working_days)
        )
        return self.analyse(
            project_id=project_id,
            changed_task_id=changed_task_id,
            proposed_start=proposed_start,
        )

    def get_task_schedule_overview(self, project_id: str, task_id: str) -> TaskScheduleOverview:
        """Task Detail -> Schedule Impact's always-visible current-state
        facts (§6-§11) -- ONE canonical CPM pass, no hypothetical change,
        no persistence. Reuses the exact same in-memory task/dependency
        load ``analyse`` uses (§25: no per-task repository calls)."""
        tasks = select_leaf_tasks(self._task_repo.list_by_project(project_id))
        deps = select_leaf_dependencies(
            self._dependency_repo.list_by_project(project_id),
            tasks,
        )
        tasks_by_id: dict[str, Task] = {t.id: t for t in tasks}
        task = tasks_by_id.get(task_id)
        if task is None:
            return TaskScheduleOverview(task_id=task_id, is_available=False)

        result: CPMResult = self._run_cpm(self._calendar, tasks_by_id, deps)
        info = result.schedule.get(task_id)
        if info is None:
            return TaskScheduleOverview(task_id=task_id, is_available=False)

        critical_ids = set(result.critical_path_task_ids)
        successors = build_successors_by_task_id(deps)
        downstream = compute_downstream_exposure(task_id, tasks_by_id, successors, critical_ids)
        free_float = compute_free_float_days(task_id, result.schedule, deps, self._calendar)

        incoming = [d for d in deps if d.successor_task_id == task_id]
        predecessor_names = {
            d.predecessor_task_id: tasks_by_id[d.predecessor_task_id].name
            for d in incoming
            if d.predecessor_task_id in tasks_by_id
        }
        drivers = build_schedule_drivers(task, incoming, predecessor_names)

        all_conflicts = ConstraintValidator(self._calendar).validate(
            tasks_by_id, result.schedule
        ).dependency_conflicts
        conflicts = tuple(c for c in all_conflicts if c.task_id == task_id)

        all_variances = find_dependency_actual_variances(tasks_by_id, result.schedule, self._calendar)
        variances = tuple(v for v in all_variances if v.task_id == task_id)

        baseline_finish, schedule_variance_days = self._baseline_comparison(
            project_id, task_id, info.earliest_finish
        )

        return TaskScheduleOverview(
            task_id=task_id,
            is_available=True,
            current_start=info.earliest_start,
            current_finish=info.earliest_finish,
            is_critical=info.is_critical,
            total_float_days=info.total_float_days,
            free_float_days=free_float,
            baseline_finish=baseline_finish,
            schedule_variance_days=schedule_variance_days,
            drivers=drivers,
            dependency_conflicts=conflicts,
            actual_variances=variances,
            downstream=downstream,
        )

    def _baseline_comparison(
        self, project_id: str, task_id: str, current_finish: date | None
    ) -> tuple[date | None, int | None]:
        """Best-effort: only produces a fact when an approved baseline
        exists AND has a recorded snapshot for this exact task AND the
        current schedule has a computed finish to compare against.
        Never invents a value (§6, §20)."""
        get_baseline_task = getattr(self._baseline_lookup, "get_baseline_task", None)
        if not callable(get_baseline_task) or current_finish is None:
            return None, None
        baseline = self._baseline_lookup.get_approved_baseline(project_id)
        if baseline is None:
            return None, None
        baseline_task = get_baseline_task(baseline.id, task_id)
        if baseline_task is None or baseline_task.baseline_finish is None:
            return None, None
        return baseline_task.baseline_finish, self._day_shift(baseline_task.baseline_finish, current_finish)

    def _has_approved_baseline(self, project_id: str) -> bool:
        return self._baseline_lookup.get_approved_baseline(project_id) is not None

    # ── internal ─────────────────────────────────────────────────────────────

    def _day_shift(self, original: date | None, proposed: date | None) -> int:
        if original is None or proposed is None:
            return 0
        if proposed == original:
            return 0
        if proposed > original:
            return self._calendar.working_days_between(original, proposed) - 1
        return -(self._calendar.working_days_between(proposed, original) - 1)


__all__ = [
    "ApprovedBaselineLookup",
    "ScheduleChangeImpactService",
    "ScheduleChangeImpactReport",
    "TaskImpact",
]
