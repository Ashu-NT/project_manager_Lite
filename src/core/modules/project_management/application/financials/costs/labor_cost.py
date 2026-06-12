"""Labor cost engine — owns all labor cost calculation logic.

Computes labor details and plan-vs-actual from assignments and project resources.
Reporting delegates here; this class is the authoritative source for labor figures.
"""

from __future__ import annotations


from src.core.platform.common.exceptions import NotFoundError
from src.core.modules.project_management.contracts.repositories.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.domain.tasks.task import TaskAssignment

from src.core.modules.project_management.application.financials.models.finance_models import (
    LaborAssignmentRow,
    LaborPlanActualRow,
    LaborResourceRow,
)


class LaborCostEngine:
    """
    Compute labor cost details and plan-vs-actual for a project.

    Uses assignment execution data (hours_logged × resolved rate) for actuals,
    and ProjectResource planning data for planned figures.
    """

    def __init__(
        self,
        *,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        assignment_repo: AssignmentRepository,
        resource_repo: ResourceRepository,
        project_resource_repo: ProjectResourceRepository,
    ) -> None:
        self._project_repo = project_repo
        self._task_repo = task_repo
        self._assignment_repo = assignment_repo
        self._resource_repo = resource_repo
        self._project_resource_repo = project_resource_repo

    def get_project_labor_details(self, project_id: str) -> list[LaborResourceRow]:
        """Return labor cost details grouped by resource for the given project."""
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        tasks = self._task_repo.list_by_project(project_id)
        task_map = {t.id: t for t in tasks}
        task_ids = list(task_map.keys())
        if not task_ids:
            return []

        assignments = self._assignment_repo.list_by_tasks(task_ids)

        by_res: dict[str, list[TaskAssignment]] = {}
        for a in assignments:
            lst = by_res.get(a.resource_id, [])
            lst.append(a)
            by_res[a.resource_id] = lst

        result: list[LaborResourceRow] = []
        for res_id, assigns in by_res.items():
            res = self._resource_repo.get(res_id)
            res_name = res.name if res else "<unknown>"
            total_hours = 0.0
            total_cost = 0.0
            as_rows: list[LaborAssignmentRow] = []
            hourly_rate: float = 0.0
            currency: str | None = None
            for a in assigns:
                hourly_rate, currency = self._resolve_project_rate_currency(project_id, a)
                hours = float(getattr(a, "hours_logged", 0.0) or 0.0)
                task_name = task_map.get(a.task_id).name if a.task_id in task_map else "<unknown>"
                cost = hours * hourly_rate
                total_hours += hours
                total_cost += cost
                as_rows.append(
                    LaborAssignmentRow(
                        assignment_id=a.id,
                        task_id=a.task_id,
                        task_name=task_name,
                        hours=hours,
                        hourly_rate=hourly_rate,
                        currency_code=currency,
                        cost=cost,
                    )
                )
            result.append(
                LaborResourceRow(
                    resource_id=res_id,
                    resource_name=res_name,
                    total_hours=total_hours,
                    hourly_rate=hourly_rate,
                    currency_code=currency,
                    total_cost=total_cost,
                    assignments=as_rows,
                )
            )

        result.sort(key=lambda r: r.total_cost, reverse=True)
        return result

    def get_project_labor_plan_vs_actual(self, project_id: str) -> list[LaborPlanActualRow]:
        """Return plan vs actual labor per resource using planning + execution data."""
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        proj_cur = (getattr(project, "currency", None) or "").upper() or None

        actual_rows = self.get_project_labor_details(project_id)
        actual_by_res: dict[str, LaborResourceRow] = {r.resource_id: r for r in actual_rows}

        prs = self._project_resource_repo.list_by_project(project_id)
        pr_by_res: dict[str, object] = {
            pr.resource_id: pr
            for pr in prs
            if getattr(pr, "resource_id", None)
        }

        resource_ids = set(actual_by_res.keys()) | set(pr_by_res.keys())

        out: list[LaborPlanActualRow] = []
        for rid in resource_ids:
            res = self._resource_repo.get(rid)
            if not res:
                continue

            pr = pr_by_res.get(rid)
            planned_hours = float(getattr(pr, "planned_hours", 0.0) or 0.0) if pr else 0.0

            planned_rate = None
            planned_cur = None
            if pr:
                if getattr(pr, "hourly_rate", None) is not None:
                    planned_rate = float(pr.hourly_rate)
                if getattr(pr, "currency_code", None):
                    planned_cur = str(pr.currency_code).upper()

            if planned_rate is None:
                planned_rate = float(getattr(res, "hourly_rate", 0.0) or 0.0)

            if not planned_cur:
                planned_cur = (str(getattr(res, "currency_code", "") or "")).upper() or proj_cur

            planned_cost = planned_hours * float(planned_rate or 0.0)

            ar = actual_by_res.get(rid)
            actual_hours = float(getattr(ar, "total_hours", 0.0) or 0.0) if ar else 0.0
            actual_cost = float(getattr(ar, "total_cost", 0.0) or 0.0) if ar else 0.0

            actual_cur = None
            if ar and getattr(ar, "currency_code", None):
                actual_cur = (ar.currency_code or "").upper() or None
            if not actual_cur:
                actual_cur = planned_cur

            out.append(LaborPlanActualRow(
                resource_id=rid,
                resource_name=getattr(res, "name", "<unknown>"),
                planned_hours=planned_hours,
                planned_hourly_rate=float(planned_rate or 0.0),
                planned_currency_code=planned_cur,
                planned_cost=planned_cost,
                actual_hours=actual_hours,
                actual_currency_code=actual_cur,
                actual_cost=actual_cost,
                variance_cost=actual_cost - planned_cost,
            ))

        out.sort(key=lambda r: r.variance_cost, reverse=True)
        return out

    def _resolve_project_rate_currency(
        self, project_id: str, assignment
    ) -> tuple[float, str | None]:
        pr = None
        pr_id = getattr(assignment, "project_resource_id", None)
        if pr_id:
            pr = self._project_resource_repo.get(pr_id)
        if not pr:
            rid = getattr(assignment, "resource_id", None)
            if rid:
                pr = self._project_resource_repo.get_for_project(project_id, rid)

        res = (
            self._resource_repo.get(getattr(assignment, "resource_id", ""))
            if getattr(assignment, "resource_id", None)
            else None
        )

        rate = None
        cur = None
        if pr:
            if getattr(pr, "hourly_rate", None) is not None:
                rate = float(pr.hourly_rate)
            if getattr(pr, "currency_code", None):
                cur = str(pr.currency_code).upper()

        if rate is None:
            rate = float(getattr(res, "hourly_rate", 0.0) or 0.0) if res else 0.0

        if not cur:
            cur = (str(getattr(res, "currency_code", "") or "")).upper() if res else None

        return rate, (cur or None)


__all__ = ["LaborCostEngine"]
