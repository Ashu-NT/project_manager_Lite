from __future__ import annotations

from datetime import date
from typing import Dict, Optional

from core.exceptions import BusinessRuleError
from core.interfaces import BaselineRepository, CostRepository, ProjectRepository, TaskRepository
from core.services.reporting.models import EarnedValueMetrics
from core.services.work_calendar.engine import WorkCalendarEngine


class ReportingEvmCoreMixin:
    _baseline_repo: BaselineRepository
    _task_repo: TaskRepository
    _calendar: WorkCalendarEngine
    _project_repo: ProjectRepository
    _cost_repo: CostRepository

    def get_earned_value(
        self,
        project_id: str,
        as_of: Optional[date] = None,
        baseline_id: Optional[str] = None,
    ) -> EarnedValueMetrics:
        """
        PM-grade Earned Value (EVM) computation.

        - BAC from baseline task planned cost sum.
        - PV: cost-weighted PV by default; falls back to duration-weighted PV when baseline costs are missing.
        - EV: baseline planned cost * actual % complete (falls back to duration-weighted planned cost if needed).
        - AC: sums actual costs up to 'as_of' (respects incurred_date when present).

        Returns CPI/SPI/EAC/ETC/VAC + optional TCPI and a PM-friendly notes string.
        """
        from datetime import date as _date

        as_of = as_of or _date.today()
        notes = []

        if baseline_id:
            baseline = self._baseline_repo.get_baseline(baseline_id)
        else:
            baseline = self._baseline_repo.get_latest_for_project(project_id)

        if not baseline:
            raise BusinessRuleError("No baseline found. Create a baseline first.", code="NO_BASELINE")

        b_tasks = self._baseline_repo.list_tasks(baseline.id)
        if not b_tasks:
            raise BusinessRuleError("Baseline has no tasks. Recreate baseline.", code="BASELINE_EMPTY")

        tasks = {t.id: t for t in self._task_repo.list_by_project(project_id)}

        def clamp01(x: float) -> float:
            return max(0.0, min(1.0, x))

        def working_days_inclusive(start: date, end: date) -> int:
            return max(0, self._calendar.working_days_between(start, end))

        BAC = float(sum(bt.baseline_planned_cost for bt in b_tasks))

        project = self._project_repo.get(project_id)
        if BAC <= 0 and project and getattr(project, "planned_budget", None):
            BAC = float(project.planned_budget or 0.0)
            notes.append("BAC set from project planned budget (project.planned_budget).")

        sum_task_costs = float(
            sum(bt.baseline_planned_cost for bt in b_tasks if bt.baseline_planned_cost > 0)
        )
        has_cost_loaded_baseline = sum_task_costs > 0.0

        durations: Dict[str, int] = {}
        for bt in b_tasks:
            dur = int(bt.baseline_duration_days or 0)
            if dur <= 0 and bt.baseline_start and bt.baseline_finish:
                dur = working_days_inclusive(bt.baseline_start, bt.baseline_finish)
            durations[bt.task_id] = max(0, dur)

        total_duration = sum(durations.values())

        if BAC <= 0:
            notes.append(
                "BAC is 0 (baseline has no planned cost). Enter planned costs and recreate baseline for EVM."
            )

        PV = 0.0

        if has_cost_loaded_baseline:
            for bt in b_tasks:
                cost = float(bt.baseline_planned_cost or 0.0)
                if cost <= 0:
                    continue
                if not bt.baseline_start or not bt.baseline_finish:
                    continue

                if as_of <= bt.baseline_start:
                    frac = 0.0
                elif as_of >= bt.baseline_finish:
                    frac = 1.0
                else:
                    total_wd = working_days_inclusive(bt.baseline_start, bt.baseline_finish)
                    if total_wd <= 0:
                        frac = 0.0
                    else:
                        done_wd = working_days_inclusive(bt.baseline_start, as_of)
                        frac = clamp01(done_wd / total_wd)

                PV += cost * frac

        else:
            if BAC > 0 and total_duration > 0:
                for bt in b_tasks:
                    dur = durations.get(bt.task_id, 0)
                    if dur <= 0:
                        continue
                    if not bt.baseline_start or not bt.baseline_finish:
                        continue

                    task_budget = BAC * (dur / total_duration)

                    if as_of <= bt.baseline_start:
                        frac = 0.0
                    elif as_of >= bt.baseline_finish:
                        frac = 1.0
                    else:
                        total_wd = working_days_inclusive(bt.baseline_start, bt.baseline_finish)
                        if total_wd <= 0:
                            frac = 0.0
                        else:
                            done_wd = working_days_inclusive(bt.baseline_start, as_of)
                            frac = clamp01(done_wd / total_wd)

                    PV += task_budget * frac

                notes.append(
                    "PV computed using duration-weighted BAC (baseline costs not loaded per task)."
                )
            else:
                if BAC > 0 and project and getattr(project, "start_date", None) and getattr(project, "end_date", None):
                    proj_total_wd = working_days_inclusive(project.start_date, project.end_date)
                    if proj_total_wd > 0:
                        proj_done_wd = working_days_inclusive(project.start_date, as_of)
                        frac = clamp01(proj_done_wd / proj_total_wd)
                        PV = BAC * frac
                        notes.append(
                            "PV computed using project-level schedule and BAC (fallback to project planned budget)."
                        )
                    else:
                        notes.append("PV is 0 (no baseline cost-loading and no usable durations/dates).")
                else:
                    notes.append("PV is 0 (no baseline cost-loading and no usable durations/dates).")

        EV = 0.0

        if has_cost_loaded_baseline:
            for bt in b_tasks:
                t = tasks.get(bt.task_id)
                if not t:
                    continue
                pc = float(getattr(t, "percent_complete", 0.0) or 0.0)
                pc = clamp01(pc / 100.0)
                EV += float(bt.baseline_planned_cost or 0.0) * pc
        else:
            if BAC > 0 and total_duration > 0:
                for bt in b_tasks:
                    t = tasks.get(bt.task_id)
                    if not t:
                        continue
                    dur = durations.get(bt.task_id, 0)
                    if dur <= 0:
                        continue
                    task_budget = BAC * (dur / total_duration)

                    pc = float(getattr(t, "percent_complete", 0.0) or 0.0)
                    pc = clamp01(pc / 100.0)
                    EV += task_budget * pc

                notes.append(
                    "EV computed using duration-weighted BAC (baseline costs not loaded per task)."
                )

        if EV <= 0:
            notes.append("EV is 0 (tasks may have 0% progress or baseline budget is missing).")

        cost_items = self._cost_repo.list_by_project(project_id)
        labor_rows = self.get_project_labor_details(project_id)
        project = self._project_repo.get(project_id)
        project_currency = project.currency if project else None

        if project_currency:
            labor_total = sum(
                r.total_cost
                for r in labor_rows
                if (r.currency_code or project_currency or "").upper() == project_currency.upper()
            )
        else:
            labor_total = sum(r.total_cost for r in labor_rows)

        from core.models import CostType

        if labor_total > 0:
            filtered_items = [
                ci for ci in cost_items if getattr(ci, "cost_type", None) != CostType.LABOR
            ]
        else:
            filtered_items = cost_items

        AC = 0.0
        for c in filtered_items:
            amt = float(getattr(c, "actual_amount", 0.0) or 0.0)
            if amt <= 0:
                continue
            inc = getattr(c, "incurred_date", None)
            if inc is not None and inc > as_of:
                continue
            AC += amt

        AC += float(labor_total or 0.0)

        if AC <= 0:
            notes.append(
                "AC is 0 (no actual costs recorded up to the as-of date, including logged labor)."
            )

        CPI = (EV / AC) if AC > 0 else None
        SPI = (EV / PV) if PV > 0 else None

        EAC = (BAC / CPI) if (CPI is not None and CPI > 0) else None
        ETC = (EAC - AC) if EAC is not None else None
        VAC = (BAC - EAC) if EAC is not None else None

        TCPI_to_BAC = None
        tcpi_note = None
        den_bac = BAC - AC
        num = BAC - EV
        if den_bac > 0:
            TCPI_to_BAC = num / den_bac
        else:
            tcpi_note = "TCPI(BAC) N/A AC >= BAC (already over baseline budget)"

        if tcpi_note:
            notes.append(tcpi_note)

        TCPI_to_EAC = None
        if EAC is not None:
            den_eac = EAC - AC
            if den_eac > 0:
                TCPI_to_EAC = num / den_eac

        if BAC > 0 and AC > 0 and AC > 5 * BAC:
            notes.append("Warning: AC is much larger than BAC. Check currency/units or baseline planned costs.")

        return EarnedValueMetrics(
            as_of=as_of,
            baseline_id=baseline.id,
            BAC=BAC,
            PV=PV,
            EV=EV,
            AC=AC,
            CPI=CPI,
            SPI=SPI,
            EAC=EAC,
            ETC=ETC,
            VAC=VAC,
            TCPI_to_BAC=TCPI_to_BAC,
            TCPI_to_EAC=TCPI_to_EAC,
            notes=" ".join(notes) if notes else None,
        )
