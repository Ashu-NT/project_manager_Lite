from __future__ import annotations

from typing import List

from core.exceptions import NotFoundError
from core.interfaces import (
    AssignmentRepository,
    ProjectRepository,
    ProjectResourceRepository,
    ResourceRepository,
    TaskRepository,
)
from core.models import TaskAssignment
from core.services.reporting.models import LaborAssignmentRow, LaborPlanActualRow, LaborResourceRow


class ReportingLaborMixin:
    _project_repo: ProjectRepository
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository
    _project_resource_repo: ProjectResourceRepository

    def get_project_labor_details(self, project_id: str) -> List["LaborResourceRow"]:
        """Returns labor cost details grouped by resource for the given project.

        Each LaborResourceRow contains per-resource totals and a list of assignment rows
        (task-level breakdown). Costs are calculated as hours_logged * resource.hourly_rate.
        Currency is taken from the resource.currency_code.
        """
        project = self._project_repo.get(project_id)

        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        tasks = self._task_repo.list_by_project(project_id)
        task_map = {t.id: t for t in tasks}
        task_ids = list(task_map.keys())
        if not task_ids:
            return []

        assignments = self._assignment_repo.list_by_tasks(task_ids)

        # group assignments by resource
        by_res: dict[str, List[TaskAssignment]] = {}
        for a in assignments:
            lst = by_res.get(a.resource_id, []) 
            lst.append(a)
            by_res[a.resource_id] = lst

        result: List[LaborResourceRow] = []
        for res_id, assigns in by_res.items():
            res = self._resource_repo.get(res_id)
            res_name = res.name if res else "<unknown>"
            total_hours = 0.0
            total_cost = 0.0
            as_rows: List[LaborAssignmentRow] = []
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

        # sort by highest total cost
        result.sort(key=lambda r: r.total_cost, reverse=True)
        return result

    def get_project_labor_plan_vs_actual(self, project_id: str) -> list["LaborPlanActualRow"]:
        """
        Professional labor view:
        - Planned hours/cost from ProjectResource (planning layer)
        - Actual hours/cost from logged hours (execution layer)
        """

        project = self._project_repo.get(project_id)

        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        proj_cur = (getattr(project, "currency", None) or "").upper() or None

        # Actuals from assignments (hours_logged × resolved rate)
        actual_rows = self.get_project_labor_details(project_id)
        actual_by_res: dict[str, LaborResourceRow] = {r.resource_id: r for r in actual_rows}

        # Planned from ProjectResource
        prs = self._project_resource_repo.list_by_project(project_id)
        pr_by_res: dict[str, object] = {pr.resource_id: pr for pr in prs if getattr(pr, "resource_id", None)}

        # Union of resources seen in either planned or actual
        resource_ids = set(actual_by_res.keys()) | set(pr_by_res.keys())

        out: list[LaborPlanActualRow] = []
        for rid in resource_ids:
            res = self._resource_repo.get(rid)
            # if master resource deleted, skip (UI can still show "<missing>" elsewhere)
            if not res:
                continue

            pr = pr_by_res.get(rid)

            # --- Planned ---
            planned_hours = float(getattr(pr, "planned_hours", 0.0) or 0.0) if pr else 0.0

            # planned rate/currency: ProjectResource override -> Resource default -> project currency
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

            # --- Actual ---
            ar = actual_by_res.get(rid)
            actual_hours = float(getattr(ar, "total_hours", 0.0) or 0.0) if ar else 0.0
            actual_cost = float(getattr(ar, "total_cost", 0.0) or 0.0) if ar else 0.0

            # choose a currency for actual display (prefer actual row currency, else planned)
            actual_cur = None
            if ar and getattr(ar, "currency_code", None):
                actual_cur = (ar.currency_code or "").upper() or None
            if not actual_cur:
                actual_cur = planned_cur

            variance = actual_cost - planned_cost

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

                variance_cost=variance,
            ))

        # sort by biggest overrun first
        out.sort(key=lambda r: r.variance_cost, reverse=True)
        return out

    def _resolve_project_rate_currency(self, project_id: str, assignment) -> tuple[float, str | None]:
        """
        Returns (hourly_rate, currency_code) for an assignment using:
        - ProjectResource override (if exists)
        - else Resource defaults
        """
        pr = None
        pr_id = getattr(assignment, "project_resource_id", None)
        if pr_id:
            pr = self._project_resource_repo.get(pr_id)

        # fallback: try resolve by (project_id, resource_id)
        if not pr:
            rid = getattr(assignment, "resource_id", None)
            if rid:
                pr = self._project_resource_repo.get_for_project(project_id, rid)

        res = self._resource_repo.get(getattr(assignment, "resource_id", "")) if getattr(assignment, "resource_id", None) else None

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
