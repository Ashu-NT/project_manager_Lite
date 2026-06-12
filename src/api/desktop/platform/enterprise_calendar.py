"""Desktop API for the enterprise calendar engine."""

from __future__ import annotations

from datetime import date, time
from src.api.desktop.platform._support import execute_desktop_operation
from src.api.desktop.platform.models import DesktopApiResult
from src.api.desktop.platform.models.enterprise_calendar import (
    CalendarAssignmentDto,
    CalendarCreateCommand,
    CalendarDto,
    CalendarExceptionDto,
    CalendarUpdateCommand,
    DeptCalendarAssignCommand,
    EmpCalendarAssignCommand,
    ExceptionCreateCommand,
    ExceptionUpdateCommand,
    ProjectCalendarAssignCommand,
    RecurringEventCreateCommand,
    RecurringEventDto,
    RecurringEventUpdateCommand,
    ResolveContextCommand,
    ResolvedContextDto,
    ResourceCalendarAssignCommand,
    ResourceCapacityCommand,
    ResourceCapacityDto,
    ShiftPatternCreateCommand,
    ShiftPatternDayDto,
    ShiftPatternDto,
    ShiftPatternUpdateCommand,
    SiteCalendarAssignCommand,
    WorkingDaysCommand,
    WorkingDaysResultDto,
    WorkingRuleDto,
    WorkingRuleSaveCommand,
)
from src.core.platform.calendar.application.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.calendar.application.calendar_exception_service import (
    CalendarExceptionService,
)
from src.core.platform.calendar.application.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
)
from src.core.platform.calendar.application.enterprise_calendar_service import (
    EnterpriseCalendarService,
)
from src.core.platform.calendar.application.recurring_event_service import (
    RecurringEventService,
)
from src.core.platform.calendar.application.shift_pattern_service import ShiftPatternService
from src.core.platform.calendar.application.working_rule_service import WorkingRuleService
from src.core.platform.calendar.domain.enterprise_calendar import (
    CalendarException,
    CalendarRecurringEvent,
    CalendarWorkingRule,
    PlatformCalendar,
    ShiftPattern,
    ShiftPatternDay,
)


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_time(value: str) -> time | None:
    if not value:
        return None
    try:
        parts = value.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return time(hour, minute)
    except (ValueError, IndexError):
        return None


def _fmt_date(d) -> str:
    return str(d) if d else ""


def _fmt_time(t) -> str:
    return t.strftime("%H:%M") if t else ""


def _serialize_calendar(cal: PlatformCalendar) -> CalendarDto:
    return CalendarDto(
        id=cal.id,
        organization_id=cal.organization_id,
        code=cal.code,
        name=cal.name,
        calendar_type=cal.calendar_type,
        timezone=cal.timezone,
        is_default=cal.is_default,
        is_active=cal.is_active,
        description=cal.description or "",
        base_calendar_id=cal.base_calendar_id or "",
        scope_type=cal.scope_type or "",
        scope_id=cal.scope_id or "",
        locale=cal.locale or "",
        effective_from=_fmt_date(cal.effective_from),
        effective_to=_fmt_date(cal.effective_to),
        priority=cal.priority,
        version=cal.version,
    )


def _serialize_rule(rule: CalendarWorkingRule) -> WorkingRuleDto:
    return WorkingRuleDto(
        id=rule.id,
        calendar_id=rule.calendar_id,
        weekday=rule.weekday,
        is_working_day=rule.is_working_day,
        start_time=_fmt_time(rule.start_time),
        end_time=_fmt_time(rule.end_time),
        break_start_time=_fmt_time(rule.break_start_time),
        break_end_time=_fmt_time(rule.break_end_time),
        break_minutes=rule.break_minutes,
        hours_override=rule.hours_override or 0.0,
        shift_code=rule.shift_code or "",
        computed_hours=rule.compute_hours(),
    )


def _serialize_exception(exc: CalendarException) -> CalendarExceptionDto:
    return CalendarExceptionDto(
        id=exc.id,
        calendar_id=exc.calendar_id,
        exception_date=_fmt_date(exc.exception_date),
        exception_type=exc.exception_type,
        name=exc.name,
        impact_type=exc.impact_type,
        approval_status=exc.approval_status,
        scope_type=exc.scope_type or "",
        scope_id=exc.scope_id or "",
        description=exc.description or "",
        start_time=_fmt_time(exc.start_time),
        end_time=_fmt_time(exc.end_time),
        hours_override=exc.hours_override or 0.0,
        priority=exc.priority,
        approved_by=exc.approved_by or "",
    )


def _serialize_recurring_event(event: CalendarRecurringEvent) -> RecurringEventDto:
    return RecurringEventDto(
        id=event.id,
        calendar_id=event.calendar_id,
        title=event.title,
        event_type=event.event_type,
        recurrence_rule=event.recurrence_rule,
        start_time=_fmt_time(event.start_time),
        end_time=_fmt_time(event.end_time),
        impact_type=event.impact_type,
        effective_from=_fmt_date(event.effective_from),
        is_active=event.is_active,
        scope_type=event.scope_type or "",
        scope_id=event.scope_id or "",
        capacity_impact_percent=event.capacity_impact_percent or 0.0,
        effective_to=_fmt_date(event.effective_to),
        priority=event.priority,
    )


def _serialize_shift_pattern(p: ShiftPattern) -> ShiftPatternDto:
    return ShiftPatternDto(
        id=p.id,
        organization_id=p.organization_id,
        code=p.code,
        name=p.name,
        pattern_type=p.pattern_type,
        timezone=p.timezone,
        is_active=p.is_active,
        description=p.description or "",
        rotation_cycle_days=p.rotation_cycle_days or 0,
    )


def _serialize_shift_day(d: ShiftPatternDay) -> ShiftPatternDayDto:
    return ShiftPatternDayDto(
        id=d.id,
        shift_pattern_id=d.shift_pattern_id,
        day_offset=d.day_offset,
        is_working_day=d.is_working_day,
        start_time=_fmt_time(d.start_time),
        end_time=_fmt_time(d.end_time),
        break_minutes=d.break_minutes,
        hours=d.hours or 0.0,
        shift_label=d.shift_label or "",
    )


class EnterpriseCalendarDesktopApi:
    """Desktop-facing API for the enterprise calendar engine."""

    def __init__(
        self,
        *,
        calendar_service: EnterpriseCalendarService,
        rule_service: WorkingRuleService,
        exception_service: CalendarExceptionService,
        recurring_event_service: RecurringEventService,
        shift_pattern_service: ShiftPatternService,
        assignment_service: CalendarAssignmentService,
        resolver: EnterpriseCalendarResolver,
        capacity_calculator=None,
    ) -> None:
        self._calendar_service = calendar_service
        self._rule_service = rule_service
        self._exception_service = exception_service
        self._recurring_event_service = recurring_event_service
        self._shift_pattern_service = shift_pattern_service
        self._assignment_service = assignment_service
        self._resolver = resolver
        self._capacity_calculator = capacity_calculator

    # --- Calendars ---

    def list_calendars(
        self, *, calendar_type: str = "", active_only: bool | None = None
    ) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: tuple(
                _serialize_calendar(c)
                for c in self._calendar_service.list_calendars(
                    calendar_type=calendar_type or None,
                    active_only=active_only,
                )
            )
        )

    def get_calendar(self, calendar_id: str) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: _serialize_calendar(self._calendar_service.get_calendar(calendar_id))
        )

    def create_calendar(self, command: CalendarCreateCommand) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: _serialize_calendar(
                self._calendar_service.create_calendar(
                    code=command.code,
                    name=command.name,
                    calendar_type=command.calendar_type,
                    timezone=command.timezone or "UTC",
                    description=command.description or None,
                    base_calendar_id=command.base_calendar_id or None,
                    scope_type=command.scope_type or None,
                    scope_id=command.scope_id or None,
                    locale=command.locale or None,
                    is_default=command.is_default,
                    effective_from=_parse_date(command.effective_from),
                    effective_to=_parse_date(command.effective_to),
                    priority=command.priority,
                )
            )
        )

    def update_calendar(self, command: CalendarUpdateCommand) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: _serialize_calendar(
                self._calendar_service.update_calendar(
                    command.calendar_id,
                    name=command.name or None,
                    description=command.description or None,
                    timezone=command.timezone or None,
                    locale=command.locale or None,
                    is_default=command.is_default,
                    is_active=command.is_active,
                    effective_from=_parse_date(command.effective_from),
                    effective_to=_parse_date(command.effective_to),
                    priority=command.priority,
                )
            )
        )

    def delete_calendar(self, calendar_id: str) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: self._calendar_service.delete_calendar(calendar_id) or None
        )

    # --- Working Rules ---

    def list_working_rules(self, calendar_id: str) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: tuple(
                _serialize_rule(r)
                for r in self._rule_service.list_rules(calendar_id)
            )
        )

    def save_working_rule(self, command: WorkingRuleSaveCommand) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: _serialize_rule(
                self._rule_service.save_rule(
                    command.calendar_id,
                    command.weekday,
                    is_working_day=command.is_working_day,
                    start_time=_parse_time(command.start_time),
                    end_time=_parse_time(command.end_time),
                    break_start_time=_parse_time(command.break_start_time),
                    break_end_time=_parse_time(command.break_end_time),
                    break_minutes=command.break_minutes,
                    hours_override=command.hours_override if command.hours_override else None,
                    shift_code=command.shift_code or None,
                )
            )
        )

    def delete_working_rule(self, rule_id: str) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: self._rule_service.delete_rule(rule_id) or None
        )

    # --- Exceptions ---

    def list_exceptions(
        self, calendar_id: str, *, start: str = "", end: str = ""
    ) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: tuple(
                _serialize_exception(e)
                for e in self._exception_service.list_exceptions(
                    calendar_id,
                    start=_parse_date(start),
                    end=_parse_date(end),
                )
            )
        )

    def add_exception(self, command: ExceptionCreateCommand) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: _serialize_exception(
                self._exception_service.add_exception(
                    command.calendar_id,
                    exception_date=date.fromisoformat(command.exception_date),
                    exception_type=command.exception_type,
                    name=command.name,
                    impact_type=command.impact_type,
                    scope_type=command.scope_type or None,
                    scope_id=command.scope_id or None,
                    description=command.description or None,
                    start_time=_parse_time(command.start_time),
                    end_time=_parse_time(command.end_time),
                    hours_override=command.hours_override if command.hours_override else None,
                    priority=command.priority,
                    approval_status=command.approval_status or "APPROVED",
                )
            )
        )

    def update_exception(self, command: ExceptionUpdateCommand) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: _serialize_exception(
                self._exception_service.update_exception(
                    command.exception_id,
                    name=command.name or None,
                    description=command.description or None,
                    exception_type=command.exception_type or None,
                    impact_type=command.impact_type or None,
                    hours_override=command.hours_override if command.hours_override else None,
                    priority=command.priority,
                    approval_status=command.approval_status or None,
                    approved_by=command.approved_by or None,
                )
            )
        )

    def delete_exception(self, exception_id: str) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: self._exception_service.delete_exception(exception_id) or None
        )

    # --- Recurring Events ---

    def list_recurring_events(
        self, calendar_id: str, *, active_only: bool = True
    ) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: tuple(
                _serialize_recurring_event(e)
                for e in self._recurring_event_service.list_recurring_events(
                    calendar_id, active_only=active_only
                )
            )
        )

    def add_recurring_event(self, command: RecurringEventCreateCommand) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: _serialize_recurring_event(
                self._recurring_event_service.add_recurring_event(
                    command.calendar_id,
                    title=command.title,
                    event_type=command.event_type,
                    recurrence_rule=command.recurrence_rule,
                    start_time=_parse_time(command.start_time),
                    end_time=_parse_time(command.end_time),
                    impact_type=command.impact_type,
                    effective_from=date.fromisoformat(command.effective_from),
                    scope_type=command.scope_type or None,
                    scope_id=command.scope_id or None,
                    capacity_impact_percent=command.capacity_impact_percent or None,
                    effective_to=_parse_date(command.effective_to),
                    priority=command.priority,
                )
            )
        )

    def update_recurring_event(
        self, command: RecurringEventUpdateCommand
    ) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: _serialize_recurring_event(
                self._recurring_event_service.update_recurring_event(
                    command.event_id,
                    title=command.title or None,
                    event_type=command.event_type or None,
                    recurrence_rule=command.recurrence_rule or None,
                    start_time=_parse_time(command.start_time),
                    end_time=_parse_time(command.end_time),
                    impact_type=command.impact_type or None,
                    capacity_impact_percent=command.capacity_impact_percent or None,
                    effective_from=_parse_date(command.effective_from),
                    effective_to=_parse_date(command.effective_to),
                    is_active=command.is_active,
                    priority=command.priority,
                )
            )
        )

    def delete_recurring_event(self, event_id: str) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: self._recurring_event_service.delete_recurring_event(event_id) or None
        )

    # --- Shift Patterns ---

    def list_shift_patterns(self, *, active_only: bool | None = None) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: tuple(
                _serialize_shift_pattern(p)
                for p in self._shift_pattern_service.list_shift_patterns(
                    active_only=active_only
                )
            )
        )

    def get_shift_pattern(self, pattern_id: str) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: _serialize_shift_pattern(
                self._shift_pattern_service.get_shift_pattern(pattern_id)
            )
        )

    def list_shift_pattern_days(self, pattern_id: str) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: tuple(
                _serialize_shift_day(d)
                for d in self._shift_pattern_service.list_days(pattern_id)
            )
        )

    def create_shift_pattern(self, command: ShiftPatternCreateCommand) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: _serialize_shift_pattern(
                self._shift_pattern_service.create_shift_pattern(
                    code=command.code,
                    name=command.name,
                    pattern_type=command.pattern_type,
                    timezone=command.timezone or "UTC",
                    description=command.description or None,
                    rotation_cycle_days=command.rotation_cycle_days or None,
                )
            )
        )

    def update_shift_pattern(self, command: ShiftPatternUpdateCommand) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: _serialize_shift_pattern(
                self._shift_pattern_service.update_shift_pattern(
                    command.pattern_id,
                    name=command.name or None,
                    description=command.description or None,
                    pattern_type=command.pattern_type or None,
                    timezone=command.timezone or None,
                    rotation_cycle_days=command.rotation_cycle_days or None,
                    is_active=command.is_active,
                )
            )
        )

    def delete_shift_pattern(self, pattern_id: str) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: self._shift_pattern_service.delete_shift_pattern(pattern_id) or None
        )

    # --- Assignments ---

    def assign_site_calendar(self, command: SiteCalendarAssignCommand) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: self._serialize_assignment(
                self._assignment_service.assign_site_calendar(
                    command.site_id,
                    command.calendar_id,
                    effective_from=_parse_date(command.effective_from),
                    effective_to=_parse_date(command.effective_to),
                    is_default=command.is_default,
                    priority=command.priority,
                ),
                entity_type="site",
            )
        )

    def assign_department_calendar(
        self, command: DeptCalendarAssignCommand
    ) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: self._serialize_assignment(
                self._assignment_service.assign_department_calendar(
                    command.department_id,
                    command.calendar_id,
                    effective_from=_parse_date(command.effective_from),
                    effective_to=_parse_date(command.effective_to),
                    is_default=command.is_default,
                    priority=command.priority,
                ),
                entity_type="department",
            )
        )

    def assign_employee_calendar(
        self, command: EmpCalendarAssignCommand
    ) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: self._serialize_assignment(
                self._assignment_service.assign_employee_calendar(
                    command.employee_id,
                    command.calendar_id,
                    effective_from=_parse_date(command.effective_from),
                    effective_to=_parse_date(command.effective_to),
                    is_default=command.is_default,
                    priority=command.priority,
                ),
                entity_type="employee",
            )
        )

    def assign_project_calendar(
        self, command: ProjectCalendarAssignCommand
    ) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: self._serialize_assignment(
                self._assignment_service.assign_project_calendar(
                    command.project_id,
                    command.calendar_id,
                    effective_from=_parse_date(command.effective_from),
                    effective_to=_parse_date(command.effective_to),
                    is_default=command.is_default,
                    priority=command.priority,
                ),
                entity_type="project",
            )
        )

    def assign_resource_calendar(
        self, command: ResourceCalendarAssignCommand
    ) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: self._serialize_assignment(
                self._assignment_service.assign_resource_calendar(
                    command.resource_id,
                    command.calendar_id,
                    effective_from=_parse_date(command.effective_from),
                    effective_to=_parse_date(command.effective_to),
                    is_default=command.is_default,
                    priority=command.priority,
                ),
                entity_type="resource",
            )
        )

    def list_site_calendar_assignments(self, site_id: str) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_assignment(assignment, entity_type="site")
                for assignment in self._assignment_service.list_site_assignments(site_id)
            )
        )

    def list_department_calendar_assignments(
        self, department_id: str
    ) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_assignment(assignment, entity_type="department")
                for assignment in self._assignment_service.list_department_assignments(
                    department_id
                )
            )
        )

    def list_employee_calendar_assignments(self, employee_id: str) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_assignment(assignment, entity_type="employee")
                for assignment in self._assignment_service.list_employee_assignments(
                    employee_id
                )
            )
        )

    def remove_assignment(self, assignment_id: str, assignment_type: str) -> DesktopApiResult:
        def _remove():
            t = assignment_type.lower()
            if t == "site":
                self._assignment_service.remove_site_assignment(assignment_id)
            elif t == "department":
                self._assignment_service.remove_department_assignment(assignment_id)
            elif t == "employee":
                self._assignment_service.remove_employee_assignment(assignment_id)
            elif t == "project":
                self._assignment_service.remove_project_assignment(assignment_id)
            elif t == "resource":
                self._assignment_service.remove_resource_assignment(assignment_id)

        return execute_desktop_operation(_remove)

    def list_calendar_assignments(self, calendar_id: str) -> DesktopApiResult:
        def _list_assignments():
            assignments = self._assignment_service.list_calendar_assignments(calendar_id)
            return {
                "sites": tuple(
                    self._serialize_assignment(assignment, entity_type="site")
                    for assignment in assignments.get("sites", ())
                ),
                "departments": tuple(
                    self._serialize_assignment(assignment, entity_type="department")
                    for assignment in assignments.get("departments", ())
                ),
                "employees": tuple(
                    self._serialize_assignment(assignment, entity_type="employee")
                    for assignment in assignments.get("employees", ())
                ),
                "projects": tuple(
                    self._serialize_assignment(assignment, entity_type="project")
                    for assignment in assignments.get("projects", ())
                ),
                "resources": tuple(
                    self._serialize_assignment(assignment, entity_type="resource")
                    for assignment in assignments.get("resources", ())
                ),
            }

        return execute_desktop_operation(
            _list_assignments
        )

    # --- Resolution ---

    def resolve_calendar_context(
        self, command: ResolveContextCommand
    ) -> DesktopApiResult:
        def _resolve():
            ctx = self._resolver.resolve_calendar_context(
                site_id=command.site_id or None,
                department_id=command.department_id or None,
                employee_id=command.employee_id or None,
                project_id=command.project_id or None,
                resource_id=command.resource_id or None,
                worker_type=command.worker_type or None,
                target_date=date.fromisoformat(command.target_date),
                assigned_hours=command.assigned_hours,
            )
            return ResolvedContextDto(
                date=str(ctx.date),
                base_hours=ctx.base_hours,
                available_hours=ctx.available_hours,
                assigned_hours=ctx.assigned_hours,
                remaining_hours=ctx.remaining_hours,
                capacity_percent=ctx.capacity_percent,
                utilization_percent=ctx.utilization_percent,
                status=ctx.status,
                source_chain=list(ctx.source_chain),
                overrides=list(ctx.overrides),
                timezone=ctx.timezone,
                exceptions=ctx.exceptions,
                working_start=_fmt_time(ctx.working_start),
                working_end=_fmt_time(ctx.working_end),
            )

        return execute_desktop_operation(_resolve)

    def get_source_chain(
        self,
        *,
        site_id: str = "",
        department_id: str = "",
        employee_id: str = "",
        project_id: str = "",
        resource_id: str = "",
        worker_type: str = "",
    ) -> DesktopApiResult:
        return execute_desktop_operation(
            lambda: tuple(
                self._resolver.get_source_chain(
                    site_id=site_id or None,
                    department_id=department_id or None,
                    employee_id=employee_id or None,
                    project_id=project_id or None,
                    resource_id=resource_id or None,
                    worker_type=worker_type or None,
                )
            )
        )

    def calculate_resource_capacity(
        self, command: ResourceCapacityCommand
    ) -> DesktopApiResult:
        if self._capacity_calculator is None:
            from src.api.desktop.platform.models import DesktopApiResult
            from src.api.desktop.platform.models import DesktopApiError
            return DesktopApiResult(
                ok=False,
                error=DesktopApiError(
                    category="not_available",
                    message="Capacity calculator not configured.",
                    code="not_available",
                ),
            )

        def _compute():
            summary = self._capacity_calculator.compute(
                command.resource_id,
                date.fromisoformat(command.start_date),
                date.fromisoformat(command.end_date),
                project_id=command.project_id or None,
            )
            return ResourceCapacityDto(
                resource_id=summary.resource_id,
                start=str(summary.start),
                end=str(summary.end),
                base_hours=summary.base_hours,
                available_hours=summary.available_hours,
                assigned_hours=summary.assigned_hours,
                remaining_hours=summary.remaining_hours,
                capacity_percent=summary.capacity_percent,
                utilization_percent=summary.utilization_percent,
                working_days=summary.working_days,
                unavailable_days=summary.unavailable_days,
                conflicts=summary.conflicts,
                source_chain=summary.source_chain,
            )

        return execute_desktop_operation(_compute)

    # --- Helpers ---

    def _serialize_assignment(self, assignment, entity_type: str) -> CalendarAssignmentDto:
        cal = self._calendar_service.get_calendar(assignment.calendar_id)
        entity_id = getattr(
            assignment,
            f"{entity_type}_id",
            getattr(assignment, "id", ""),
        )
        return CalendarAssignmentDto(
            id=assignment.id,
            entity_type=entity_type,
            entity_id=entity_id,
            calendar_id=assignment.calendar_id,
            calendar_name=cal.name,
            calendar_type=cal.calendar_type,
            is_default=assignment.is_default,
            priority=assignment.priority,
            effective_from=_fmt_date(assignment.effective_from),
            effective_to=_fmt_date(assignment.effective_to),
        )


__all__ = ["EnterpriseCalendarDesktopApi"]
