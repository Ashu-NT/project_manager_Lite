# core/services/dashboard_service.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from core.services.reporting.service import ReportingService
from core.services.reporting.models import ProjectKPI, ResourceLoadRow
from core.services.task.service import TaskService
from core.services.project.service import ProjectService
from core.services.scheduling.engine import SchedulingEngine
from core.services.work_calendar.engine import WorkCalendarEngine

from core.exceptions import BusinessRuleError

@dataclass
class DashboardEVM:
    as_of: date
    baseline_id: str
    BAC: float
    PV: float
    EV: float
    AC: float
    CPI: Optional[float]
    SPI: Optional[float]
    EAC: Optional[float]
    VAC: Optional[float]
    status_text: str
    TCPI_to_BAC: Optional[float]
    TCPI_to_EAC: Optional[float]

@dataclass
class UpcomingTask:
    task_id: str
    name: str
    start_date: date | None
    end_date: date | None
    percent_complete: float
    main_resource: str | None
    is_late: bool
    is_critical: bool


@dataclass
class BurndownPoint:
    day: date
    remaining_tasks: int


@dataclass
class DashboardData:
    kpi: ProjectKPI
    resource_load: List[ResourceLoadRow]
    alerts: List[str]
    upcoming_tasks: List[UpcomingTask]
    burndown: List[BurndownPoint]
    evm: Optional[DashboardEVM] = None


class DashboardService:
    """
    Aggregates data for the Dashboard tab in a modern SaaS-style way.
    """

    def __init__(
        self,
        reporting_service: ReportingService,
        task_service: TaskService,
        project_service: ProjectService,
        scheduling_engine: SchedulingEngine,
        work_calendar_engine: WorkCalendarEngine,
    ):
        self._reporting = reporting_service
        self._tasks = task_service
        self._projects = project_service
        self._sched = scheduling_engine
        self._calendar = work_calendar_engine

    # --------------------------------------------------------------
    # Public API
    # --------------------------------------------------------------

    def get_dashboard_data(self, project_id: str, baseline_id:str | None = None) -> DashboardData:
        # Ensure schedule is up to date
        self._sched.recalculate_project_schedule(project_id)

        kpi = self._reporting.get_project_kpis(project_id)
        resource_load = self._reporting.get_resource_load_summary(project_id)
        alerts = self._build_alerts(project_id, kpi, resource_load)
        upcoming = self._build_upcoming_tasks(project_id)
        burndown = self._build_burndown(project_id)
        
        evm_obj = None
        try:
            evm = self._reporting.get_earned_value(project_id,baseline_id=baseline_id)  # uses latest baseline by default
            
            status = self._interpret_evm(evm)
            evm_obj = DashboardEVM(
                as_of=evm.as_of,
                baseline_id=evm.baseline_id,
                BAC=evm.BAC, PV=evm.PV, EV=evm.EV, AC=evm.AC,
                CPI=evm.CPI, SPI=evm.SPI, EAC=evm.EAC, VAC=evm.VAC, 
                TCPI_to_BAC=getattr(evm,"TCPI_to_BAC",None), TCPI_to_EAC= getattr(evm,"TCPI_to_EAC",None),
                status_text=status,
            )
        except BusinessRuleError:
            # No baseline yet -> no EVM section data.
            evm_obj = None

        data = DashboardData(
            kpi=kpi,
            alerts=alerts,
            resource_load=resource_load,
            burndown=burndown,
            evm=evm_obj,
            upcoming_tasks= upcoming
        )
        return data


    # --------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------

    def _build_alerts(
        self,
        project_id: str,
        kpi: ProjectKPI,
        resource_load: List[ResourceLoadRow],
    ) -> List[str]:
        alerts: List[str] = []
        today = date.today()

        # 1) Overallocated resources
        for r in resource_load:
            if r.total_allocation_percent > 100.0:
                alerts.append(
                    f'Resource "{r.resource_name}" is overloaded '
                    f"({r.total_allocation_percent:.1f}% allocation on {r.tasks_count} tasks)."
                )

        # 2) Late tasks
        if kpi.late_tasks > 0:
            alerts.append(
                f"There are {kpi.late_tasks} late tasks in this project."
            )

        # 3) No start/end dates
        tasks = self._tasks.list_tasks_for_project(project_id)
        missing_dates = [
            t
            for t in tasks
            if (t.duration_days or 0) > 0
            and (t.start_date is None or t.end_date is None)
        ]
        if missing_dates:
            alerts.append(
                f"{len(missing_dates)} task(s) have duration but are missing start or end dates."
            )

        # 4) Project not scheduled or empty
        if not tasks:
            alerts.append("This project has no tasks yet.")
        elif not (kpi.start_date and kpi.end_date):
            alerts.append(
                "Project schedule has incomplete dates. Check task start/end."
            )

        # 5) Project is late vs today
        if kpi.end_date and kpi.end_date < today and kpi.tasks_completed < kpi.tasks_total:
            alerts.append(
                f"Project appears delayed: planned finish was {kpi.end_date.isoformat()}."
            )
            
        # 6) Deadline and priority
        for t in tasks:
            if t.deadline and t.end_date and t.end_date > t.deadline:
                alerts.append(f"Task '{t.name}' missed its deadline.")

            priority = int(getattr(t, "priority", 0) or 0)
            if priority >= 80 and t.deadline and t.end_date and t.end_date > t.deadline:
                alerts.append(f"High-priority task '{t.name}' is late.")

        return alerts

    def _build_upcoming_tasks(self, project_id: str) -> List[UpcomingTask]:
        today = date.today()
        horizon = today + timedelta(days=14)  # next 2 weeks

        tasks = self._tasks.list_tasks_for_project(project_id)
        upcoming: List[UpcomingTask] = []

        for t in tasks:
            if t.start_date is None:
                continue
            if t.start_date < today:
                continue
            if t.start_date > horizon:
                continue
            if str(t.status) in ("TaskStatus.DONE", "DONE"):
                continue
            if str(t.status) in ("TaskStatus.BLOCKED", "BLOCKED"):
                continue

            assigns = self._tasks.list_assignments_for_task(t.id)
            main_res = None
            if assigns:
                # pick highest allocation
                a = max(assigns, key=lambda x: x.allocation_percent or 0.0)
                # you might need a ResourceService to resolve names;
                # for now we assume assignment has a .resource_name or you adapt this
                main_res = getattr(a, "resource_name", None)

            pct = t.percent_complete or 0.0
            is_late = (
                t.end_date is not None
                and t.end_date < today
                and pct < 100.0
            )

            # is_critical: use reporting_service Gantt / CPM info
            is_critical = False
            # You can optionally prefetch CPM info here; for now, keep False or enhance later.

            upcoming.append(
                UpcomingTask(
                    task_id=t.id,
                    name=t.name,
                    start_date=t.start_date,
                    end_date=t.end_date,
                    percent_complete=pct,
                    main_resource=main_res,
                    is_late=is_late,
                    is_critical=is_critical,
                )
            )

        upcoming.sort(key=lambda u: (u.start_date or date.max))
        return upcoming

    def _build_burndown(self, project_id: str) -> List[BurndownPoint]:
        """
        Simple logical burndown: count of remaining (not completed) tasks per day between
        project start and end. For visualization in the dashboard.
        """
        kpi = self._reporting.get_project_kpis(project_id)
        tasks = self._tasks.list_tasks_for_project(project_id)

        if not tasks or not (kpi.start_date and kpi.end_date):
            return []

        start = kpi.start_date
        end = kpi.end_date
        if start > end:
            start, end = end, start

        days: List[BurndownPoint] = []
        current = start
        while current <= end:
            remaining = 0
            for t in tasks:
                pct = t.percent_complete or 0.0
                # consider task "remaining" if not 100% complete and its start_date <= day <= end_date
                if pct < 100.0:
                    if t.start_date and t.end_date:
                        if t.start_date <= current <= t.end_date:
                            remaining += 1
                    else:
                        # tasks without dates but not completed count globally
                        remaining += 1
            days.append(BurndownPoint(day=current, remaining_tasks=remaining))
            current = current + timedelta(days=1)

        return days
    
    def _interpret_evm(self, evm:DashboardEVM) -> str:
        parts = []

        # CPI interpretation
        if evm.CPI is None:
            parts.append("CPI: not available (no actual cost yet).")
        elif evm.CPI >= 1.05:
            parts.append("Cost: under budget (good).")
        elif evm.CPI >= 0.95:
            parts.append("Cost: roughly on budget.")
        else:
            parts.append("Cost: over budget (needs action).")

        # SPI interpretation
        if evm.SPI is None:
            parts.append("SPI: not available.")
        elif evm.SPI >= 1.05:
            parts.append("Schedule: ahead.")
        elif evm.SPI >= 0.95:
            parts.append("Schedule: on track.")
        else:
            parts.append("Schedule: behind (recover plan).")

        # Forecast interpretation
        if evm.EAC is not None and evm.VAC is not None:
            if evm.VAC >= 0:
                parts.append("Forecast: within budget at completion.")
            else:
                parts.append("Forecast: likely over budget at completion.")
        else:
             parts.append("VAC: not available.")
        if evm.TCPI_to_BAC is not None:
            if evm.TCPI_to_BAC < 0.5:
                parts.append("TCPI(BAC): unusually low; verify budget and progress data.")
            elif evm.TCPI_to_BAC <= 1.05:
                parts.append("TCPI(BAC): achievable efficiency to hit budget.")
            elif evm.TCPI_to_BAC <= 1.15:
                parts.append("TCPI(BAC): challenging; requires efficiency improvement.")
            else:
                parts.append("TCPI(BAC): severely over budget or BAC is unrealistic.")
        else:
            parts.append("TCPI(BAC): total planned budget exceeded.")

        return " ".join(parts)
    




