"""Enterprise calendar resolver — resolves full hierarchy for a given scope."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, time
from time import perf_counter
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

logger = logging.getLogger(__name__)


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
        # In-process caches for data that rarely changes within a request/transaction.
        # Eliminates repeated DB queries when resolve_calendar_context is called
        # many times for the same calendar (e.g. during CPM forward pass).
        self._recurring_cache: dict[str, list] = {}  # cal_id → recurring events
        self._rules_cache: dict[str, list] = {}      # cal_id → working rules

        self._missing_rule_warning_keys: set[tuple[tuple[str, ...], int]] = set()

    def invalidate_cache(self) -> None:
        """Clear the in-process caches. Call after calendar data is mutated."""
        logger.info(
            "Enterprise calendar resolver cache invalidated organization_id=%s rules_cached=%s recurring_cached=%s",
            self._org_id,
            len(self._rules_cache),
            len(self._recurring_cache),
        )
        self._recurring_cache.clear()
        self._rules_cache.clear()
        self._missing_rule_warning_keys.clear()

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
        started = perf_counter()
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
        if chain and effective_rule is None:
            self._warn_missing_rule_once(chain, target_date.weekday(), target_date)
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
        result = ResolvedCalendarContext.from_day_capacity(
            day,
            source_chain=labels,
            timezone=timezone,
            exceptions=all_exceptions,
        )
        duration_ms = (perf_counter() - started) * 1000
        if duration_ms > 50:
            logger.warning(
                "Calendar context resolved slowly organization_id=%s target_date=%s site_id=%s department_id=%s employee_id=%s project_id=%s resource_id=%s worker_type=%s chain=%s exception_count=%s recurring_count=%s duration_ms=%.1f",
                self._org_id,
                target_date,
                site_id or "-",
                department_id or "-",
                employee_id or "-",
                project_id or "-",
                resource_id or "-",
                worker_type or "-",
                labels,
                len(all_exceptions),
                len(all_recurring),
                duration_ms,
            )
        if not chain:
            logger.warning(
                "Calendar context resolved without source chain organization_id=%s target_date=%s project_id=%s resource_id=%s",
                self._org_id,
                target_date,
                project_id or "-",
                resource_id or "-",
            )
        return result

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
        """
        Efficient range resolution: builds the chain once and bulk-fetches all
        calendar data before iterating. DB queries = O(chain_length), not O(days).
        """
        from datetime import timedelta

        if end < start:
            logger.warning(
                "Calendar range resolution skipped because end precedes start organization_id=%s start=%s end=%s project_id=%s resource_id=%s",
                self._org_id,
                start,
                end,
                project_id or "-",
                resource_id or "-",
            )
            return []
        started = perf_counter()
        requested_day_count = (end - start).days + 1
        far_future_year = date.today().year + 20
        if requested_day_count > 5000 or end.year > far_future_year:
            logger.warning(
                "Calendar range is suspicious organization_id=%s start=%s end=%s day_count=%s project_id=%s resource_id=%s",
                self._org_id,
                start,
                end,
                requested_day_count,
                project_id or "-",
                resource_id or "-",
            )

        # 1. Build chain once — assignments are stable across a typical range
        chain = self._build_chain(
            site_id=site_id,
            department_id=department_id,
            employee_id=employee_id,
            project_id=project_id,
            resource_id=resource_id,
            worker_type=worker_type,
            at_date=start,
        )

        if not chain:
            logger.warning(
                "Calendar range resolution using unavailable fallback organization_id=%s start=%s end=%s project_id=%s resource_id=%s",
                self._org_id,
                start,
                end,
                project_id or "-",
                resource_id or "-",
            )
            results = []
            current = start
            while current <= end:
                ah = (assigned_hours_by_date or {}).get(current, 0.0)
                results.append(ResolvedCalendarContext(
                    date=current, base_hours=0.0, available_hours=0.0,
                    assigned_hours=ah, remaining_hours=0.0,
                    capacity_percent=0.0, utilization_percent=0.0,
                    status="UNAVAILABLE", source_chain=[], overrides=[],
                    timezone="UTC", working_start=None, working_end=None,
                    exceptions=[],
                ))
                current += timedelta(days=1)
            logger.debug(
                "Calendar range resolved without source chain organization_id=%s start=%s end=%s day_count=%s duration_ms=%.1f",
                self._org_id,
                start,
                end,
                len(results),
                (perf_counter() - started) * 1000,
            )
            return results

        # 2. Bulk-fetch all data — one pass per calendar in chain, using caches
        all_rules: list = []
        for _label, cal_id in chain:
            if cal_id not in self._rules_cache:
                logger.debug("Calendar rules cache miss calendar_id=%s", cal_id)
                self._rules_cache[cal_id] = self._rule_repo.list_for_calendar(cal_id)
            all_rules.extend(self._rules_cache[cal_id])

        all_exceptions: list = []
        for _label, cal_id in chain:
            all_exceptions.extend(
                self._exception_repo.list_for_calendar(cal_id, start=start, end=end)
            )

        all_recurring: list = []
        for _label, cal_id in chain:
            if cal_id not in self._recurring_cache:
                logger.debug("Calendar recurring cache miss calendar_id=%s", cal_id)
                self._recurring_cache[cal_id] = self._recurring_repo.list_for_calendar(
                    cal_id, active_only=True
                )
            all_recurring.extend(self._recurring_cache[cal_id])

        timezone = self._resolve_timezone(chain)
        labels = [label for label, _ in chain]

        # 3. Iterate days in pure Python — zero DB calls in the loop
        results = []
        current = start
        while current <= end:
            weekday = current.weekday()

            # Resolve working rule: innermost chain level wins
            effective_rule = None
            for _label, cal_id in chain:
                rule = next(
                    (r for r in all_rules if r.calendar_id == cal_id and r.weekday == weekday),
                    None,
                )
                if rule is not None:
                    effective_rule = rule

            day_exceptions = [e for e in all_exceptions if e.exception_date == current]
            day_exceptions.sort(key=lambda e: e.priority, reverse=True)

            working_rules = [effective_rule] if effective_rule else []
            ah = (assigned_hours_by_date or {}).get(current, 0.0)
            day = self._calculator.compute_day(
                working_rules=working_rules,
                exceptions=day_exceptions,
                recurring_events=all_recurring,
                target_date=current,
                assigned_hours=ah,
            )

            results.append(ResolvedCalendarContext.from_day_capacity(
                day,
                source_chain=labels,
                timezone=timezone,
                exceptions=day_exceptions,
            ))
            current += timedelta(days=1)

        duration_ms = (perf_counter() - started) * 1000
        log_method = logger.warning if duration_ms > 250 or len(results) > 5000 else logger.debug
        log_method(
            "Calendar range resolved organization_id=%s start=%s end=%s day_count=%s chain=%s rule_count=%s exception_count=%s recurring_count=%s duration_ms=%.1f",
            self._org_id,
            start,
            end,
            len(results),
            labels,
            len(all_rules),
            len(all_exceptions),
            len(all_recurring),
            duration_ms,
        )
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

        calendar_ids = [calendar_id for _label, calendar_id in chain]
        if len(calendar_ids) != len(set(calendar_ids)):
            logger.warning(
                "Calendar chain contains repeated calendar ids organization_id=%s chain=%s site_id=%s department_id=%s employee_id=%s project_id=%s resource_id=%s",
                self._org_id,
                chain,
                site_id or "-",
                department_id or "-",
                employee_id or "-",
                project_id or "-",
                resource_id or "-",
            )
        return chain

    def _resolve_working_rule(
        self, chain: list[tuple[str, str]], weekday: int
    ) -> Optional[CalendarWorkingRule]:
        effective: Optional[CalendarWorkingRule] = None
        for _label, cal_id in chain:
            # Use cached rules if available — avoids N DB queries per weekday lookup
            if cal_id not in self._rules_cache:
                logger.debug("Calendar rules cache miss calendar_id=%s weekday=%s", cal_id, weekday)
                self._rules_cache[cal_id] = self._rule_repo.list_for_calendar(cal_id)
            rules = self._rules_cache[cal_id]
            rule = next((r for r in rules if r.weekday == weekday), None)
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
            # Use cache — recurring events change rarely; avoids repeated DB queries
            if cal_id not in self._recurring_cache:
                logger.debug("Calendar recurring cache miss calendar_id=%s", cal_id)
                self._recurring_cache[cal_id] = self._recurring_repo.list_for_calendar(
                    cal_id, active_only=True
                )
            all_events.extend(self._recurring_cache[cal_id])
        return all_events

    def _warn_missing_rule_once(
        self,
        chain: list[tuple[str, str]],
        weekday: int,
        target_date: date,
    ) -> None:
        calendar_ids = tuple(calendar_id for _label, calendar_id in chain)
        key = (calendar_ids, weekday)
        if key in self._missing_rule_warning_keys:
            return
        self._missing_rule_warning_keys.add(key)
        logger.warning(
            "Calendar chain has no working rule for weekday; day will be unavailable organization_id=%s target_date=%s weekday=%s chain=%s",
            self._org_id,
            target_date,
            weekday,
            [label for label, _calendar_id in chain],
        )

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
