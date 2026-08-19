"""
``ResourceLevelingPlanner`` is a pure, in-memory, application-level
component: it takes an already-loaded project's tasks/dependencies/
assignments/resources and produces a typed ``LevelingProposal`` (§K).
It does not own persistence, does not commit, does not format for QML,
and does not duplicate CPM/dependency/constraint/calendar math -- every
feasibility check is a real call into ``run_cpm``/``ConstraintValidator``
against an in-memory candidate task set (the "canonical feasibility
seam," §D: this codebase's existing canonical scheduler IS the seam,
there is no separate ``evaluate_placement`` formula to maintain).

Replaces the old ``ResourceLevelingMixin.auto_level_resources``'s
"+1 working day, re-scan, +1 working day" loop (§J) with a bounded,
in-memory nearest-legal-placement search per candidate task, and reuses
its ``build_resource_conflicts``/``choose_auto_level_task``-adjacent
day-bucketing (``leveling.py``) rather than re-deriving conflict
detection.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment, TaskDependency
from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import run_cpm
from src.core.modules.project_management.application.scheduling.leveling.leveling import (
    build_resource_conflicts,
)
from src.core.modules.project_management.application.scheduling.leveling.movability_policy import (
    task_movability,
)
from src.core.modules.project_management.application.scheduling.leveling.schedule_fingerprint import (
    compute_schedule_fingerprint,
)
from src.core.modules.project_management.application.scheduling.models.leveling import (
    LevelingProposal,
    ProposedTaskMove,
    UnresolvedConflict,
)
from src.core.modules.project_management.application.scheduling.utils.task_priority import (
    get_task_priority_value,
)


class ResourceLevelingPlanner:
    """Pure application-level planner. Construct once per preview call
    with an already-fetched, in-memory project snapshot."""

    def __init__(
        self,
        calendar: CalendarProtocol,
        *,
        threshold_percent: float = 100.0,
        max_moves: int = 60,
        search_horizon_working_days: int = 60,
    ) -> None:
        self._calendar = calendar
        self._threshold_percent = threshold_percent
        self._max_moves = max_moves
        self._search_horizon_working_days = search_horizon_working_days

    def build_proposal(
        self,
        *,
        project_id: str,
        tasks_by_id: dict[str, Task],
        deps: list[TaskDependency],
        assignments: list[TaskAssignment],
        resource_name_by_id: dict[str, str],
        resource_threshold_by_id: dict[str, float] | None = None,
    ) -> LevelingProposal:
        schedule_fingerprint = compute_schedule_fingerprint(tasks_by_id, deps, assignments)
        before_result = run_cpm(self._calendar, tasks_by_id, deps)
        before_computed = {tid: info.task for tid, info in before_result.schedule.items()}
        conflicts_before = build_resource_conflicts(
            tasks_by_id=before_computed,
            assignments=assignments,
            calendar=self._calendar,
            resource_name_by_id=resource_name_by_id,
            threshold_percent=self._threshold_percent,
            threshold_by_resource_id=resource_threshold_by_id,
        )

        working_tasks: dict[str, Task] = dict(tasks_by_id)
        accepted: list[ProposedTaskMove] = []
        given_up_on: set[tuple[str, date]] = set()
        warnings: list[str] = []
        unresolved: list[UnresolvedConflict] = []

        moves_made = 0
        while moves_made < self._max_moves:
            current_result = run_cpm(self._calendar, working_tasks, deps)
            current_computed = {tid: info.task for tid, info in current_result.schedule.items()}
            conflicts = build_resource_conflicts(
                tasks_by_id=current_computed,
                assignments=assignments,
                calendar=self._calendar,
                resource_name_by_id=resource_name_by_id,
                threshold_percent=self._threshold_percent,
                threshold_by_resource_id=resource_threshold_by_id,
            )
            live_conflicts = [
                c for c in conflicts if (c.resource_id, c.conflict_date) not in given_up_on
            ]
            if not live_conflicts:
                break

            top_conflict = max(
                live_conflicts,
                key=lambda c: (c.total_allocation_percent, len(c.entries)),
            )

            candidate_ids = self._ordered_candidates(
                top_conflict.entries, working_tasks, current_result.schedule
            )
            resolved_this_conflict = False
            for task_id in candidate_ids:
                base_task = working_tasks[task_id]
                info = current_result.schedule.get(task_id)
                if info is None or info.earliest_start is None:
                    continue
                was_infeasible = bool(info.is_infeasible)

                move = self._search_placement(
                    task_id=task_id,
                    base_task=base_task,
                    working_tasks=working_tasks,
                    deps=deps,
                    assignments=assignments,
                    resource_name_by_id=resource_name_by_id,
                    resource_threshold_by_id=resource_threshold_by_id,
                    from_start=info.earliest_start,
                    was_infeasible=was_infeasible,
                    conflict_resource_name=top_conflict.resource_name,
                )
                if move is None:
                    continue

                working_tasks[task_id] = replace(
                    base_task, resource_leveling_not_before=move.new_start
                )
                accepted.append(move)
                if move.deadline_warning:
                    warnings.append(move.deadline_warning)
                moves_made += 1
                resolved_this_conflict = True
                break

            if not resolved_this_conflict:
                given_up_on.add((top_conflict.resource_id, top_conflict.conflict_date))
                decision_reason = self._best_unresolved_reason(
                    top_conflict.entries, working_tasks
                )
                unresolved.append(
                    UnresolvedConflict(
                        resource_id=top_conflict.resource_id,
                        resource_name=top_conflict.resource_name,
                        conflict_date=top_conflict.conflict_date,
                        total_allocation_percent=top_conflict.total_allocation_percent,
                        reason=decision_reason,
                    )
                )

        final_result = run_cpm(self._calendar, working_tasks, deps)
        final_computed = {tid: info.task for tid, info in final_result.schedule.items()}
        conflicts_after = build_resource_conflicts(
            tasks_by_id=final_computed,
            assignments=assignments,
            calendar=self._calendar,
            resource_name_by_id=resource_name_by_id,
            threshold_percent=self._threshold_percent,
            threshold_by_resource_id=resource_threshold_by_id,
        )

        moves = tuple(
            self._build_move_dto(a, before_result.schedule, final_result.schedule)
            for a in accepted
        )

        critical_before = {
            tid for tid, info in before_result.schedule.items() if info.is_critical
        }
        critical_after = {
            tid for tid, info in final_result.schedule.items() if info.is_critical
        }
        new_infeasible = tuple(
            tid
            for tid, info in final_result.schedule.items()
            if info.is_infeasible
            and tid in before_result.schedule
            and not before_result.schedule[tid].is_infeasible
        )

        return LevelingProposal(
            project_id=project_id,
            schedule_fingerprint=schedule_fingerprint,
            is_feasible=len(unresolved) == 0,
            resource_conflicts_before=len(conflicts_before),
            resource_conflicts_after=len(conflicts_after),
            moves=moves,
            unresolved_conflicts=tuple(unresolved),
            project_finish_before=before_result.project_early_finish,
            project_finish_after=final_result.project_early_finish,
            critical_path_changed=critical_before != critical_after,
            new_infeasibility_task_ids=new_infeasible,
            warnings=tuple(warnings),
        )

    # ── candidate ordering (R4.4I1) ──────────────────────────────────────

    def _ordered_candidates(self, entries, working_tasks, schedule) -> list[str]:
        scored: list[tuple[tuple, str]] = []
        for entry in entries:
            task = working_tasks.get(entry.task_id)
            if task is None:
                continue
            decision = task_movability(task)
            if not decision.movable:
                continue
            info = schedule.get(entry.task_id)
            is_critical = bool(info.is_critical) if info is not None else False
            total_float = int(info.total_float_days) if info and info.total_float_days is not None else 0
            start_ordinal = task.start_date.toordinal() if task.start_date else 0
            key = (
                1 if is_critical else 0,
                -total_float,
                -get_task_priority_value(task),
                start_ordinal,
                task.id,
            )
            scored.append((key, entry.task_id))
        scored.sort(key=lambda pair: pair[0])
        return [task_id for _key, task_id in scored]

    def _best_unresolved_reason(self, entries, working_tasks) -> str:
        for entry in entries:
            task = working_tasks.get(entry.task_id)
            if task is None:
                continue
            decision = task_movability(task)
            if not decision.movable:
                return (
                    f"{task.name}: {decision.reason} prevents automatic movement, "
                    "and no alternative task on this resource could be legally rescheduled."
                )
        return "No legal placement found for any task on this resource within the search horizon."

    # ── candidate placement search (R4.4J) ──────────────────────────────

    def _search_placement(
        self,
        *,
        task_id: str,
        base_task: Task,
        working_tasks: dict[str, Task],
        deps: list[TaskDependency],
        assignments: list[TaskAssignment],
        resource_name_by_id: dict[str, str],
        resource_threshold_by_id: dict[str, float] | None,
        from_start: date,
        was_infeasible: bool,
        conflict_resource_name: str,
    ) -> ProposedTaskMove | None:
        decision = task_movability(base_task)
        if not decision.movable:
            return None

        for shift in range(1, self._search_horizon_working_days + 1):
            candidate_start = self._calendar.add_working_days(from_start, shift)
            if decision.start_ceiling is not None and candidate_start > decision.start_ceiling:
                break  # every later shift only gets further past the ceiling
            duration = int(base_task.duration_days or 0)
            candidate_finish = (
                self._calendar.add_working_days(candidate_start, duration)
                if duration > 0
                else candidate_start
            )
            if decision.finish_ceiling is not None and candidate_finish > decision.finish_ceiling:
                break

            trial_tasks = dict(working_tasks)
            trial_tasks[task_id] = replace(base_task, resource_leveling_not_before=candidate_start)
            trial_result = run_cpm(self._calendar, trial_tasks, deps)
            trial_info = trial_result.schedule.get(task_id)
            if trial_info is None or trial_info.earliest_start != candidate_start:
                # The floor didn't actually land the task at candidate_start
                # (e.g. a dependency pushed it even later) -- not a legal
                # placement for THIS candidate date; try the next one.
                continue
            if trial_info.is_infeasible and not was_infeasible:
                continue  # never worsen dependency/constraint infeasibility (R4.4I2)

            trial_computed = {tid: info.task for tid, info in trial_result.schedule.items()}
            trial_conflicts = build_resource_conflicts(
                tasks_by_id=trial_computed,
                assignments=assignments,
                calendar=self._calendar,
                resource_name_by_id=resource_name_by_id,
                threshold_percent=self._threshold_percent,
                threshold_by_resource_id=resource_threshold_by_id,
            )
            # E1: a multi-resource task is only a legal placement when EVERY
            # resource it uses is clear over the new interval, not just the
            # one resource that triggered the conflict being resolved.
            task_resource_ids = {a.resource_id for a in assignments if a.task_id == task_id}
            still_conflicts_in_window = any(
                c.resource_id in task_resource_ids
                and candidate_start <= c.conflict_date <= candidate_finish
                for c in trial_conflicts
            )
            if still_conflicts_in_window:
                continue

            deadline_warning = ""
            if decision.deadline is not None and candidate_finish > decision.deadline:
                deadline_warning = (
                    f"{base_task.name}: proposed finish {candidate_finish.isoformat()} "
                    f"exceeds its deadline of {decision.deadline.isoformat()}."
                )

            old_finish = self._calendar.add_working_days(from_start, duration) if duration > 0 else from_start
            resource_ids = tuple(sorted({a.resource_id for a in assignments if a.task_id == task_id}))
            return ProposedTaskMove(
                task_id=task_id,
                task_name=base_task.name,
                wbs_code=getattr(base_task, "wbs_code", "") or "",
                old_start=from_start,
                old_finish=old_finish,
                new_start=candidate_start,
                new_finish=candidate_finish,
                shift_working_days=shift,
                reason=(
                    f"Resolved {conflict_resource_name} capacity conflict "
                    f"({self._threshold_percent:.0f}% threshold)."
                ),
                resource_ids=resource_ids,
                resource_names=tuple(resource_name_by_id.get(rid, rid) for rid in resource_ids),
                float_before=None,  # filled in by _build_move_dto from the true before/after schedules
                float_after=None,
                critical_before=False,
                critical_after=False,
                infeasible_after=bool(trial_info.is_infeasible),
                deadline_warning=deadline_warning,
            )
        return None

    def _build_move_dto(
        self,
        accepted: ProposedTaskMove,
        before_schedule,
        final_schedule,
    ) -> ProposedTaskMove:
        before_info = before_schedule.get(accepted.task_id)
        after_info = final_schedule.get(accepted.task_id)
        return replace(
            accepted,
            float_before=before_info.total_float_days if before_info else None,
            float_after=after_info.total_float_days if after_info else None,
            critical_before=bool(before_info.is_critical) if before_info else False,
            critical_after=bool(after_info.is_critical) if after_info else False,
            infeasible_after=bool(after_info.is_infeasible) if after_info else accepted.infeasible_after,
        )


__all__ = ["ResourceLevelingPlanner"]
