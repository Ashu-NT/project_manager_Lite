"""Enterprise calendar resolver — resolves full hierarchy for a given scope."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from copy import copy
from dataclasses import dataclass
from datetime import date, time, timedelta
from time import perf_counter
from typing import Any, Generic, TypeVar

from src.core.platform.application.time_management.calendar._input import required_date
from src.core.platform.application.time_management.calendar.capacity.dto.queries.calendar_resolution import (
    ResolveCalendarRangeCommand,
    ResolveContextCommand,
    ResolveEffectiveCalendarCommand,
)
from src.core.platform.application.time_management.calendar.capacity.dto.queries.resource_capacity import (
    ResourceCapacityCommand,
)
from src.core.platform.application.time_management.calendar.capacity.dto.queries.working_days import (
    WorkingDaysCommand,
)
from src.core.platform.application.time_management.calendar.capacity.dto.responses.working_days import (
    WorkingDaysResolution,
)
from src.core.platform.application.time_management.calendar.capacity.working_time_calculator import (
    DayCapacity,
    WorkingTimeCalculator,
    recurring_event_occurs_on,
)
from src.core.platform.contract.port.time_management.calendar.external_assignment_port import (
    ExternalCalendarAssignment,
    ProjectCalendarAssignmentPort,
    ResourceCalendarAssignmentPort,
)
from src.core.platform.contract.repositories.time_management.calendar.contracts import (
    CalendarAssignmentRepository,
    CalendarExceptionRepository,
    CalendarRecurringEventRepository,
    CalendarWorkingRuleRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarException,
    CalendarRecurringEvent,
    CalendarWorkingRule,
    PlatformCalendar,
)
from src.core.shared.time.business_date import business_today

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EffectiveCalendarResolution:
    """Identity result of resolution -- which calendar is actually in
    effect, and the chain of internal source labels that produced it --
    distinct from ResolvedCalendarContext below (a capacity/hours result for
    one date). This is the single source of truth for "effective calendar"
    display (summary cards, Inspector, Detail Overview): never reimplement
    the Site/Department/Employee fallback chain independently in a
    presenter/controller -- call resolve_effective_calendar() instead."""

    calendar_id: str
    calendar_name: str
    timezone: str
    source_chain: list[str]

    @property
    def has_calendar(self) -> bool:
        return bool(self.calendar_id)

    @property
    def source_label(self) -> str:
        """The innermost (winning) chain entry, e.g. "GLOBAL", "SITE-ABC",
        "EMP-XYZ" -- an internal label, never exposed to QML directly (see
        calendar_summary_support.py for the canonical human-readable
        translation)."""
        return self.source_chain[-1] if self.source_chain else ""

    @staticmethod
    def empty() -> EffectiveCalendarResolution:
        return EffectiveCalendarResolution(
            calendar_id="", calendar_name="", timezone="", source_chain=[]
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
    working_start: time | None
    working_end: time | None
    exceptions: list[dict]
    recurring_events: list[dict]

    @staticmethod
    def from_day_capacity(
        day: DayCapacity,
        *,
        source_chain: list[str],
        timezone: str,
        exceptions: list[CalendarException],
        recurring_events: Sequence[CalendarRecurringEvent] = (),
    ) -> ResolvedCalendarContext:
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
            # Recurring events have no single "date" field (they're defined
            # by an RRULE, not a row per occurrence) -- membership on this
            # day is determined the same way WorkingTimeCalculator itself
            # decided whether the event applied, so the Month view can never
            # show an hours delta with no visible cause.
            recurring_events=[
                {
                    "id": e.id,
                    "type": e.event_type,
                    "name": e.title,
                    "impact": e.impact_type,
                }
                for e in sorted(
                    recurring_events, key=lambda e: e.priority, reverse=True
                )
                if recurring_event_occurs_on(e, day.date)
            ],
        )


ProjectAssignmentT = TypeVar("ProjectAssignmentT", bound=ExternalCalendarAssignment)
ResourceAssignmentT = TypeVar("ResourceAssignmentT", bound=ExternalCalendarAssignment)


class PlatformCalendarResolver(Generic[ProjectAssignmentT, ResourceAssignmentT]):
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
        project_assignment_repo: ProjectCalendarAssignmentPort[ProjectAssignmentT],
        resource_assignment_repo: ResourceCalendarAssignmentPort[ResourceAssignmentT],
        calculator: WorkingTimeCalculator,
        shift_pattern_repo: Any = None,
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
        self._shift_pattern_repo = shift_pattern_repo
        # In-process caches for data that rarely changes within a request/transaction.
        # Eliminates repeated DB queries when resolve_calendar_context is called
        # many times for the same calendar (e.g. during CPM forward pass).
        self._recurring_cache: dict[str, list] = {}  # cal_id → recurring events
        self._rules_cache: dict[str, list] = {}  # cal_id → working rules
        self._shift_pattern_cache: dict[
            str, Any
        ] = {}  # shift_code → ShiftPattern | None
        self._shift_pattern_days_cache: dict[
            str, list
        ] = {}  # pattern_id → ShiftPatternDay list

        self._missing_rule_warning_keys: set[tuple[tuple[str, ...], int]] = set()
        self._missing_chain_warning_keys: set[tuple[str | None, ...]] = set()

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
        self._shift_pattern_cache.clear()
        self._shift_pattern_days_cache.clear()
        self._missing_rule_warning_keys.clear()
        self._missing_chain_warning_keys.clear()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_calendar_context(
        self, command: ResolveContextCommand
    ) -> ResolvedCalendarContext:
        site_id = command.site_id or None
        department_id = command.department_id or None
        employee_id = command.employee_id or None
        project_id = command.project_id or None
        resource_id = command.resource_id or None
        worker_type = command.worker_type or None
        target_date = required_date(command.target_date)
        assigned_hours = command.assigned_hours

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
        shift_pattern_day = self._resolve_shift_pattern_day(effective_rule, target_date)
        day = self._calculator.compute_day(
            working_rules=working_rules,
            exceptions=all_exceptions,
            recurring_events=all_recurring,
            target_date=target_date,
            assigned_hours=assigned_hours,
            shift_pattern_day=shift_pattern_day,
        )

        labels = [label for label, _ in chain]
        result = ResolvedCalendarContext.from_day_capacity(
            day,
            source_chain=labels,
            timezone=timezone,
            exceptions=all_exceptions,
            recurring_events=all_recurring,
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
            self._warn_missing_chain_once(
                site_id=site_id,
                department_id=department_id,
                employee_id=employee_id,
                project_id=project_id,
                resource_id=resource_id,
                worker_type=worker_type,
                target_date=target_date,
            )
        return result

    def resolve_range(
        self, command: ResolveCalendarRangeCommand
    ) -> list[ResolvedCalendarContext]:
        site_id = command.site_id or None
        department_id = command.department_id or None
        employee_id = command.employee_id or None
        project_id = command.project_id or None
        resource_id = command.resource_id or None
        worker_type = command.worker_type or None
        start = required_date(command.start_date)
        end = required_date(command.end_date)
        assigned_hours_by_date = command.assigned_hours_by_date

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
        far_future_year = date.today().year + 20  # noqa: DTZ011
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
                results.append(
                    ResolvedCalendarContext(
                        date=current,
                        base_hours=0.0,
                        available_hours=0.0,
                        assigned_hours=ah,
                        remaining_hours=0.0,
                        capacity_percent=0.0,
                        utilization_percent=0.0,
                        status="UNAVAILABLE",
                        source_chain=[],
                        overrides=[],
                        timezone="UTC",
                        working_start=None,
                        working_end=None,
                        exceptions=[],
                        recurring_events=[],
                    )
                )
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

        return self._compute_range_days(command, chain, all_rules, all_exceptions, all_recurring)

    def _compute_range_days(
        self, command: ResolveCalendarRangeCommand, chain: list[tuple[str, str]],
        all_rules: list, all_exceptions: list, all_recurring: list,
        *, calendars: dict[str, PlatformCalendar] | None = None,
    ) -> list[ResolvedCalendarContext]:
        start = required_date(command.start_date)
        end = required_date(command.end_date)
        assigned_hours_by_date = command.assigned_hours_by_date
        started = perf_counter()
        timezone = (
            (calendars[chain[-1][1]].timezone if chain else "UTC")
            if calendars is not None else self._resolve_timezone(chain)
        )
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
                    (
                        r
                        for r in all_rules
                        if r.calendar_id == cal_id and r.weekday == weekday
                    ),
                    None,
                )
                if rule is not None:
                    effective_rule = rule

            day_exceptions = [e for e in all_exceptions if e.exception_date == current]
            day_exceptions.sort(key=lambda e: e.priority, reverse=True)

            working_rules = [effective_rule] if effective_rule else []
            shift_pattern_day = self._resolve_shift_pattern_day(effective_rule, current)
            ah = (assigned_hours_by_date or {}).get(current, 0.0)
            day = self._calculator.compute_day(
                working_rules=working_rules,
                exceptions=day_exceptions,
                recurring_events=all_recurring,
                target_date=current,
                assigned_hours=ah,
                shift_pattern_day=shift_pattern_day,
            )

            results.append(
                ResolvedCalendarContext.from_day_capacity(
                    day,
                    source_chain=labels,
                    timezone=timezone,
                    exceptions=day_exceptions,
                    recurring_events=all_recurring,
                )
            )
            current += timedelta(days=1)

        duration_ms = (perf_counter() - started) * 1000
        log_method = (
            logger.warning if duration_ms > 250 or len(results) > 5000 else logger.debug
        )
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

    def resolve_resource_ranges(
        self, commands: list[ResolveCalendarRangeCommand]
    ) -> list[list[ResolvedCalendarContext]]:
        """Batch PM resource/employee ranges; all row calculation is query-free.

        Like resolve_range, effective assignments are selected at each range's
        start date. Site/department scopes are deliberately not part of this API.
        """
        if not commands:
            return []
        if any(command.site_id or command.department_id for command in commands):
            raise ValueError("Resource range batches do not accept site/department scopes")
        global_calendar = self._calendar_repo.get_global(self._org_id)
        employees = self._assignment_repo.list_for_employees(sorted({
            command.employee_id for command in commands
            if command.employee_id and command.worker_type in (None, "EMPLOYEE")
        }))
        projects = self._project_assignment_repo.list_for_projects(sorted({
            command.project_id for command in commands if command.project_id
        }))
        resources = self._resource_assignment_repo.list_for_resources(sorted({
            command.resource_id for command in commands
            if command.resource_id and command.worker_type == "EXTERNAL"
        }))
        requested_calendar_ids = (
            {row.calendar_id for row in employees}
            | {row.calendar_id for row in projects}
            | {row.calendar_id for row in resources}
        )
        if global_calendar is not None:
            requested_calendar_ids.add(global_calendar.id)
        calendars = {cal.id: cal for cal in self._calendar_repo.list_by_ids(sorted(requested_calendar_ids))}

        def index_assignments(rows: Sequence[Any], key: str) -> dict[str, list[Any]]:
            indexed: dict[str, list[Any]] = {}
            for row in rows:
                indexed.setdefault(getattr(row, key), []).append(row)
            return indexed

        employees_by_id = index_assignments(employees, "employee_id")
        projects_by_id = index_assignments(projects, "project_id")
        resources_by_id = index_assignments(resources, "resource_id")

        def effective(rows: Sequence[Any], at_date: date) -> Any:
            return next((row for row in rows
                         if (row.effective_from is None or row.effective_from <= at_date)
                         and (row.effective_to is None or row.effective_to >= at_date)), None)

        chains = []
        for command in commands:
            at_date = required_date(command.start_date)
            employee = (
                effective(employees_by_id.get(command.employee_id or "", []), at_date)
                if command.worker_type in (None, "EMPLOYEE") else None
            )
            project = effective(projects_by_id.get(command.project_id or "", []), at_date)
            resource = (
                effective(resources_by_id.get(command.resource_id or "", []), at_date)
                if command.worker_type == "EXTERNAL" else None
            )
            chains.append(self._assemble_chain(global_calendar, calendars, [
                ("EMP", command.employee_id, employee),
                ("PRJ", command.project_id, project),
                ("RESOURCE", command.resource_id, resource),
            ]))
        calendar_ids = sorted({cal_id for chain in chains for _, cal_id in chain})
        start = min(required_date(command.start_date) for command in commands)
        end = max(required_date(command.end_date) for command in commands)
        rules = self._rule_repo.list_for_calendars(calendar_ids)
        exceptions = self._exception_repo.list_for_calendars(calendar_ids, start=start, end=end)
        recurring = self._recurring_repo.list_for_calendars(calendar_ids)

        rules_by_calendar = index_assignments(rules, "calendar_id")
        exceptions_by_calendar = index_assignments(exceptions, "calendar_id")
        recurring_by_calendar = index_assignments(recurring, "calendar_id")
        # Request-local shift facts: no database fallback (including unknown codes).
        calculator = copy(self)
        shift_codes = {rule.shift_code for rule in rules if rule.shift_code}
        calculator._shift_pattern_cache = dict.fromkeys(shift_codes)
        calculator._shift_pattern_days_cache = {}
        if shift_codes and self._shift_pattern_repo is not None:
            patterns = self._shift_pattern_repo.list_for_organization(self._org_id)
            selected = [pattern for pattern in patterns if pattern.code in shift_codes]
            calculator._shift_pattern_cache.update({pattern.code: pattern for pattern in selected})
            calculator._shift_pattern_days_cache = {pattern.id: [] for pattern in selected}
            for day in self._shift_pattern_repo.list_days_for_patterns([pattern.id for pattern in selected]):
                calculator._shift_pattern_days_cache[day.shift_pattern_id].append(day)
        results = []
        for command, chain in zip(commands, chains, strict=True):
            ids = [cal_id for _, cal_id in chain]
            # Preserve repeated calendar ids and chain ordering from resolve_range.
            chain_rules = [rule for cal_id in ids for rule in rules_by_calendar.get(cal_id, [])]
            chain_exceptions = [row for cal_id in ids for row in exceptions_by_calendar.get(cal_id, [])]
            chain_recurring = [row for cal_id in ids for row in recurring_by_calendar.get(cal_id, [])]
            results.append(calculator._compute_range_days(
                command, chain, chain_rules, chain_exceptions, chain_recurring, calendars=calendars
            ))
        return results

    def calculate_working_days(
        self, command: WorkingDaysCommand
    ) -> WorkingDaysResolution:
        def _is_available(target_date: date) -> bool:
            ctx = self.resolve_calendar_context(
                ResolveContextCommand(
                    project_id=command.project_id,
                    resource_id=command.resource_id,
                    target_date=target_date,
                )
            )
            return ctx.available_hours > 0

        def _calculate():
            start = required_date(command.start_date)
            working_days = max(command.working_days, 0)
            if working_days == 0:
                return WorkingDaysResolution(
                    start_date=start,
                    end_date=start,
                    working_days=0,
                )

            # Bounded like ProjectCalendarAdapter.add_working_days: small moves
            # fail fast, large moves are capped so bad data can't scan forever.
            max_iterations = min(max(working_days * 7, 730), 365 * 40)
            iterations = 0

            current = start
            while not _is_available(current) and iterations < max_iterations:
                current += timedelta(days=1)
                iterations += 1

            remaining = working_days - 1
            while remaining > 0 and iterations < max_iterations:
                current += timedelta(days=1)
                iterations += 1
                if _is_available(current):
                    remaining -= 1

            return WorkingDaysResolution(
                start_date=start,
                end_date=current,
                working_days=working_days,
            )

        return _calculate()

    def calculate_resource_capacity(
        self, command: ResourceCapacityCommand, *, calculator
    ):
        resource_id = command.resource_id
        start = required_date(command.start_date)
        end = required_date(command.end_date)
        project_id = command.project_id or None
        return calculator.compute(resource_id, start, end, project_id=project_id)

    def get_source_chain(
        self,
        *,
        site_id: str | None = None,
        department_id: str | None = None,
        employee_id: str | None = None,
        project_id: str | None = None,
        resource_id: str | None = None,
        worker_type: str | None = None,
        at_date: date | None = None,
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

    def resolve_effective_calendar(
        self, command: ResolveEffectiveCalendarCommand
    ) -> EffectiveCalendarResolution:
        site_id = command.site_id or None
        department_id = command.department_id or None
        employee_id = command.employee_id or None
        project_id = command.project_id or None
        resource_id = command.resource_id or None
        worker_type = command.worker_type or None
        at_date = required_date(command.at_date) if command.at_date else None

        """The single source of truth for "which calendar is actually in
        effect" -- the exact same chain-building `resolve_calendar_context`/
        `get_source_chain` already use (same at_date-aware assignment
        resolution, same priority/is_default tie-breaking), just returning
        calendar identity instead of a capacity/hours result. Presenters
        must call this rather than independently reimplementing the Site/
        Department/Employee fallback."""
        chain = self._build_chain(
            site_id=site_id,
            department_id=department_id,
            employee_id=employee_id,
            project_id=project_id,
            resource_id=resource_id,
            worker_type=worker_type,
            at_date=at_date,
        )
        if not chain:
            return EffectiveCalendarResolution.empty()
        _winning_label, calendar_id = chain[-1]
        calendar = self._calendar_repo.get(calendar_id)
        return EffectiveCalendarResolution(
            calendar_id=calendar_id,
            calendar_name=calendar.name if calendar else "",
            timezone=calendar.timezone if calendar else "",
            source_chain=[label for label, _ in chain],
        )

    def business_today(self) -> date:
        """ "Today" in this organization's own configured business timezone
        (its default calendar's timezone), not the server's local time.
        Date-sensitive calendar resolution (which assignment/calendar is
        "currently" effective) must use this instead of `date.today()` --
        see src.core.shared.time.business_date for the underlying, generic
        conversion every such caller shares."""
        calendar = self._calendar_repo.get_global(self._org_id)
        timezone_name = calendar.timezone if calendar else None
        return business_today(timezone_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_chain(
        self,
        *,
        site_id: str | None,
        department_id: str | None,
        employee_id: str | None,
        project_id: str | None,
        resource_id: str | None,
        worker_type: str | None,
        at_date: date | None,
    ) -> list[tuple[str, str]]:
        global_cal = self._calendar_repo.get_global(self._org_id)
        assignments: list[tuple[str, str, Any]] = []
        if site_id:
            assignments.append(("SITE", site_id, self._assignment_repo.get_site_assignment(
                site_id, at_date=at_date)))
        if department_id:
            assignments.append(("DEPT", department_id, self._assignment_repo.get_department_assignment(
                department_id, at_date=at_date)))
        is_employee_backed = worker_type is None or worker_type == "EMPLOYEE"
        if employee_id and is_employee_backed:
            assignments.append(("EMP", employee_id, self._assignment_repo.get_employee_assignment(
                employee_id, at_date=at_date)))
        if project_id:
            assignments.append(("PRJ", project_id, self._project_assignment_repo.get(
                project_id, at_date=at_date)))
        is_external = worker_type == "EXTERNAL"
        if resource_id and is_external:
            assignments.append(("RESOURCE", resource_id, self._resource_assignment_repo.get(
                resource_id, at_date=at_date)))
        calendars = {
            cal.id: cal for cal in self._calendar_repo.list_by_ids(
                [row.calendar_id for _, _, row in assignments if row is not None])
        } if any(row is not None for _, _, row in assignments) else {}
        chain = self._assemble_chain(global_cal, calendars, assignments)
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

    def _assemble_chain(self, global_calendar, calendars, assignments) -> list[tuple[str, str]]:
        chain = [("GLOBAL", global_calendar.id)] if global_calendar else []
        for prefix, owner_id, assignment in assignments:
            if assignment is None:
                continue
            calendar = calendars.get(assignment.calendar_id)
            if calendar is not None and calendar.is_active:
                chain.append((f"{prefix}-{self._short(calendar.code or owner_id)}", calendar.id))
        return chain

    def _resolve_working_rule(
        self, chain: list[tuple[str, str]], weekday: int
    ) -> CalendarWorkingRule | None:
        effective: CalendarWorkingRule | None = None
        for _label, cal_id in chain:
            # Use cached rules if available — avoids N DB queries per weekday lookup
            if cal_id not in self._rules_cache:
                logger.debug(
                    "Calendar rules cache miss calendar_id=%s weekday=%s",
                    cal_id,
                    weekday,
                )
                self._rules_cache[cal_id] = self._rule_repo.list_for_calendar(cal_id)
            rules = self._rules_cache[cal_id]
            rule = next((r for r in rules if r.weekday == weekday), None)
            if rule is not None:
                effective = rule
        return effective

    def _get_cached_shift_pattern(self, shift_code: str):
        if shift_code not in self._shift_pattern_cache:
            self._shift_pattern_cache[shift_code] = (
                self._shift_pattern_repo.get_by_code(self._org_id, shift_code)
            )
        return self._shift_pattern_cache[shift_code]

    def _get_cached_shift_pattern_days(self, pattern_id: str) -> list:
        if pattern_id not in self._shift_pattern_days_cache:
            self._shift_pattern_days_cache[pattern_id] = (
                self._shift_pattern_repo.list_days(pattern_id)
            )
        return self._shift_pattern_days_cache[pattern_id]

    def _resolve_shift_pattern_day(
        self, rule: CalendarWorkingRule | None, target_date: date
    ):
        if rule is None or not rule.shift_code or self._shift_pattern_repo is None:
            return None
        pattern = self._get_cached_shift_pattern(rule.shift_code)
        if (
            pattern is None
            or pattern.rotation_cycle_days is None
            or pattern.anchor_date is None
        ):
            return None
        day_offset = (
            target_date - pattern.anchor_date
        ).days % pattern.rotation_cycle_days
        days = self._get_cached_shift_pattern_days(pattern.id)
        return next((d for d in days if d.day_offset == day_offset), None)

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

    def _warn_missing_chain_once(
        self,
        *,
        site_id: str | None,
        department_id: str | None,
        employee_id: str | None,
        project_id: str | None,
        resource_id: str | None,
        worker_type: str | None,
        target_date: date,
    ) -> None:
        # A missing chain is a property of the SCOPE (this project/resource/
        # site/... has no calendar assignment anywhere in its hierarchy), not
        # of any one date -- a caller walking many dates for the same scope
        # (e.g. add_working_days searching backward/forward) would otherwise
        # log this once per day, flooding the log for what is a single
        # configuration gap.
        key = (
            site_id,
            department_id,
            employee_id,
            project_id,
            resource_id,
            worker_type,
        )
        if key in self._missing_chain_warning_keys:
            return
        self._missing_chain_warning_keys.add(key)
        logger.warning(
            "Calendar context resolved without source chain organization_id=%s target_date=%s project_id=%s resource_id=%s",
            self._org_id,
            target_date,
            project_id or "-",
            resource_id or "-",
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


__all__ = [
    "EffectiveCalendarResolution",
    "PlatformCalendarResolver",
    "ResolvedCalendarContext",
]
