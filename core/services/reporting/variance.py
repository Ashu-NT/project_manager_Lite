from __future__ import annotations

from core.services.reporting.models import TaskVarianceRow


class ReportingVarianceMixin:
    def get_baseline_schedule_variance(
        self,
        project_id: str,
        baseline_id: str | None = None,
    ) -> list[TaskVarianceRow]:
        """
        Compares baseline task dates vs current task dates.
        """
        # Get baseline tasks
        if baseline_id:
            b_tasks = self._baseline_repo.list_tasks(baseline_id)
        else:
            latest = self._baseline_repo.get_latest_for_project(project_id)
            b_tasks = self._baseline_repo.list_tasks(latest.id) if latest else []

        # Map current tasks
        tasks = self._task_repo.list_by_project(project_id)
        tasks_by_id = {t.id: t for t in tasks}

        # Critical tasks (optional – you already have get_critical_path)
        critical_ids = set()
        try:
            cp = self.get_critical_path(project_id)
            critical_ids = {info.task.id for info in cp}
        except Exception:
            pass

        rows: list[TaskVarianceRow] = []
        for bt in b_tasks:
            t = tasks_by_id.get(bt.task_id)
            if not t:
                continue

            bs = bt.baseline_start
            bf = bt.baseline_finish
            cs = getattr(t, "start_date", None)
            cf = getattr(t, "end_date", None)

            sv = None
            fv = None
            if bs and cs:
                sv = (cs - bs).days
            if bf and cf:
                fv = (cf - bf).days

            rows.append(TaskVarianceRow(
                task_id=bt.task_id,
                task_name=getattr(t, "name", bt.task_id),
                baseline_start=bs,
                baseline_finish=bf,
                current_start=cs,
                current_finish=cf,
                start_variance_days=sv,
                finish_variance_days=fv,
                is_critical=(bt.task_id in critical_ids),
            ))

        # Sort: critical first, then largest finish variance
        rows.sort(key=lambda r: (not r.is_critical, -(r.finish_variance_days or 0)))
        return rows
