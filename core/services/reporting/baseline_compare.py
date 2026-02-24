from __future__ import annotations

from core.exceptions import NotFoundError, ValidationError
from core.interfaces import BaselineRepository, TaskRepository
from core.models import BaselineTask, ProjectBaseline
from core.services.reporting.models import BaselineComparisonResult, BaselineComparisonRow


class ReportingBaselineCompareMixin:
    _baseline_repo: BaselineRepository
    _task_repo: TaskRepository

    def list_project_baselines(self, project_id: str) -> list[ProjectBaseline]:
        return self._baseline_repo.list_for_project(project_id)

    def compare_baselines(
        self,
        project_id: str,
        baseline_a_id: str,
        baseline_b_id: str,
        include_unchanged: bool = False,
    ) -> BaselineComparisonResult:
        if not baseline_a_id or not baseline_b_id:
            raise ValidationError("Two baseline IDs are required.", code="BASELINE_COMPARE_INPUT_INVALID")
        if baseline_a_id == baseline_b_id:
            raise ValidationError(
                "Select two different baselines to compare.",
                code="BASELINE_COMPARE_SAME_BASELINE",
            )

        baseline_a = self._baseline_repo.get_baseline(baseline_a_id)
        baseline_b = self._baseline_repo.get_baseline(baseline_b_id)

        if not baseline_a:
            raise NotFoundError("Baseline A not found.", code="BASELINE_A_NOT_FOUND")
        if not baseline_b:
            raise NotFoundError("Baseline B not found.", code="BASELINE_B_NOT_FOUND")

        if baseline_a.project_id != project_id or baseline_b.project_id != project_id:
            raise ValidationError(
                "Selected baselines do not belong to the selected project.",
                code="BASELINE_COMPARE_PROJECT_MISMATCH",
            )

        all_rows = self._build_baseline_comparison_rows(
            project_id=project_id,
            baseline_a_id=baseline_a_id,
            baseline_b_id=baseline_b_id,
            include_unchanged=True,
        )
        rows = (
            all_rows
            if include_unchanged
            else [row for row in all_rows if row.change_type != "UNCHANGED"]
        )

        return BaselineComparisonResult(
            project_id=project_id,
            baseline_a_id=baseline_a.id,
            baseline_a_name=baseline_a.name,
            baseline_a_created_at=baseline_a.created_at,
            baseline_b_id=baseline_b.id,
            baseline_b_name=baseline_b.name,
            baseline_b_created_at=baseline_b.created_at,
            total_tasks_compared=len(all_rows),
            changed_tasks=sum(1 for row in all_rows if row.change_type == "CHANGED"),
            added_tasks=sum(1 for row in all_rows if row.change_type == "ADDED"),
            removed_tasks=sum(1 for row in all_rows if row.change_type == "REMOVED"),
            unchanged_tasks=sum(1 for row in all_rows if row.change_type == "UNCHANGED"),
            rows=rows,
        )

    def _build_baseline_comparison_rows(
        self,
        project_id: str,
        baseline_a_id: str,
        baseline_b_id: str,
        include_unchanged: bool,
    ) -> list[BaselineComparisonRow]:
        baseline_a_tasks = {row.task_id: row for row in self._baseline_repo.list_tasks(baseline_a_id)}
        baseline_b_tasks = {row.task_id: row for row in self._baseline_repo.list_tasks(baseline_b_id)}

        task_name_by_id = {task.id: task.name for task in self._task_repo.list_by_project(project_id)}
        all_task_ids = set(baseline_a_tasks) | set(baseline_b_tasks)

        rows: list[BaselineComparisonRow] = []
        for task_id in all_task_ids:
            row_a = baseline_a_tasks.get(task_id)
            row_b = baseline_b_tasks.get(task_id)
            change_type = self._resolve_change_type(row_a, row_b)
            if not include_unchanged and change_type == "UNCHANGED":
                continue

            a_start = row_a.baseline_start if row_a else None
            b_start = row_b.baseline_start if row_b else None
            a_finish = row_a.baseline_finish if row_a else None
            b_finish = row_b.baseline_finish if row_b else None
            a_duration = row_a.baseline_duration_days if row_a else None
            b_duration = row_b.baseline_duration_days if row_b else None
            a_cost = float(row_a.baseline_planned_cost or 0.0) if row_a else 0.0
            b_cost = float(row_b.baseline_planned_cost or 0.0) if row_b else 0.0

            start_shift = (b_start - a_start).days if (a_start and b_start) else None
            finish_shift = (b_finish - a_finish).days if (a_finish and b_finish) else None
            duration_delta = (b_duration - a_duration) if (a_duration is not None and b_duration is not None) else None

            rows.append(
                BaselineComparisonRow(
                    task_id=task_id,
                    task_name=(
                        task_name_by_id.get(task_id)
                        or (row_b.task_name if row_b and row_b.task_name else None)
                        or (row_a.task_name if row_a and row_a.task_name else None)
                        or task_id
                    ),
                    baseline_a_start=a_start,
                    baseline_a_finish=a_finish,
                    baseline_a_duration_days=a_duration,
                    baseline_a_planned_cost=(float(row_a.baseline_planned_cost or 0.0) if row_a else None),
                    baseline_b_start=b_start,
                    baseline_b_finish=b_finish,
                    baseline_b_duration_days=b_duration,
                    baseline_b_planned_cost=(float(row_b.baseline_planned_cost or 0.0) if row_b else None),
                    start_shift_days=start_shift,
                    finish_shift_days=finish_shift,
                    duration_delta_days=duration_delta,
                    planned_cost_delta=b_cost - a_cost,
                    change_type=change_type,
                )
            )

        change_priority = {"ADDED": 0, "REMOVED": 1, "CHANGED": 2, "UNCHANGED": 3}
        rows.sort(key=lambda row: (change_priority.get(row.change_type, 9), row.task_name.lower()))
        return rows

    @staticmethod
    def _resolve_change_type(
        baseline_a_task: BaselineTask | None,
        baseline_b_task: BaselineTask | None,
    ) -> str:
        if baseline_a_task is None and baseline_b_task is not None:
            return "ADDED"
        if baseline_a_task is not None and baseline_b_task is None:
            return "REMOVED"
        if baseline_a_task is None or baseline_b_task is None:
            return "CHANGED"

        unchanged = (
            baseline_a_task.baseline_start == baseline_b_task.baseline_start
            and baseline_a_task.baseline_finish == baseline_b_task.baseline_finish
            and int(baseline_a_task.baseline_duration_days or 0) == int(baseline_b_task.baseline_duration_days or 0)
            and abs(
                float(baseline_a_task.baseline_planned_cost or 0.0)
                - float(baseline_b_task.baseline_planned_cost or 0.0)
            )
            < 1e-9
        )
        return "UNCHANGED" if unchanged else "CHANGED"


__all__ = ["ReportingBaselineCompareMixin"]
