"""Enterprise calendar resolver — resolves full hierarchy for a given scope."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional

from src.core.platform.calendar.contracts import (
    CalendarAssignmentRepository,
    CalendarExceptionRepository,
    CalendarRecurringEventRepository,
    CalendarWorkingRuleRepository,
    PlatformCalendarRepository,
)
from src.core.platform.calendar.application.working_time_calculator import (
    DayCapacity,
    WorkingTimeCalculator,
)
from src.core.platform.calendar.domain.enterprise_calendar import (
    CalendarException,
    CalendarRecurringEvent,
    CalendarWorkingRule,
    PlatformCalendar,
)


@dataclass
class ResolvedCalendarContext:
    date: date
    base_hours: float
    available_hours: float
    assigned_hours: float
    remaining_hours: float
    capacity_percent: float
    utilization_percent: float
    status: str
    source_chain: list[str]
    overrides: list[str]
    timezone: str
    working_start: Optional[time]
    working_end: Optional[time]
    exceptions: list[dict]

    @staticmethod
    def from_day_capacity(
        day: DayCapacity,
        *,
        source_chain: list[str],
        timezone: str,
        exceptions: list[CalendarException],
    ) -> "ResolvedCalendarContext":
        return ResolvedCalendarContext(
            date=day.date,
            base_hours=day.base_hours,
            available_hours=day.available_hours,
            assigned_hours=day.assigned_hours,
            remaining_hours=day.remaining_hours,
            capacity_percent=day.capacity_percent,
            utilization_percent=day.utilization_percent,
            status=day.status,
            source_chain=source_chain,
            overrides=day.active_overrides,
            timezone=timezone,
            working_start=day.effective_start,
            working_end=day.effective_end,
            exceptions=[
                {
                    "id": e.id,
                    "date": str(e.exception_date),
                    "type": e.exception_type,
                    "name": e.name,
                    "impact": e.impact_type,
                }
                for e in exceptions
                if e.exception_date == day.date
            ],
        )


class EnterpriseCalendarResolver:
    """
    Resolves calendar hierarchy for a given org/site/dept/employee/project/resource scope.

    Resolution order (lower level overrides higher level):
        1. GLOBAL (organization)
        2. SITE
        3. DEPARTMENT
        4. EMPLOYEE  — only if worker_type is EMPLOYEE or None
        5. PROJECT
        6. RESOURCE   — only if worker_type is EXTERNAL (no employee_id)

    Working rules: each level's rule for a weekday fully replaces the level above.
    Exceptions + recurring events: collected from ALL levels, highest-priority wins.
    """

    def __init__(
        self,
        organization_id: str,
        calendar_repo: PlatformCalendarRepository,
        rule_repo: CalendarWorkingRuleRepository,
        exception_repo: CalendarExceptionRepository,
        recurring_repo: CalendarRecurringEventRepository,
        assignment_repo: CalendarAssignmentRepository,
        project_assignment_repo,
        resource_assignment_repo,
        calculator: WorkingTimeCalculator,
    ) -> None:
        self._org_id = organization_id
        self._calendar_repo = calendar_repo
        self._rule_repo = rule_repo
        self._exception_repo = exception_repo
        self._recurring_repo = recurring_repo
        self._assignment_repo = assignment_repo
        self._project_assignment_repo = project_assignment_repo
        self._resource_assignment_repo = resource_assignment_repo
        self._calculator = calculator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_calendar_context(
        self,
        *,
        site_id: Optional[str] = None,
        department_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        project_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        worker_type: Optional[str] = None,
        target_date: date,
        assigned_hours: float = 0.0,
    ) -> ResolvedCalendarContext:
        chain = self._build_chain(
            site_id=site_id,
            department_id=department_id,
            employee_id=employee_id,
            project_id=project_id,
            resource_id=resource_id,
            worker_type=worker_type,
            at_date=target_date,
        )

        effective_rule = self._resolve_working_rule(chain, target_date.weekday())
        all_exceptions = self._collect_exceptions(chain, target_date)
        all_recurring = self._collect_recurring(chain)
        timezone = self._resolve_timezone(chain)

        working_rules = [effective_rule] if effective_rule else []
        day = self._calculator.compute_day(
            working_rules=working_rules,
            exceptions=all_exceptions,
            recurring_events=all_recurring,
            target_date=target_date,
            assigned_hours=assigned_hours,
        )

        labels = [label for label, _ in chain]
        return ResolvedCalendarContext.from_day_capacity(
            day,
            source_chain=labels,
            timezone=timezone,
            exceptions=all_exceptions,
        )

    def resolve_range(
        self,
        *,
        site_id: Optional[str] = None,
        department_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        project_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        worker_type: Optional[str] = None,
        start: date,
        end: date,
        assigned_hours_by_date: Optional[dict[date, float]] = None,
    ) -> list[ResolvedCalendarContext]:
        from datetime import timedelta

        results = []
        current = start
        while current <= end:
            ah = (assigned_hours_by_date or {}).get(current, 0.0)
            results.append(
                self.resolve_calendar_context(
                    site_id=site_id,
                    department_id=department_id,
                    employee_id=employee_id,
                    project_id=project_id,
                    resource_id=resource_id,
                    worker_type=worker_type,
                    target_date=current,
                    assigned_hours=ah,
                )
            )
            current += timedelta(days=1)
        return results

    def get_source_chain(
        self,
        *,
        site_id: Optional[str] = None,
        department_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        project_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        worker_type: Optional[str] = None,
        at_date: Optional[date] = None,
    ) -> list[str]:
        chain = self._build_chain(
            site_id=site_id,
            department_id=department_id,
            employee_id=employee_id,
            project_id=project_id,
            resource_id=resource_id,
            worker_type=worker_type,
            at_date=at_date,
        )
        return [label for label, _ in chain]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_chain(
        self,
        *,
        site_id: Optional[str],
        department_id: Optional[str],
        employee_id: Optional[str],
        project_id: Optional[str],
        resource_id: Optional[str],
        worker_type: Optional[str],
        at_date: Optional[date],
    ) -> list[tuple[str, str]]:
        chain: list[tuple[str, str]] = []

        global_cal = self._calendar_repo.get_global(self._org_id)
        if global_cal:
            chain.append(("GLOBAL", global_cal.id))

        if site_id:
            assign = self._assignment_repo.get_site_assignment(site_id, at_date=at_date)
            if assign:
                cal = self._calendar_repo.get(assign.calendar_id)
                if cal and cal.is_active:
                    label = f"SITE-{self._short(cal.code or site_id)}"
                    chain.append((label, cal.id))

        if department_id:
            assign = self._assignment_repo.get_department_assignment(
                department_id, at_date=at_date
            )
            if assign:
                cal = self._calendar_repo.get(assign.calendar_id)
                if cal and cal.is_active:
                    label = f"DEPT-{self._short(cal.code or department_id)}"
                    chain.append((label, cal.id))

        is_employee_backed = worker_type is None or worker_type == "EMPLOYEE"
        if employee_id and is_employee_backed:
            assign = self._assignment_repo.get_employee_assignment(
                employee_id, at_date=at_date
            )
            if assign:
                cal = self._calendar_repo.get(assign.calendar_id)
                if cal and cal.is_active:
                    label = f"EMP-{self._short(cal.code or employee_id)}"
                    chain.append((label, cal.id))

        if project_id:
            assign = self._project_assignment_repo.get(project_id, at_date=at_date)
            if assign:
                cal = self._calendar_repo.get(assign.calendar_id)
                if cal and cal.is_active:
                    label = f"PRJ-{self._short(cal.code or project_id)}"
                    chain.append((label, cal.id))

        is_external = worker_type == "EXTERNAL"
        if resource_id and is_external:
            assign = self._resource_assignment_repo.get(resource_id, at_date=at_date)
            if assign:
                cal = self._calendar_repo.get(assign.calendar_id)
                if cal and cal.is_active:
                    label = f"RESOURCE-{self._short(cal.code or resource_id)}"
                    chain.append((label, cal.id))

        return chain

    def _resolve_working_rule(
        self, chain: list[tuple[str, str]], weekday: int
    ) -> Optional[CalendarWorkingRule]:
        effective: Optional[CalendarWorkingRule] = None
        for _label, cal_id in chain:
            rule = self._rule_repo.get_for_weekday(cal_id, weekday)
            if rule is not None:
                effective = rule
        return effective

    def _collect_exceptions(
        self, chain: list[tuple[str, str]], target_date: date
    ) -> list[CalendarException]:
        all_exceptions: list[CalendarException] = []
        for _label, cal_id in chain:
            excs = self._exception_repo.list_for_date(cal_id, target_date)
            all_exceptions.extend(excs)
        all_exceptions.sort(key=lambda e: e.priority, reverse=True)
        return all_exceptions

    def _collect_recurring(
        self, chain: list[tuple[str, str]]
    ) -> list[CalendarRecurringEvent]:
        all_events: list[CalendarRecurringEvent] = []
        for _label, cal_id in chain:
            events = self._recurring_repo.list_for_calendar(cal_id, active_only=True)
            all_events.extend(events)
        return all_events

    def _resolve_timezone(self, chain: list[tuple[str, str]]) -> str:
        if not chain:
            return "UTC"
        last_cal_id = chain[-1][1]
        cal = self._calendar_repo.get(last_cal_id)
        return cal.timezone if cal else "UTC"

    @staticmethod
    def _short(value: str) -> str:
        return value[:12].upper()


__all__ = ["EnterpriseCalendarResolver", "ResolvedCalendarContext"]
