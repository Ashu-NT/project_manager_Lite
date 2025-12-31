# core/services/reporting_service.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple

import calendar
from sqlalchemy.orm import Session

#from core.models import Project, Task, Resource
from core.interfaces import (
    ProjectRepository,
    TaskRepository,
    ResourceRepository,
    AssignmentRepository,
    CostRepository,
    BaselineRepository,
    ProjectResourceRepository
)
from core.exceptions import NotFoundError
from ._base_service import ServiceBase
from .scheduling_service import SchedulingEngine, CPMTaskInfo
from .work_calendar_engine import WorkCalendarEngine
from core.exceptions import BusinessRuleError
from core.models import CostType, TaskAssignment,ProjectResource


@dataclass
class EvmSeriesPoint:
    period_end: date
    PV: float
    EV: float
    AC: float
    BAC: float
    CPI: float
    SPI: float

@dataclass
class EarnedValueMetrics:
    as_of: date
    baseline_id: str

    BAC: float  # Budget at Completion
    PV: float   # Planned Value
    EV: float   # Earned Value
    AC: float   # Actual Cost

    CPI: Optional[float]
    SPI: Optional[float]
    EAC: Optional[float]
    ETC: Optional[float]
    VAC: Optional[float]
    TCPI_to_BAC: Optional[float] = None
    TCPI_to_EAC: Optional[float] = None
    notes: Optional[str] =None

@dataclass
class LaborAssignmentRow:
    assignment_id: str
    task_id: str
    task_name: str
    hours: float
    hourly_rate: float
    currency_code: Optional[str]
    cost: float

@dataclass
class LaborResourceRow:
    resource_id: str
    resource_name: str
    total_hours: float
    hourly_rate: float
    currency_code: Optional[str]
    total_cost: float
    assignments: List[LaborAssignmentRow]

@dataclass
class LaborPlanActualRow:
    resource_id: str
    resource_name: str

    planned_hours: float
    planned_hourly_rate: float
    planned_currency_code: Optional[str]
    planned_cost: float

    actual_hours: float
    actual_currency_code: Optional[str]
    actual_cost: float

    variance_cost: float  # actual - planned

@dataclass
class GanttTaskBar:
    task_id: str
    name: str
    start: Optional[date]
    end: Optional[date]
    is_critical: bool
    percent_complete: float
    status: str


@dataclass
class ProjectKPI:
    project_id: str
    name: str
    start_date: Optional[date]
    end_date: Optional[date]
    duration_working_days: Optional[int]
    tasks_total: int
    tasks_completed: int
    tasks_in_progress: int
    task_blocked: int
    tasks_not_started: int
    critical_tasks: int
    late_tasks: int
    total_planned_cost: float
    total_actual_cost: float
    cost_variance: float  # actual - planned
    total_committed_cost: float
    committment_variance: float


@dataclass
class ResourceLoadRow:
    resource_id: str
    resource_name: str
    total_allocation_percent: float
    tasks_count: int

@dataclass
class TaskVarianceRow:
    task_id: str
    task_name: str
    baseline_start: date | None
    baseline_finish: date | None
    current_start: date | None
    current_finish: date | None
    start_variance_days: int | None
    finish_variance_days: int | None
    is_critical: bool

@dataclass
class CostBreakdownRow:
    cost_type: str
    currency: str
    planned: float
    actual: float

class ReportingService(ServiceBase):
    """
    High-level reporting facade:
    - Gantt data
    - Project KPIs (schedule & costs)
    - Critical path overview
    - Resource utilization summary
    """

    def __init__(
        self,
        session: Session,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        resource_repo: ResourceRepository,
        assignment_repo: AssignmentRepository,
        cost_repo: CostRepository,
        scheduling_engine: SchedulingEngine,
        calendar: WorkCalendarEngine,
        baseline_repo : BaselineRepository,
        project_resource_repo: ProjectResourceRepository
    ):
        super().__init__(session)
        self._project_repo = project_repo
        self._task_repo = task_repo
        self._resource_repo = resource_repo
        self._assignment_repo = assignment_repo
        self._cost_repo = cost_repo
        self._scheduling_engine = scheduling_engine
        self._calendar = calendar
        self._baseline_repo = baseline_repo
        self._project_resource_repo = project_resource_repo

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_gantt_data(self, project_id: str) -> List[GanttTaskBar]:
        """
        Returns a list of GanttTaskBars, ensuring schedule is up to date (CPM).
        """
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        cpm_result = self._scheduling_engine.recalculate_project_schedule(project_id)
        # cpm_result: Dict[task_id, CPMTaskInfo]
        bars: List[GanttTaskBar] = []

        for tid, info in cpm_result.items():
            t = info.task
            bars.append(
                GanttTaskBar(
                    task_id=t.id,
                    name=t.name,
                    start=info.earliest_start,
                    end=info.earliest_finish,
                    is_critical=info.is_critical,
                    percent_complete=t.percent_complete or 0.0,
                    status=t.status.value if hasattr(t.status, "value") else str(t.status),
                )
            )
        # Also include unscheduled tasks (no ES/EF)
        all_tasks = {t.id: t for t in self._task_repo.list_by_project(project_id)}
        for tid, t in all_tasks.items():
            if tid not in cpm_result:
                bars.append(
                    GanttTaskBar(
                        task_id=t.id,
                        name=t.name,
                        start=t.start_date,
                        end=t.end_date,
                        is_critical=False,
                        percent_complete=t.percent_complete or 0.0,
                        status=t.status.value if hasattr(t.status, "value") else str(t.status),
                    )
                )
        return bars

    def get_project_kpis(self, project_id: str) -> ProjectKPI:
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        tasks = self._task_repo.list_by_project(project_id)
        tasks_total = len(tasks)
        tasks_completed = sum(1 for t in tasks if str(t.status) in ("TaskStatus.DONE", "DONE"))
        tasks_in_progress = sum(1 for t in tasks if str(t.status) in ("TaskStatus.IN_PROGRESS", "IN_PROGRESS"))
        task_blocked = sum(1 for t in tasks if str(t.status) in ("TaskStatus.BLOCKED", "BLOCKED"))
        tasks_not_started = tasks_total - tasks_completed - tasks_in_progress- task_blocked

        # Reuse CPM data for critical & late tasks
        cpm_result: Dict[str, CPMTaskInfo] = self._scheduling_engine.recalculate_project_schedule(project_id)
        critical_tasks = sum(1 for info in cpm_result.values() if info.is_critical)
        late_tasks = sum(
            1
            for info in cpm_result.values()
            if info.late_by_days is not None and info.late_by_days > 0
        )

        # Project dates & duration
        start_date = project.start_date
        end_date = project.end_date
        duration_working_days = None
        if start_date and end_date:
            duration_working_days = self._calendar.working_days_between(start_date, end_date)

        # Cost summary
        cost_items = self._cost_repo.list_by_project(project_id)
        # computed labor totals (in project currency if set)
        labor_rows = self.get_project_labor_details(project_id)
        project_currency = project.currency if project else None
        if project_currency:
            computed_labor_total = sum(r.total_cost for r in labor_rows if (r.currency_code or project_currency or "").upper() == project_currency.upper())
        else:
            computed_labor_total = sum(r.total_cost for r in labor_rows)

        if computed_labor_total > 0:
            # ignore manual labor CostItems to avoid double counting
            filtered = [ci for ci in cost_items if getattr(ci, 'cost_type', None) != CostType.LABOR]
        else:
            filtered = cost_items

        # -------------------------
        # Planned totals (NEW planning model)
        # planned = planned CostItems + planned ProjectResource labor
        # Budget is NOT used as planned; budget is a reference/limit.
        # -------------------------

        proj_cur = (project.currency or "").upper() if project and getattr(project, "currency", None) else None

        # Planned CostItems (typed)
        planned_costitems_total = 0.0
        for ci in filtered:
            amt = float(getattr(ci, "planned_amount", 0.0) or 0.0)
            if amt <= 0:
                continue

            if proj_cur:
                cur = (getattr(ci, "currency_code", None) or proj_cur or "").upper()
                if cur != proj_cur:
                    continue
            planned_costitems_total += amt

        # Planned labor from ProjectResources
        planned_labor_total = 0.0
        prs = self._project_resource_repo.list_by_project(project_id)
        for pr in prs:
            if not getattr(pr, "is_active", True):
                continue

            ph = float(getattr(pr, "planned_hours", 0.0) or 0.0)
            if ph <= 0:
                continue

            res = self._resource_repo.get(pr.resource_id)

            rate = float(pr.hourly_rate) if getattr(pr, "hourly_rate", None) is not None else float(getattr(res, "hourly_rate", 0.0) or 0.0)
            if rate <= 0:
                continue

            # currency filter if project currency is set
            if proj_cur:
                pr_cur = (getattr(pr, "currency_code", None) or getattr(res, "currency_code", None) or proj_cur or "").upper()
                if pr_cur != proj_cur:
                    continue

            planned_labor_total += ph * rate

        total_planned = float(planned_costitems_total + planned_labor_total)

        # -------------------------
        # Actual/Committed totals
        # -------------------------
        total_actual = sum(float(getattr(ci, "actual_amount", 0.0) or 0.0) for ci in filtered) + float(computed_labor_total or 0.0)
        total_committed = sum(float(getattr(ci, "committed_amount", 0.0) or 0.0) for ci in filtered)

        cost_variance = float(total_actual - total_planned)
        committed_variance = float(total_committed - total_planned)

        return ProjectKPI(
            project_id=project.id,
            name=project.name,
            start_date=start_date,
            end_date=end_date,
            duration_working_days=duration_working_days,
            tasks_total=tasks_total,
            tasks_completed=tasks_completed,
            tasks_in_progress=tasks_in_progress,
            task_blocked=task_blocked,
            tasks_not_started=tasks_not_started,
            critical_tasks=critical_tasks,
            late_tasks=late_tasks,
            
            total_planned_cost=total_planned,
            total_committed_cost= total_committed,
            total_actual_cost=total_actual,
            cost_variance=cost_variance,
            committment_variance= committed_variance,
        )

    def get_critical_path(self, project_id: str) -> List[CPMTaskInfo]:
        """
        Return critical tasks in topological order (approximate critical path).
        """
        cpm_result = self._scheduling_engine.recalculate_project_schedule(project_id)
        critical = [info for info in cpm_result.values() if info.is_critical]
        # Sort by ES to show actual path order
        critical.sort(key=lambda info: (info.earliest_start or date.min))
        return critical

    def get_resource_load_summary(self, project_id: str) -> List[ResourceLoadRow]:
        """
        Simple resource load: for a given project, sum allocation_percent across its tasks.
        Not a time-phased histogram, but a quick overview.
        """
        tasks = self._task_repo.list_by_project(project_id)
        task_ids = [t.id for t in tasks]
        if not task_ids:
            return []

        assignments = self._assignment_repo.list_by_tasks(task_ids)
        # group by resource
        load_by_res: Dict[str, Tuple[float, int]] = {}
        for a in assignments:
            total, count = load_by_res.get(a.resource_id, (0.0, 0))
            total += a.allocation_percent or 0.0
            count += 1
            load_by_res[a.resource_id] = (total, count)

        rows: List[ResourceLoadRow] = []
        for res_id, (total_alloc, count) in load_by_res.items():
            res = self._resource_repo.get(res_id)
            name = res.name if res else "<unknown>"
            rows.append(
                ResourceLoadRow(
                    resource_id=res_id,
                    resource_name=name,
                    total_allocation_percent=total_alloc,
                    tasks_count=count,
                )
            )

        # Sort by highest total allocation
        rows.sort(key=lambda r: r.total_allocation_percent, reverse=True)
        return rows

    # -------------------------
    # Labor cost aggregation
    # -------------------------
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

        # --- choose baseline ---
        if baseline_id:
            baseline = self._baseline_repo.get_baseline(baseline_id)
        else:
            baseline = self._baseline_repo.get_latest_for_project(project_id)

        if not baseline:
            raise BusinessRuleError("No baseline found. Create a baseline first.", code="NO_BASELINE")

        b_tasks = self._baseline_repo.list_tasks(baseline.id)
        if not b_tasks:
            raise BusinessRuleError("Baseline has no tasks. Recreate baseline.", code="BASELINE_EMPTY")

        # Current tasks (for percent_complete)
        tasks = {t.id: t for t in self._task_repo.list_by_project(project_id)}

        # -------------------------
        # Helpers
        # -------------------------
        def clamp01(x: float) -> float:
            return max(0.0, min(1.0, x))

        def working_days_inclusive(start: date, end: date) -> int:
            # Your engine likely counts working days between two dates; keep consistent with your implementation.
            # If your engine is inclusive/exclusive, adjust here to match.
            return max(0, self._calendar.working_days_between(start, end))

        # -------------------------
        # BAC
        # -------------------------
        BAC = float(sum(bt.baseline_planned_cost for bt in b_tasks))

        # If BAC is zero, fallback to the project's planned budget (conservative behavior)
        project = self._project_repo.get(project_id)
        if BAC <= 0 and project and getattr(project, 'planned_budget', None):
            BAC = float(project.planned_budget or 0.0)
            
            notes.append("BAC set from project planned budget (project.planned_budget).")

        # -------------------------
        # Determine whether baseline has meaningful cost-loading
        # -------------------------
        sum_task_costs = float(sum(bt.baseline_planned_cost for bt in b_tasks if bt.baseline_planned_cost > 0))
        has_cost_loaded_baseline = sum_task_costs > 0.0
        
        
        # For fallback weighting, we use baseline_duration_days (or derive from dates)
        durations: Dict[str, int] = {}
        for bt in b_tasks:
            dur = int(bt.baseline_duration_days or 0)
            # If duration is 0 but we have dates, derive working days
            if dur <= 0 and bt.baseline_start and bt.baseline_finish:
                dur = working_days_inclusive(bt.baseline_start, bt.baseline_finish)
            durations[bt.task_id] = max(0, dur)

        total_duration = sum(durations.values())

        # If BAC is 0 (no baseline costs at all), PV/EV will not be meaningful.
        # We'll still compute AC, and return notes that baseline has no cost budget.
        

        if BAC <= 0:
            notes.append("BAC is 0 (baseline has no planned cost). Enter planned costs and recreate baseline for EVM.")

        # -------------------------
        # Planned value (PV)
        # -------------------------
        PV = 0.0

        if has_cost_loaded_baseline:
            # --- Cost-weighted PV (preferred) ---
            
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
            # --- Fallback PV: duration-weighted BAC (professional fallback) ---
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

                notes.append("PV computed using duration-weighted BAC (baseline costs not loaded per task).")
            else:
                # Try project-level schedule fallback (use project start/end if available)
                if BAC > 0 and project and getattr(project, 'start_date', None) and getattr(project, 'end_date', None):
                    proj_total_wd = working_days_inclusive(project.start_date, project.end_date)
                    if proj_total_wd > 0:
                        proj_done_wd = working_days_inclusive(project.start_date, as_of)
                        frac = clamp01(proj_done_wd / proj_total_wd)
                        PV = BAC * frac
                        notes.append("PV computed using project-level schedule and BAC (fallback to project planned budget).")
                    else:
                        notes.append("PV is 0 (no baseline cost-loading and no usable durations/dates).")
                else:
                    # Can't compute time-phased PV meaningfully
                    notes.append("PV is 0 (no baseline cost-loading and no usable durations/dates).")
        # -------------------------
        # Earned value (EV)
        # -------------------------
        EV = 0.0

        if has_cost_loaded_baseline:
            # EV from baseline planned cost * % complete
            for bt in b_tasks:
                t = tasks.get(bt.task_id)
                if not t:
                    continue
                pc = float(getattr(t, "percent_complete",0.0) or 0.0)
                
                pc = clamp01(pc / 100.0)
                EV += float(bt.baseline_planned_cost or 0.0) * pc
        else:
            # Fallback EV: duration-weighted budget * % complete
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

                notes.append("EV computed using duration-weighted BAC (baseline costs not loaded per task).")
            else:
                # EV remains 0 if there's no budget basis
                pass

        if EV <= 0:
            notes.append("EV is 0 (tasks may have 0% progress or baseline budget is missing).")


        # -------------------------
        # Actual cost (AC)
        # -------------------------
        cost_items = self._cost_repo.list_by_project(project_id)

        # labor totals (hours_logged × hourly_rate)
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
            # avoid double counting if user also entered labor CostItems manually
            filtered_items = [ci for ci in cost_items if getattr(ci, "cost_type", None) != CostType.LABOR]
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

        # add computed labor (no dates on hours_logged -> treated as incurred-to-date)
        AC += float(labor_total or 0.0)

        if AC <= 0:
            notes.append("AC is 0 (no actual costs recorded up to the as-of date, including logged labor).")

        # -------------------------
        # Indices + Forecasts
        # -------------------------
        CPI = (EV / AC) if AC > 0 else None
        SPI = (EV / PV) if PV > 0 else None

        # EAC: common default: BAC / CPI (only when CPI is meaningful)
        EAC = (BAC / CPI) if (CPI is not None and CPI > 0) else None
        ETC = (EAC - AC) if EAC is not None else None
        VAC = (BAC - EAC) if EAC is not None else None

        # TCPI (optional)
        TCPI_to_BAC = None
        tcpi_note = None
        den_bac = (BAC - AC)
        num = (BAC - EV)
        if den_bac > 0:
            TCPI_to_BAC = num / den_bac
        else:
            tcpi_note = "TCPI(BAC) N/A AC >= BAC (already over baseline budget)"

        if tcpi_note:
            notes.append(tcpi_note)
        
        TCPI_to_EAC = None
        if EAC is not None:
            den_eac = (EAC - AC)
            if den_eac > 0:
                TCPI_to_EAC = num / den_eac

        # Add practical warnings (PM-friendly)
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
     
        
    def get_evm_series(
        self,
        project_id: str,
        baseline_id: str | None = None,
        as_of: date | None = None,
        freq: str = "M",  # "M" monthly
    ) -> list[EvmSeriesPoint]:
        """
        Returns cumulative PV/EV/AC at each period end (monthly by default).
        Uses get_earned_value() repeatedly (simple + consistent).
        """
        proj = self._project_repo.get(project_id)
        if not proj:
            return []

        if as_of is None:
            as_of = date.today()

        # Determine start date for series
        start = proj.start_date or as_of
        # If baseline exists, use earliest baseline start as series start
        if baseline_id:
            b_tasks = self._baseline_repo.list_tasks(baseline_id)
        else:
            latest = self._baseline_repo.get_latest_for_project(project_id)
            b_tasks = self._baseline_repo.list_tasks(latest.id) if latest else []

        if b_tasks:
            starts = [bt.baseline_start for bt in b_tasks if bt.baseline_start]
            if starts:
                start = min(starts)

        # Build period ends
        points: list[date] = []
        cur = _month_end(start)
        end = _month_end(as_of)

        while cur <= end:
            points.append(cur)
            cur = _month_end(_add_months(cur, 1))

        out: list[EvmSeriesPoint] = []
        for pe in points:
            evm = self.get_earned_value(project_id, baseline_id=baseline_id, as_of=pe)
            PV = float(getattr(evm,"PV", 0.0) or 0.0)
            EV = float(getattr(evm,"EV", 0.0) or 0.0)
            AC = float(getattr(evm,"AC", 0.0) or 0.0)
            BAC = float(getattr(evm,"BAC", 0.0) or 0.0)
            CPI = float(getattr(evm,"CPI", 0.0) or 0.0)
            SPI = float(getattr(evm,"SPI", 0.0) or 0.0)

            out.append(EvmSeriesPoint(pe, PV, EV, AC, BAC, CPI, SPI))

        return out 

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
            critical_ids = set(cp.get("critical_task_ids", []) or [])
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
    
def _month_end(d: date) -> date:
        last = calendar.monthrange(d.year, d.month)[1]
        return date(d.year, d.month, last)

def _add_months(d: date, months: int) -> date:
        y = d.year + (d.month - 1 + months) // 12
        m = (d.month - 1 + months) % 12 + 1
        day = min(d.day, calendar.monthrange(y, m)[1])
        return date(y, m, day)
    