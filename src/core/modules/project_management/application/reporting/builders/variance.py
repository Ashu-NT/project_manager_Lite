from __future__ import annotations

import logging

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.dashboard.models.report_models import (
    TaskVarianceRow,
)
from src.core.modules.project_management.application.reporting.builders.access import (
    ReportingAccessPolicy,
)
from src.core.modules.project_management.contracts.ports.reporting.critical_path import (
    CriticalPathReport,
)
from src.core.modules.project_management.contracts.repositories.scheduling.baseline import (
    BaselineRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks
from src.core.platform.common.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class ScheduleVarianceReportBuilder(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        *,
        access: ReportingAccessPolicy,
        baseline_repo: BaselineRepository,
        task_repo: TaskRepository,
        critical_path: CriticalPathReport,
        module_catalog_service=None,
    ) -> None:
        self._access = access
        self._baseline_repo = baseline_repo
        self._task_repo = task_repo
        self._critical_path = critical_path
        self._user_session = access.user_session
        self._module_catalog_service = module_catalog_service

    def get_baseline_schedule_variance(
        self,
        project_id: str,
        baseline_id: str | None = None,
    ) -> list[TaskVarianceRow]:
        """Compares baseline task dates vs current task dates."""
        self._access.require_view("view schedule variance", project_id=project_id)
        if baseline_id:
            baseline = self._baseline_repo.get_baseline(baseline_id)
            if baseline is None or baseline.project_id != project_id:
                raise NotFoundError("Baseline not found.", code="BASELINE_NOT_FOUND")
            b_tasks = self._baseline_repo.list_tasks(baseline_id)
        else:
            latest = self._baseline_repo.get_latest_for_project(project_id)
            b_tasks = self._baseline_repo.list_tasks(latest.id) if latest else []

        tasks = select_leaf_tasks(self._task_repo.list_by_project(project_id))
        tasks_by_id = {t.id: t for t in tasks}

        # Critical-path task ids, best-effort -- not required for variance itself.
        critical_ids: set[str] = set()
        try:
            cp = self._critical_path.get_critical_path(project_id)
            critical_ids = {info.task.id for info in cp}
        except Exception:
            logger.exception("Failed to resolve critical path project_id=%s",
                            project_id,)

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


__all__ = [ "ScheduleVarianceReportBuilder"]
