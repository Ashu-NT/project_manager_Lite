from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple

from core.models import CostType
from core.services.reporting.models import CostBreakdownRow


class ReportingCostBreakdownMixin:
    def get_cost_breakdown(
        self,
        project_id: str,
        as_of: Optional[date] = None,
        baseline_id: Optional[str] = None,
    ) -> List["CostBreakdownRow"]:
        """
        Planned vs Actual cost breakdown by CostType and currency.

        Updated for ProjectResource planning model:
        - Planned includes:
            (a) CostItems.planned_amount grouped by CostType
            (b) Planned labor from ProjectResource.planned_hours × resolved hourly rate
        - Actual includes:
            (a) CostItems.actual_amount (to as_of)
            (b) Computed labor from assignments (hours_logged × resolved hourly rate)
        - Avoids double counting manual LABOR CostItems when computed labor exists.

        """
        as_of = as_of or date.today()

        project = self._project_repo.get(project_id)
        proj_cur = (project.currency or "").upper() if project else ""

        # --- choose baseline (kept for optional fallback only) ---
        if baseline_id:
            baseline = self._baseline_repo.get_baseline(baseline_id)
        else:
            baseline = self._baseline_repo.get_latest_for_project(project_id)

        b_tasks = self._baseline_repo.list_tasks(baseline.id) if baseline else []

        # -------------------------
        # ACTUAL map
        # -------------------------
        cost_items = self._cost_repo.list_by_project(project_id)

        labor_rows = self.get_project_labor_details(project_id)
        project_currency = project.currency if project else None

        if project_currency:
            labor_total = sum(
                float(r.total_cost or 0.0)
                for r in labor_rows
                if (r.currency_code or project_currency or "").upper() == project_currency.upper()
            )
            labor_currency = project_currency.upper()
        else:
            labor_total = sum(float(r.total_cost or 0.0) for r in labor_rows)
            labor_currency = (proj_cur or "").upper().strip() or "—"

        if labor_total > 0:
            filtered_items = [ci for ci in cost_items if getattr(ci, "cost_type", None) != CostType.LABOR]
        else:
            filtered_items = cost_items

        actual_map: Dict[Tuple[CostType, str], float] = {}
        for c in filtered_items:
            amt = float(getattr(c, "actual_amount", 0.0) or 0.0)
            if amt <= 0:
                continue
            inc = getattr(c, "incurred_date", None)
            if inc is not None and inc > as_of:
                continue

            ct = getattr(c, "cost_type", None) or CostType.OTHER
            cur = (getattr(c, "currency_code", None) or proj_cur or "").upper().strip() or "—"
            actual_map[(ct, cur)] = actual_map.get((ct, cur), 0.0) + amt

        if labor_total > 0:
            actual_map[(CostType.LABOR, labor_currency or "—")] = actual_map.get((CostType.LABOR, labor_currency or "—"), 0.0) + float(labor_total)

        # -------------------------
        # PLANNED map
        # -------------------------
        planned_map: Dict[Tuple[CostType, str], float] = {}

        # (1) Planned from CostItems (typed)
        planned_sum = 0.0
        for c in cost_items:
            amt = float(getattr(c, "planned_amount", 0.0) or 0.0)
            if amt <= 0:
                continue
            ct = getattr(c, "cost_type", None) or CostType.OTHER
            cur = (getattr(c, "currency_code", None) or proj_cur or "").upper().strip() or "—"
            planned_map[(ct, cur)] = planned_map.get((ct, cur), 0.0) + amt
            planned_sum += amt

        # (2) Planned labor from ProjectResource planned_hours × resolved rate
        # Uses project override rate/currency if present, else resource defaults, else project currency
        prs = self._project_resource_repo.list_by_project(project_id)
        for pr in prs:
            if not getattr(pr, "is_active", True):
                continue
            ph = float(getattr(pr, "planned_hours", 0.0) or 0.0)
            if ph <= 0:
                continue

            res = self._resource_repo.get(pr.resource_id)
            rate = None
            cur = None

            if getattr(pr, "hourly_rate", None) is not None:
                rate = float(pr.hourly_rate)
            if getattr(pr, "currency_code", None):
                cur = str(pr.currency_code).upper()

            if rate is None:
                rate = float(getattr(res, "hourly_rate", 0.0) or 0.0) if res else 0.0

            if not cur:
                cur = (getattr(res, "currency_code", None) or proj_cur or "—")
                cur = str(cur).upper().strip() or "—"

            if rate <= 0:
                continue

            planned_labor_cost = ph * rate
            planned_map[(CostType.LABOR, cur)] = planned_map.get((CostType.LABOR, cur), 0.0) + planned_labor_cost
            planned_sum += planned_labor_cost

        # (3) Optional baseline fallback ONLY if there is literally no planning data
        # This prevents "planned labor = 0" when you actually planned labor via ProjectResources.
        if planned_sum <= 0.0:
            baseline_total = float(sum(float(getattr(bt, "baseline_planned_cost", 0.0) or 0.0) for bt in b_tasks))
            if baseline_total > 0:
                planned_map[(CostType.OTHER, proj_cur or "—")] = baseline_total

        # NOTE: Removed the project.planned_budget fallback that buckets into OTHER.
        # Budget belongs in the UI summary, not in cost breakdown categories.

        # -------------------------
        # Merge into rows
        # -------------------------
        keys = set(planned_map.keys()) | set(actual_map.keys())
        rows: List["CostBreakdownRow"] = []

        for (ct, cur) in sorted(keys, key=lambda x: (str(x[0]), x[1])):
            planned = float(planned_map.get((ct, cur), 0.0) or 0.0)
            actual = float(actual_map.get((ct, cur), 0.0) or 0.0)
            rows.append(CostBreakdownRow(
                cost_type=str(ct),
                currency=cur,
                planned=planned,
                actual=actual,
            ))

        return rows
