"""SQLAlchemy repositories for enterprise calendar domain."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.platform.calendar.contracts import (
    CalendarAssignmentRepository,
    CalendarExceptionRepository,
    CalendarRecurringEventRepository,
    CalendarWorkingRuleRepository,
    PlatformCalendarRepository,
    ShiftPatternRepository,
)
from src.core.platform.calendar.domain.enterprise_calendar import (
    CalendarException,
    CalendarRecurringEvent,
    CalendarWorkingRule,
    DepartmentCalendarAssignment,
    EmployeeCalendarAssignment,
    PlatformCalendar,
    ShiftPattern,
    ShiftPatternDay,
    SiteCalendarAssignment,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.infrastructure.persistence.mappers.enterprise_calendar import (
    calendar_exception_from_orm,
    calendar_exception_to_orm,
    dept_assignment_from_orm,
    dept_assignment_to_orm,
    employee_assignment_from_orm,
    employee_assignment_to_orm,
    platform_calendar_from_orm,
    platform_calendar_to_orm,
    recurring_event_from_orm,
    recurring_event_to_orm,
    shift_pattern_day_from_orm,
    shift_pattern_day_to_orm,
    shift_pattern_from_orm,
    shift_pattern_to_orm,
    site_assignment_from_orm,
    site_assignment_to_orm,
    working_rule_from_orm,
    working_rule_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.orm.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.enterprise_calendar import (
    CalendarExceptionORM,
    CalendarRecurringEventORM,
    CalendarWorkingRuleORM,
    DepartmentCalendarAssignmentORM,
    EmployeeCalendarAssignmentORM,
    PlatformCalendarORM,
    ShiftPatternDayORM,
    ShiftPatternORM,
    SiteCalendarAssignmentORM,
)
from src.core.platform.infrastructure.persistence.orm.sites import SiteORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)


def _scoped_calendar_stmt(base_stmt, child_orm, ctx):
    return (
        base_stmt.select_from(child_orm).join(
            PlatformCalendarORM,
            child_orm.calendar_id == PlatformCalendarORM.id,
        )
        .where(
            PlatformCalendarORM.tenant_id == ctx.tenant_id,
            PlatformCalendarORM.organization_id == ctx.organization_id,
        )
    )


def _scoped_shift_pattern_day_stmt(base_stmt, ctx):
    return (
        base_stmt.select_from(ShiftPatternDayORM).join(
            ShiftPatternORM,
            ShiftPatternDayORM.shift_pattern_id == ShiftPatternORM.id,
        ).where(
            ShiftPatternORM.tenant_id == ctx.tenant_id,
            ShiftPatternORM.organization_id == ctx.organization_id,
        )
    )


def _scoped_assignment_stmt(base_stmt, assignment_orm, entity_orm, entity_id_col, ctx):
    return (
        base_stmt.select_from(assignment_orm).join(
            PlatformCalendarORM,
            assignment_orm.calendar_id == PlatformCalendarORM.id,
        ).where(
            PlatformCalendarORM.tenant_id == ctx.tenant_id,
            PlatformCalendarORM.organization_id == ctx.organization_id,
        )
    )


def _ensure_calendar_in_scope(session: Session, ctx, calendar_id: str) -> None:
    exists = session.execute(
        select(PlatformCalendarORM.id).where(
            PlatformCalendarORM.id == calendar_id,
            PlatformCalendarORM.tenant_id == ctx.tenant_id,
            PlatformCalendarORM.organization_id == ctx.organization_id,
        )
    ).scalar_one_or_none()
    if exists is None:
        raise NotFoundError("Calendar not found.")


def _ensure_shift_pattern_in_scope(session: Session, ctx, pattern_id: str) -> None:
    exists = session.execute(
        select(ShiftPatternORM.id).where(
            ShiftPatternORM.id == pattern_id,
            ShiftPatternORM.tenant_id == ctx.tenant_id,
            ShiftPatternORM.organization_id == ctx.organization_id,
        )
    ).scalar_one_or_none()
    if exists is None:
        raise NotFoundError("Shift pattern not found.")


def _ensure_site_in_scope(session: Session, ctx, site_id: str) -> None:
    exists = session.execute(
        select(SiteORM.id).where(
            SiteORM.id == site_id,
            SiteORM.tenant_id == ctx.tenant_id,
            SiteORM.organization_id == ctx.organization_id,
        )
    ).scalar_one_or_none()
    if exists is None:
        raise NotFoundError("Site not found.")


def _ensure_department_in_scope(session: Session, ctx, department_id: str) -> None:
    exists = session.execute(
        select(DepartmentORM.id).where(
            DepartmentORM.id == department_id,
            DepartmentORM.tenant_id == ctx.tenant_id,
            DepartmentORM.organization_id == ctx.organization_id,
        )
    ).scalar_one_or_none()
    if exists is None:
        raise NotFoundError("Department not found.")


def _ensure_employee_in_scope(session: Session, ctx, employee_id: str) -> None:
    exists = session.execute(
        select(EmployeeORM.id).where(
            EmployeeORM.id == employee_id,
            EmployeeORM.tenant_id == ctx.tenant_id,
            EmployeeORM.organization_id == ctx.organization_id,
        )
    ).scalar_one_or_none()
    if exists is None:
        raise NotFoundError("Employee not found.")


class SqlAlchemyPlatformCalendarRepository(
    TenantScopedRepositorySupport, PlatformCalendarRepository
):
    _repository_label = "PlatformCalendarRepository"
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session
        self._tenant_context_service = None

    def get(self, calendar_id: str) -> PlatformCalendar | None:
        ctx = self._context(operation_label="access platform calendars")
        stmt = select(PlatformCalendarORM).where(
            PlatformCalendarORM.id == calendar_id,
            PlatformCalendarORM.tenant_id == ctx.tenant_id,
            PlatformCalendarORM.organization_id == ctx.organization_id,
        )
        obj = self._session.execute(stmt).scalar_one_or_none()
        return platform_calendar_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, code: str) -> PlatformCalendar | None:
        ctx = self._context(operation_label="access platform calendars")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(PlatformCalendarORM).where(
            PlatformCalendarORM.organization_id == ctx.organization_id,
            PlatformCalendarORM.code == code,
            PlatformCalendarORM.tenant_id == ctx.tenant_id,
        )
        obj = self._session.execute(stmt).scalars().first()
        return platform_calendar_from_orm(obj) if obj else None

    def get_global(self, organization_id: str) -> PlatformCalendar | None:
        ctx = self._context(operation_label="access platform calendars")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = (
            select(PlatformCalendarORM)
            .where(
                PlatformCalendarORM.organization_id == ctx.organization_id,
                PlatformCalendarORM.calendar_type == "GLOBAL",
                PlatformCalendarORM.is_active.is_(True),
                PlatformCalendarORM.tenant_id == ctx.tenant_id,
            )
            .order_by(PlatformCalendarORM.priority.desc())
        )
        obj = self._session.execute(stmt).scalars().first()
        return platform_calendar_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        calendar_type: str | None = None,
        active_only: bool | None = None,
    ) -> list[PlatformCalendar]:
        ctx = self._context(operation_label="access platform calendars")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(PlatformCalendarORM).where(
            PlatformCalendarORM.organization_id == ctx.organization_id,
            PlatformCalendarORM.tenant_id == ctx.tenant_id,
        )
        if calendar_type is not None:
            stmt = stmt.where(PlatformCalendarORM.calendar_type == calendar_type)
        if active_only is not None:
            stmt = stmt.where(PlatformCalendarORM.is_active.is_(active_only))
        stmt = stmt.order_by(
            PlatformCalendarORM.calendar_type,
            PlatformCalendarORM.priority.desc(),
            PlatformCalendarORM.name,
        )
        rows = self._session.execute(stmt).scalars().all()
        return [platform_calendar_from_orm(r) for r in rows]

    def add(self, calendar: PlatformCalendar) -> None:
        ctx = self._context(operation_label="access platform calendars")
        orm = platform_calendar_to_orm(calendar)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self._session.add(orm)

    def update(self, calendar: PlatformCalendar) -> None:
        ctx = self._context(operation_label="access platform calendars")
        obj = self._session.execute(
            select(PlatformCalendarORM).where(
                PlatformCalendarORM.id == calendar.id,
                PlatformCalendarORM.tenant_id == ctx.tenant_id,
                PlatformCalendarORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if obj is None:
            return
        obj.code = calendar.code
        obj.name = calendar.name
        obj.description = calendar.description
        obj.calendar_type = calendar.calendar_type
        obj.base_calendar_id = calendar.base_calendar_id
        obj.scope_type = calendar.scope_type
        obj.scope_id = calendar.scope_id
        obj.timezone = calendar.timezone
        obj.locale = calendar.locale
        obj.is_default = calendar.is_default
        obj.is_active = calendar.is_active
        obj.effective_from = calendar.effective_from
        obj.effective_to = calendar.effective_to
        obj.priority = calendar.priority
        obj.version = calendar.version
        obj.updated_by = calendar.updated_by
        obj.updated_at = calendar.updated_at

    def delete(self, calendar_id: str) -> None:
        ctx = self._context(operation_label="access platform calendars")
        obj = self._session.execute(
            select(PlatformCalendarORM).where(
                PlatformCalendarORM.id == calendar_id,
                PlatformCalendarORM.tenant_id == ctx.tenant_id,
                PlatformCalendarORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if obj is not None:
            self._session.delete(obj)


class SqlAlchemyCalendarWorkingRuleRepository(
    TenantScopedRepositorySupport, CalendarWorkingRuleRepository
):
    _repository_label = "CalendarWorkingRuleRepository"
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session
        self._tenant_context_service = None

    def list_for_calendar(self, calendar_id: str) -> list[CalendarWorkingRule]:
        ctx = self._context(operation_label="access calendar working rules")
        stmt = _scoped_calendar_stmt(
            select(CalendarWorkingRuleORM), CalendarWorkingRuleORM, ctx
        ).where(CalendarWorkingRuleORM.calendar_id == calendar_id).order_by(
            CalendarWorkingRuleORM.weekday
        )
        rows = self._session.execute(stmt).scalars().all()
        return [working_rule_from_orm(r) for r in rows]

    def get(self, rule_id: str) -> CalendarWorkingRule | None:
        ctx = self._context(operation_label="access calendar working rules")
        stmt = _scoped_calendar_stmt(
            select(CalendarWorkingRuleORM), CalendarWorkingRuleORM, ctx
        ).where(CalendarWorkingRuleORM.id == rule_id)
        obj = self._session.execute(stmt).scalar_one_or_none()
        return working_rule_from_orm(obj) if obj else None

    def get_for_weekday(
        self, calendar_id: str, weekday: int
    ) -> CalendarWorkingRule | None:
        ctx = self._context(operation_label="access calendar working rules")
        stmt = _scoped_calendar_stmt(
            select(CalendarWorkingRuleORM), CalendarWorkingRuleORM, ctx
        ).where(
            CalendarWorkingRuleORM.calendar_id == calendar_id,
            CalendarWorkingRuleORM.weekday == weekday,
        )
        obj = self._session.execute(stmt).scalars().first()
        return working_rule_from_orm(obj) if obj else None

    def save(self, rule: CalendarWorkingRule) -> None:
        ctx = self._context(operation_label="access calendar working rules")
        existing = self._session.execute(
            _scoped_calendar_stmt(
                select(CalendarWorkingRuleORM), CalendarWorkingRuleORM, ctx
            ).where(CalendarWorkingRuleORM.id == rule.id)
        ).scalar_one_or_none()
        if existing is not None:
            existing.is_working_day = rule.is_working_day
            existing.start_time = rule.start_time
            existing.end_time = rule.end_time
            existing.break_start_time = rule.break_start_time
            existing.break_end_time = rule.break_end_time
            existing.break_minutes = rule.break_minutes
            existing.hours_override = rule.hours_override
            existing.shift_code = rule.shift_code
            existing.effective_from = rule.effective_from
            existing.effective_to = rule.effective_to
            existing.priority = rule.priority
            return
        _ensure_calendar_in_scope(self._session, ctx, rule.calendar_id)
        self._session.add(working_rule_to_orm(rule))

    def delete(self, rule_id: str) -> None:
        ctx = self._context(operation_label="access calendar working rules")
        obj = self._session.execute(
            _scoped_calendar_stmt(
                select(CalendarWorkingRuleORM), CalendarWorkingRuleORM, ctx
            ).where(CalendarWorkingRuleORM.id == rule_id)
        ).scalar_one_or_none()
        if obj is not None:
            self._session.delete(obj)

    def delete_for_calendar(self, calendar_id: str) -> None:
        ctx = self._context(operation_label="access calendar working rules")
        rows = self._session.execute(
            _scoped_calendar_stmt(
                select(CalendarWorkingRuleORM), CalendarWorkingRuleORM, ctx
            ).where(CalendarWorkingRuleORM.calendar_id == calendar_id)
        ).scalars().all()
        for row in rows:
            self._session.delete(row)


class SqlAlchemyCalendarExceptionRepository(
    TenantScopedRepositorySupport, CalendarExceptionRepository
):
    _repository_label = "CalendarExceptionRepository"
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session
        self._tenant_context_service = None

    def list_for_calendar(
        self,
        calendar_id: str,
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> list[CalendarException]:
        ctx = self._context(operation_label="access calendar exceptions")
        stmt = _scoped_calendar_stmt(
            select(CalendarExceptionORM), CalendarExceptionORM, ctx
        ).where(CalendarExceptionORM.calendar_id == calendar_id)
        if start is not None:
            stmt = stmt.where(CalendarExceptionORM.exception_date >= start)
        if end is not None:
            stmt = stmt.where(CalendarExceptionORM.exception_date <= end)
        stmt = stmt.order_by(
            CalendarExceptionORM.exception_date,
            CalendarExceptionORM.priority.desc(),
        )
        rows = self._session.execute(stmt).scalars().all()
        return [calendar_exception_from_orm(r) for r in rows]

    def list_for_date(
        self, calendar_id: str, target_date: date
    ) -> list[CalendarException]:
        ctx = self._context(operation_label="access calendar exceptions")
        stmt = _scoped_calendar_stmt(
            select(CalendarExceptionORM), CalendarExceptionORM, ctx
        ).where(
            CalendarExceptionORM.calendar_id == calendar_id,
            CalendarExceptionORM.exception_date == target_date,
        ).order_by(CalendarExceptionORM.priority.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [calendar_exception_from_orm(r) for r in rows]

    def get(self, exception_id: str) -> CalendarException | None:
        ctx = self._context(operation_label="access calendar exceptions")
        stmt = _scoped_calendar_stmt(
            select(CalendarExceptionORM), CalendarExceptionORM, ctx
        ).where(CalendarExceptionORM.id == exception_id)
        obj = self._session.execute(stmt).scalar_one_or_none()
        return calendar_exception_from_orm(obj) if obj else None

    def add(self, exc: CalendarException) -> None:
        ctx = self._context(operation_label="access calendar exceptions")
        _ensure_calendar_in_scope(self._session, ctx, exc.calendar_id)
        self._session.add(calendar_exception_to_orm(exc))

    def update(self, exc: CalendarException) -> None:
        ctx = self._context(operation_label="access calendar exceptions")
        obj = self._session.execute(
            _scoped_calendar_stmt(
                select(CalendarExceptionORM), CalendarExceptionORM, ctx
            ).where(CalendarExceptionORM.id == exc.id)
        ).scalar_one_or_none()
        if obj is None:
            return
        obj.exception_date = exc.exception_date
        obj.exception_type = exc.exception_type
        obj.name = exc.name
        obj.description = exc.description
        obj.start_time = exc.start_time
        obj.end_time = exc.end_time
        obj.hours_override = exc.hours_override
        obj.impact_type = exc.impact_type
        obj.priority = exc.priority
        obj.approval_status = exc.approval_status
        obj.approved_by = exc.approved_by
        obj.updated_by = exc.updated_by
        obj.updated_at = exc.updated_at

    def delete(self, exception_id: str) -> None:
        ctx = self._context(operation_label="access calendar exceptions")
        obj = self._session.execute(
            _scoped_calendar_stmt(
                select(CalendarExceptionORM), CalendarExceptionORM, ctx
            ).where(CalendarExceptionORM.id == exception_id)
        ).scalar_one_or_none()
        if obj is not None:
            self._session.delete(obj)

    def count_for_calendar(self, calendar_id: str) -> int:
        ctx = self._context(operation_label="access calendar exceptions")
        stmt = _scoped_calendar_stmt(
            select(func.count()),
            CalendarExceptionORM,
            ctx,
        ).where(CalendarExceptionORM.calendar_id == calendar_id)
        return self._session.execute(stmt).scalar() or 0


class SqlAlchemyCalendarRecurringEventRepository(
    TenantScopedRepositorySupport, CalendarRecurringEventRepository
):
    _repository_label = "CalendarRecurringEventRepository"
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session
        self._tenant_context_service = None

    def list_for_calendar(
        self, calendar_id: str, *, active_only: bool = True
    ) -> list[CalendarRecurringEvent]:
        ctx = self._context(operation_label="access recurring events")
        stmt = _scoped_calendar_stmt(
            select(CalendarRecurringEventORM), CalendarRecurringEventORM, ctx
        ).where(CalendarRecurringEventORM.calendar_id == calendar_id)
        if active_only:
            stmt = stmt.where(CalendarRecurringEventORM.is_active.is_(True))
        stmt = stmt.order_by(
            CalendarRecurringEventORM.priority.desc(),
            CalendarRecurringEventORM.title,
        )
        rows = self._session.execute(stmt).scalars().all()
        return [recurring_event_from_orm(r) for r in rows]

    def get(self, event_id: str) -> CalendarRecurringEvent | None:
        ctx = self._context(operation_label="access recurring events")
        stmt = _scoped_calendar_stmt(
            select(CalendarRecurringEventORM), CalendarRecurringEventORM, ctx
        ).where(CalendarRecurringEventORM.id == event_id)
        obj = self._session.execute(stmt).scalar_one_or_none()
        return recurring_event_from_orm(obj) if obj else None

    def add(self, event: CalendarRecurringEvent) -> None:
        ctx = self._context(operation_label="access recurring events")
        _ensure_calendar_in_scope(self._session, ctx, event.calendar_id)
        self._session.add(recurring_event_to_orm(event))

    def update(self, event: CalendarRecurringEvent) -> None:
        ctx = self._context(operation_label="access recurring events")
        obj = self._session.execute(
            _scoped_calendar_stmt(
                select(CalendarRecurringEventORM), CalendarRecurringEventORM, ctx
            ).where(CalendarRecurringEventORM.id == event.id)
        ).scalar_one_or_none()
        if obj is None:
            return
        obj.title = event.title
        obj.event_type = event.event_type
        obj.recurrence_rule = event.recurrence_rule
        obj.start_time = event.start_time
        obj.end_time = event.end_time
        obj.impact_type = event.impact_type
        obj.capacity_impact_percent = event.capacity_impact_percent
        obj.effective_from = event.effective_from
        obj.effective_to = event.effective_to
        obj.is_active = event.is_active
        obj.priority = event.priority

    def delete(self, event_id: str) -> None:
        ctx = self._context(operation_label="access recurring events")
        obj = self._session.execute(
            _scoped_calendar_stmt(
                select(CalendarRecurringEventORM), CalendarRecurringEventORM, ctx
            ).where(CalendarRecurringEventORM.id == event_id)
        ).scalar_one_or_none()
        if obj is not None:
            self._session.delete(obj)


class SqlAlchemyShiftPatternRepository(
    TenantScopedRepositorySupport, ShiftPatternRepository
):
    _repository_label = "ShiftPatternRepository"
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session
        self._tenant_context_service = None

    def list_for_organization(
        self, organization_id: str, *, active_only: bool | None = None
    ) -> list[ShiftPattern]:
        ctx = self._context(operation_label="access shift patterns")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(ShiftPatternORM).where(
            ShiftPatternORM.organization_id == ctx.organization_id,
            ShiftPatternORM.tenant_id == ctx.tenant_id,
        )
        if active_only is not None:
            stmt = stmt.where(ShiftPatternORM.is_active.is_(active_only))
        stmt = stmt.order_by(ShiftPatternORM.name)
        rows = self._session.execute(stmt).scalars().all()
        return [shift_pattern_from_orm(r) for r in rows]

    def get(self, pattern_id: str) -> ShiftPattern | None:
        ctx = self._context(operation_label="access shift patterns")
        stmt = select(ShiftPatternORM).where(
            ShiftPatternORM.id == pattern_id,
            ShiftPatternORM.tenant_id == ctx.tenant_id,
            ShiftPatternORM.organization_id == ctx.organization_id,
        )
        obj = self._session.execute(stmt).scalar_one_or_none()
        return shift_pattern_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, code: str) -> ShiftPattern | None:
        ctx = self._context(operation_label="access shift patterns")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(ShiftPatternORM).where(
            ShiftPatternORM.organization_id == ctx.organization_id,
            ShiftPatternORM.code == code,
            ShiftPatternORM.tenant_id == ctx.tenant_id,
        )
        obj = self._session.execute(stmt).scalars().first()
        return shift_pattern_from_orm(obj) if obj else None

    def add(self, pattern: ShiftPattern) -> None:
        ctx = self._context(operation_label="access shift patterns")
        orm = shift_pattern_to_orm(pattern)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self._session.add(orm)

    def update(self, pattern: ShiftPattern) -> None:
        ctx = self._context(operation_label="access shift patterns")
        obj = self._session.execute(
            select(ShiftPatternORM).where(
                ShiftPatternORM.id == pattern.id,
                ShiftPatternORM.tenant_id == ctx.tenant_id,
                ShiftPatternORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if obj is None:
            return
        obj.code = pattern.code
        obj.name = pattern.name
        obj.description = pattern.description
        obj.pattern_type = pattern.pattern_type
        obj.rotation_cycle_days = pattern.rotation_cycle_days
        obj.timezone = pattern.timezone
        obj.is_active = pattern.is_active

    def delete(self, pattern_id: str) -> None:
        ctx = self._context(operation_label="access shift patterns")
        obj = self._session.execute(
            select(ShiftPatternORM).where(
                ShiftPatternORM.id == pattern_id,
                ShiftPatternORM.tenant_id == ctx.tenant_id,
                ShiftPatternORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if obj is not None:
            self._session.delete(obj)

    def list_days(self, pattern_id: str) -> list[ShiftPatternDay]:
        ctx = self._context(operation_label="access shift patterns")
        stmt = _scoped_shift_pattern_day_stmt(
            select(ShiftPatternDayORM), ctx
        ).where(ShiftPatternDayORM.shift_pattern_id == pattern_id).order_by(
            ShiftPatternDayORM.day_offset
        )
        rows = self._session.execute(stmt).scalars().all()
        return [shift_pattern_day_from_orm(r) for r in rows]

    def save_day(self, day: ShiftPatternDay) -> None:
        ctx = self._context(operation_label="access shift patterns")
        existing = self._session.execute(
            _scoped_shift_pattern_day_stmt(select(ShiftPatternDayORM), ctx).where(
                ShiftPatternDayORM.id == day.id
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.is_working_day = day.is_working_day
            existing.start_time = day.start_time
            existing.end_time = day.end_time
            existing.break_minutes = day.break_minutes
            existing.hours = day.hours
            existing.shift_label = day.shift_label
            return
        _ensure_shift_pattern_in_scope(self._session, ctx, day.shift_pattern_id)
        self._session.add(shift_pattern_day_to_orm(day))

    def delete_day(self, day_id: str) -> None:
        ctx = self._context(operation_label="access shift patterns")
        obj = self._session.execute(
            _scoped_shift_pattern_day_stmt(select(ShiftPatternDayORM), ctx).where(
                ShiftPatternDayORM.id == day_id
            )
        ).scalar_one_or_none()
        if obj is not None:
            self._session.delete(obj)


class SqlAlchemyCalendarAssignmentRepository(
    TenantScopedRepositorySupport, CalendarAssignmentRepository
):
    _repository_label = "CalendarAssignmentRepository"
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session
        self._tenant_context_service = None

    def _is_effective(
        self,
        effective_from: date | None,
        effective_to: date | None,
        at_date: date | None,
    ) -> bool:
        if at_date is None:
            return True
        if effective_from is not None and at_date < effective_from:
            return False
        if effective_to is not None and at_date > effective_to:
            return False
        return True

    def get_site_assignment(
        self, site_id: str, *, at_date: date | None = None
    ) -> SiteCalendarAssignment | None:
        ctx = self._context(operation_label="access calendar assignments")
        stmt = _scoped_assignment_stmt(
            select(SiteCalendarAssignmentORM),
            SiteCalendarAssignmentORM,
            SiteORM,
            SiteCalendarAssignmentORM.site_id,
            ctx,
        ).where(SiteCalendarAssignmentORM.site_id == site_id).order_by(
            SiteCalendarAssignmentORM.priority.desc(),
            SiteCalendarAssignmentORM.is_default.desc(),
        )
        rows = self._session.execute(stmt).scalars().all()
        for row in rows:
            if self._is_effective(row.effective_from, row.effective_to, at_date):
                return site_assignment_from_orm(row)
        return None

    def list_site_assignments(self, site_id: str) -> list[SiteCalendarAssignment]:
        ctx = self._context(operation_label="access calendar assignments")
        stmt = _scoped_assignment_stmt(
            select(SiteCalendarAssignmentORM),
            SiteCalendarAssignmentORM,
            SiteORM,
            SiteCalendarAssignmentORM.site_id,
            ctx,
        ).where(SiteCalendarAssignmentORM.site_id == site_id).order_by(
            SiteCalendarAssignmentORM.priority.desc()
        )
        rows = self._session.execute(stmt).scalars().all()
        return [site_assignment_from_orm(r) for r in rows]

    def save_site_assignment(self, assignment: SiteCalendarAssignment) -> None:
        ctx = self._context(operation_label="access calendar assignments")
        existing = self._session.execute(
            _scoped_assignment_stmt(
                select(SiteCalendarAssignmentORM),
                SiteCalendarAssignmentORM,
                SiteORM,
                SiteCalendarAssignmentORM.site_id,
                ctx,
            ).where(SiteCalendarAssignmentORM.id == assignment.id)
        ).scalar_one_or_none()
        if existing is not None:
            existing.calendar_id = assignment.calendar_id
            existing.effective_from = assignment.effective_from
            existing.effective_to = assignment.effective_to
            existing.is_default = assignment.is_default
            existing.priority = assignment.priority
            return
        _ensure_calendar_in_scope(self._session, ctx, assignment.calendar_id)
        self._session.add(site_assignment_to_orm(assignment))

    def delete_site_assignment(self, assignment_id: str) -> None:
        ctx = self._context(operation_label="access calendar assignments")
        obj = self._session.execute(
            _scoped_assignment_stmt(
                select(SiteCalendarAssignmentORM),
                SiteCalendarAssignmentORM,
                SiteORM,
                SiteCalendarAssignmentORM.site_id,
                ctx,
            ).where(SiteCalendarAssignmentORM.id == assignment_id)
        ).scalar_one_or_none()
        if obj is not None:
            self._session.delete(obj)

    def get_department_assignment(
        self, department_id: str, *, at_date: date | None = None
    ) -> DepartmentCalendarAssignment | None:
        ctx = self._context(operation_label="access calendar assignments")
        stmt = _scoped_assignment_stmt(
            select(DepartmentCalendarAssignmentORM),
            DepartmentCalendarAssignmentORM,
            DepartmentORM,
            DepartmentCalendarAssignmentORM.department_id,
            ctx,
        ).where(DepartmentCalendarAssignmentORM.department_id == department_id).order_by(
            DepartmentCalendarAssignmentORM.priority.desc(),
            DepartmentCalendarAssignmentORM.is_default.desc(),
        )
        rows = self._session.execute(stmt).scalars().all()
        for row in rows:
            if self._is_effective(row.effective_from, row.effective_to, at_date):
                return dept_assignment_from_orm(row)
        return None

    def list_department_assignments(
        self, department_id: str
    ) -> list[DepartmentCalendarAssignment]:
        ctx = self._context(operation_label="access calendar assignments")
        stmt = _scoped_assignment_stmt(
            select(DepartmentCalendarAssignmentORM),
            DepartmentCalendarAssignmentORM,
            DepartmentORM,
            DepartmentCalendarAssignmentORM.department_id,
            ctx,
        ).where(DepartmentCalendarAssignmentORM.department_id == department_id).order_by(
            DepartmentCalendarAssignmentORM.priority.desc()
        )
        rows = self._session.execute(stmt).scalars().all()
        return [dept_assignment_from_orm(r) for r in rows]

    def save_department_assignment(
        self, assignment: DepartmentCalendarAssignment
    ) -> None:
        ctx = self._context(operation_label="access calendar assignments")
        existing = self._session.execute(
            _scoped_assignment_stmt(
                select(DepartmentCalendarAssignmentORM),
                DepartmentCalendarAssignmentORM,
                DepartmentORM,
                DepartmentCalendarAssignmentORM.department_id,
                ctx,
            ).where(DepartmentCalendarAssignmentORM.id == assignment.id)
        ).scalar_one_or_none()
        if existing is not None:
            existing.calendar_id = assignment.calendar_id
            existing.effective_from = assignment.effective_from
            existing.effective_to = assignment.effective_to
            existing.is_default = assignment.is_default
            existing.priority = assignment.priority
            return
        _ensure_calendar_in_scope(self._session, ctx, assignment.calendar_id)
        self._session.add(dept_assignment_to_orm(assignment))

    def delete_department_assignment(self, assignment_id: str) -> None:
        ctx = self._context(operation_label="access calendar assignments")
        obj = self._session.execute(
            _scoped_assignment_stmt(
                select(DepartmentCalendarAssignmentORM),
                DepartmentCalendarAssignmentORM,
                DepartmentORM,
                DepartmentCalendarAssignmentORM.department_id,
                ctx,
            ).where(DepartmentCalendarAssignmentORM.id == assignment_id)
        ).scalar_one_or_none()
        if obj is not None:
            self._session.delete(obj)

    def get_employee_assignment(
        self, employee_id: str, *, at_date: date | None = None
    ) -> EmployeeCalendarAssignment | None:
        ctx = self._context(operation_label="access calendar assignments")
        stmt = _scoped_assignment_stmt(
            select(EmployeeCalendarAssignmentORM),
            EmployeeCalendarAssignmentORM,
            EmployeeORM,
            EmployeeCalendarAssignmentORM.employee_id,
            ctx,
        ).where(EmployeeCalendarAssignmentORM.employee_id == employee_id).order_by(
            EmployeeCalendarAssignmentORM.priority.desc(),
            EmployeeCalendarAssignmentORM.is_default.desc(),
        )
        rows = self._session.execute(stmt).scalars().all()
        for row in rows:
            if self._is_effective(row.effective_from, row.effective_to, at_date):
                return employee_assignment_from_orm(row)
        return None

    def list_employee_assignments(
        self, employee_id: str
    ) -> list[EmployeeCalendarAssignment]:
        ctx = self._context(operation_label="access calendar assignments")
        stmt = _scoped_assignment_stmt(
            select(EmployeeCalendarAssignmentORM),
            EmployeeCalendarAssignmentORM,
            EmployeeORM,
            EmployeeCalendarAssignmentORM.employee_id,
            ctx,
        ).where(EmployeeCalendarAssignmentORM.employee_id == employee_id).order_by(
            EmployeeCalendarAssignmentORM.priority.desc()
        )
        rows = self._session.execute(stmt).scalars().all()
        return [employee_assignment_from_orm(r) for r in rows]

    def save_employee_assignment(
        self, assignment: EmployeeCalendarAssignment
    ) -> None:
        ctx = self._context(operation_label="access calendar assignments")
        existing = self._session.execute(
            _scoped_assignment_stmt(
                select(EmployeeCalendarAssignmentORM),
                EmployeeCalendarAssignmentORM,
                EmployeeORM,
                EmployeeCalendarAssignmentORM.employee_id,
                ctx,
            ).where(EmployeeCalendarAssignmentORM.id == assignment.id)
        ).scalar_one_or_none()
        if existing is not None:
            existing.calendar_id = assignment.calendar_id
            existing.effective_from = assignment.effective_from
            existing.effective_to = assignment.effective_to
            existing.is_default = assignment.is_default
            existing.priority = assignment.priority
            return
        _ensure_calendar_in_scope(self._session, ctx, assignment.calendar_id)
        self._session.add(employee_assignment_to_orm(assignment))

    def delete_employee_assignment(self, assignment_id: str) -> None:
        ctx = self._context(operation_label="access calendar assignments")
        obj = self._session.execute(
            _scoped_assignment_stmt(
                select(EmployeeCalendarAssignmentORM),
                EmployeeCalendarAssignmentORM,
                EmployeeORM,
                EmployeeCalendarAssignmentORM.employee_id,
                ctx,
            ).where(EmployeeCalendarAssignmentORM.id == assignment_id)
        ).scalar_one_or_none()
        if obj is not None:
            self._session.delete(obj)

    def count_active_assignments_for_calendar(self, calendar_id: str) -> int:
        ctx = self._context(operation_label="access calendar assignments")
        site_count = (
            self._session.execute(
                _scoped_assignment_stmt(
                    select(func.count()),
                    SiteCalendarAssignmentORM,
                    SiteORM,
                    SiteCalendarAssignmentORM.site_id,
                    ctx,
                ).where(SiteCalendarAssignmentORM.calendar_id == calendar_id)
            ).scalar()
            or 0
        )
        dept_count = (
            self._session.execute(
                _scoped_assignment_stmt(
                    select(func.count()),
                    DepartmentCalendarAssignmentORM,
                    DepartmentORM,
                    DepartmentCalendarAssignmentORM.department_id,
                    ctx,
                ).where(DepartmentCalendarAssignmentORM.calendar_id == calendar_id)
            ).scalar()
            or 0
        )
        emp_count = (
            self._session.execute(
                _scoped_assignment_stmt(
                    select(func.count()),
                    EmployeeCalendarAssignmentORM,
                    EmployeeORM,
                    EmployeeCalendarAssignmentORM.employee_id,
                    ctx,
                ).where(EmployeeCalendarAssignmentORM.calendar_id == calendar_id)
            ).scalar()
            or 0
        )
        return site_count + dept_count + emp_count

    def list_sites_using_calendar(
        self, calendar_id: str
    ) -> list[SiteCalendarAssignment]:
        ctx = self._context(operation_label="access calendar assignments")
        stmt = _scoped_assignment_stmt(
            select(SiteCalendarAssignmentORM),
            SiteCalendarAssignmentORM,
            SiteORM,
            SiteCalendarAssignmentORM.site_id,
            ctx,
        ).where(SiteCalendarAssignmentORM.calendar_id == calendar_id)
        rows = self._session.execute(stmt).scalars().all()
        return [site_assignment_from_orm(r) for r in rows]

    def list_departments_using_calendar(
        self, calendar_id: str
    ) -> list[DepartmentCalendarAssignment]:
        ctx = self._context(operation_label="access calendar assignments")
        stmt = _scoped_assignment_stmt(
            select(DepartmentCalendarAssignmentORM),
            DepartmentCalendarAssignmentORM,
            DepartmentORM,
            DepartmentCalendarAssignmentORM.department_id,
            ctx,
        ).where(DepartmentCalendarAssignmentORM.calendar_id == calendar_id)
        rows = self._session.execute(stmt).scalars().all()
        return [dept_assignment_from_orm(r) for r in rows]

    def list_employees_using_calendar(
        self, calendar_id: str
    ) -> list[EmployeeCalendarAssignment]:
        ctx = self._context(operation_label="access calendar assignments")
        stmt = _scoped_assignment_stmt(
            select(EmployeeCalendarAssignmentORM),
            EmployeeCalendarAssignmentORM,
            EmployeeORM,
            EmployeeCalendarAssignmentORM.employee_id,
            ctx,
        ).where(EmployeeCalendarAssignmentORM.calendar_id == calendar_id)
        rows = self._session.execute(stmt).scalars().all()
        return [employee_assignment_from_orm(r) for r in rows]


__all__ = [
    "SqlAlchemyCalendarAssignmentRepository",
    "SqlAlchemyCalendarExceptionRepository",
    "SqlAlchemyCalendarRecurringEventRepository",
    "SqlAlchemyCalendarWorkingRuleRepository",
    "SqlAlchemyPlatformCalendarRepository",
    "SqlAlchemyShiftPatternRepository",
]
