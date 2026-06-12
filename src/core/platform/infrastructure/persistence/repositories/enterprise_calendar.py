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


class SqlAlchemyPlatformCalendarRepository(PlatformCalendarRepository):
    _session: Session

    def __init__(self, session: Session, *, tenant_id_provider=None) -> None:
        self._session = session
        self._tenant_id_provider = tenant_id_provider or (lambda: None)

    def get(self, calendar_id: str) -> PlatformCalendar | None:
        obj = self._session.get(PlatformCalendarORM, calendar_id)
        if obj is None:
            return None
        _tid = self._tenant_id_provider()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return platform_calendar_from_orm(obj)

    def get_by_code(self, organization_id: str, code: str) -> PlatformCalendar | None:
        _tid = self._tenant_id_provider()
        stmt = select(PlatformCalendarORM).where(
            PlatformCalendarORM.organization_id == organization_id,
            PlatformCalendarORM.code == code,
        )
        if _tid is not None:
            stmt = stmt.where(PlatformCalendarORM.tenant_id == _tid)
        obj = self._session.execute(stmt).scalars().first()
        return platform_calendar_from_orm(obj) if obj else None

    def get_global(self, organization_id: str) -> PlatformCalendar | None:
        _tid = self._tenant_id_provider()
        stmt = select(PlatformCalendarORM).where(
            PlatformCalendarORM.organization_id == organization_id,
            PlatformCalendarORM.calendar_type == "GLOBAL",
            PlatformCalendarORM.is_active.is_(True),
        )
        if _tid is not None:
            stmt = stmt.where(PlatformCalendarORM.tenant_id == _tid)
        stmt = stmt.order_by(PlatformCalendarORM.priority.desc())
        obj = self._session.execute(stmt).scalars().first()
        return platform_calendar_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        calendar_type: str | None = None,
        active_only: bool | None = None,
    ) -> list[PlatformCalendar]:
        _tid = self._tenant_id_provider()
        stmt = select(PlatformCalendarORM).where(
            PlatformCalendarORM.organization_id == organization_id
        )
        if _tid is not None:
            stmt = stmt.where(PlatformCalendarORM.tenant_id == _tid)
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
        orm = platform_calendar_to_orm(calendar)
        if orm.tenant_id is None:
            orm.tenant_id = self._tenant_id_provider()
        self._session.add(orm)

    def update(self, calendar: PlatformCalendar) -> None:
        obj = self._session.get(PlatformCalendarORM, calendar.id)
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
        self._session.query(PlatformCalendarORM).filter_by(id=calendar_id).delete()


class SqlAlchemyCalendarWorkingRuleRepository(CalendarWorkingRuleRepository):
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_calendar(self, calendar_id: str) -> list[CalendarWorkingRule]:
        stmt = select(CalendarWorkingRuleORM).where(
            CalendarWorkingRuleORM.calendar_id == calendar_id
        ).order_by(CalendarWorkingRuleORM.weekday)
        rows = self._session.execute(stmt).scalars().all()
        return [working_rule_from_orm(r) for r in rows]

    def get(self, rule_id: str) -> CalendarWorkingRule | None:
        obj = self._session.get(CalendarWorkingRuleORM, rule_id)
        return working_rule_from_orm(obj) if obj else None

    def get_for_weekday(
        self, calendar_id: str, weekday: int
    ) -> CalendarWorkingRule | None:
        stmt = select(CalendarWorkingRuleORM).where(
            CalendarWorkingRuleORM.calendar_id == calendar_id,
            CalendarWorkingRuleORM.weekday == weekday,
        )
        obj = self._session.execute(stmt).scalars().first()
        return working_rule_from_orm(obj) if obj else None

    def save(self, rule: CalendarWorkingRule) -> None:
        existing = self._session.get(CalendarWorkingRuleORM, rule.id)
        if existing:
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
        else:
            self._session.add(working_rule_to_orm(rule))

    def delete(self, rule_id: str) -> None:
        self._session.query(CalendarWorkingRuleORM).filter_by(id=rule_id).delete()

    def delete_for_calendar(self, calendar_id: str) -> None:
        self._session.query(CalendarWorkingRuleORM).filter_by(
            calendar_id=calendar_id
        ).delete()


class SqlAlchemyCalendarExceptionRepository(CalendarExceptionRepository):
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_calendar(
        self,
        calendar_id: str,
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> list[CalendarException]:
        stmt = select(CalendarExceptionORM).where(
            CalendarExceptionORM.calendar_id == calendar_id
        )
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
        stmt = select(CalendarExceptionORM).where(
            CalendarExceptionORM.calendar_id == calendar_id,
            CalendarExceptionORM.exception_date == target_date,
        ).order_by(CalendarExceptionORM.priority.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [calendar_exception_from_orm(r) for r in rows]

    def get(self, exception_id: str) -> CalendarException | None:
        obj = self._session.get(CalendarExceptionORM, exception_id)
        return calendar_exception_from_orm(obj) if obj else None

    def add(self, exc: CalendarException) -> None:
        self._session.add(calendar_exception_to_orm(exc))

    def update(self, exc: CalendarException) -> None:
        obj = self._session.get(CalendarExceptionORM, exc.id)
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
        self._session.query(CalendarExceptionORM).filter_by(id=exception_id).delete()

    def count_for_calendar(self, calendar_id: str) -> int:
        stmt = select(func.count()).where(
            CalendarExceptionORM.calendar_id == calendar_id
        )
        return self._session.execute(stmt).scalar() or 0


class SqlAlchemyCalendarRecurringEventRepository(CalendarRecurringEventRepository):
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_calendar(
        self, calendar_id: str, *, active_only: bool = True
    ) -> list[CalendarRecurringEvent]:
        stmt = select(CalendarRecurringEventORM).where(
            CalendarRecurringEventORM.calendar_id == calendar_id
        )
        if active_only:
            stmt = stmt.where(CalendarRecurringEventORM.is_active.is_(True))
        stmt = stmt.order_by(
            CalendarRecurringEventORM.priority.desc(),
            CalendarRecurringEventORM.title,
        )
        rows = self._session.execute(stmt).scalars().all()
        return [recurring_event_from_orm(r) for r in rows]

    def get(self, event_id: str) -> CalendarRecurringEvent | None:
        obj = self._session.get(CalendarRecurringEventORM, event_id)
        return recurring_event_from_orm(obj) if obj else None

    def add(self, event: CalendarRecurringEvent) -> None:
        self._session.add(recurring_event_to_orm(event))

    def update(self, event: CalendarRecurringEvent) -> None:
        obj = self._session.get(CalendarRecurringEventORM, event.id)
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
        self._session.query(CalendarRecurringEventORM).filter_by(id=event_id).delete()


class SqlAlchemyShiftPatternRepository(ShiftPatternRepository):
    _session: Session

    def __init__(self, session: Session, *, tenant_id_provider=None) -> None:
        self._session = session
        self._tenant_id_provider = tenant_id_provider or (lambda: None)

    def list_for_organization(
        self, organization_id: str, *, active_only: bool | None = None
    ) -> list[ShiftPattern]:
        _tid = self._tenant_id_provider()
        stmt = select(ShiftPatternORM).where(
            ShiftPatternORM.organization_id == organization_id
        )
        if _tid is not None:
            stmt = stmt.where(ShiftPatternORM.tenant_id == _tid)
        if active_only is not None:
            stmt = stmt.where(ShiftPatternORM.is_active.is_(active_only))
        stmt = stmt.order_by(ShiftPatternORM.name)
        rows = self._session.execute(stmt).scalars().all()
        return [shift_pattern_from_orm(r) for r in rows]

    def get(self, pattern_id: str) -> ShiftPattern | None:
        obj = self._session.get(ShiftPatternORM, pattern_id)
        if obj is None:
            return None
        _tid = self._tenant_id_provider()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return shift_pattern_from_orm(obj)

    def get_by_code(self, organization_id: str, code: str) -> ShiftPattern | None:
        _tid = self._tenant_id_provider()
        stmt = select(ShiftPatternORM).where(
            ShiftPatternORM.organization_id == organization_id,
            ShiftPatternORM.code == code,
        )
        if _tid is not None:
            stmt = stmt.where(ShiftPatternORM.tenant_id == _tid)
        obj = self._session.execute(stmt).scalars().first()
        return shift_pattern_from_orm(obj) if obj else None

    def add(self, pattern: ShiftPattern) -> None:
        orm = shift_pattern_to_orm(pattern)
        if orm.tenant_id is None:
            orm.tenant_id = self._tenant_id_provider()
        self._session.add(orm)

    def update(self, pattern: ShiftPattern) -> None:
        obj = self._session.get(ShiftPatternORM, pattern.id)
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
        self._session.query(ShiftPatternORM).filter_by(id=pattern_id).delete()

    def list_days(self, pattern_id: str) -> list[ShiftPatternDay]:
        stmt = select(ShiftPatternDayORM).where(
            ShiftPatternDayORM.shift_pattern_id == pattern_id
        ).order_by(ShiftPatternDayORM.day_offset)
        rows = self._session.execute(stmt).scalars().all()
        return [shift_pattern_day_from_orm(r) for r in rows]

    def save_day(self, day: ShiftPatternDay) -> None:
        existing = self._session.get(ShiftPatternDayORM, day.id)
        if existing:
            existing.is_working_day = day.is_working_day
            existing.start_time = day.start_time
            existing.end_time = day.end_time
            existing.break_minutes = day.break_minutes
            existing.hours = day.hours
            existing.shift_label = day.shift_label
        else:
            self._session.add(shift_pattern_day_to_orm(day))

    def delete_day(self, day_id: str) -> None:
        self._session.query(ShiftPatternDayORM).filter_by(id=day_id).delete()


class SqlAlchemyCalendarAssignmentRepository(CalendarAssignmentRepository):
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Site ---

    def _is_effective(self, effective_from: date | None, effective_to: date | None, at_date: date | None) -> bool:
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
        stmt = select(SiteCalendarAssignmentORM).where(
            SiteCalendarAssignmentORM.site_id == site_id
        ).order_by(
            SiteCalendarAssignmentORM.priority.desc(),
            SiteCalendarAssignmentORM.is_default.desc(),
        )
        rows = self._session.execute(stmt).scalars().all()
        for row in rows:
            if self._is_effective(row.effective_from, row.effective_to, at_date):
                return site_assignment_from_orm(row)
        return None

    def list_site_assignments(self, site_id: str) -> list[SiteCalendarAssignment]:
        stmt = select(SiteCalendarAssignmentORM).where(
            SiteCalendarAssignmentORM.site_id == site_id
        ).order_by(SiteCalendarAssignmentORM.priority.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [site_assignment_from_orm(r) for r in rows]

    def save_site_assignment(self, assignment: SiteCalendarAssignment) -> None:
        existing = self._session.get(SiteCalendarAssignmentORM, assignment.id)
        if existing:
            existing.calendar_id = assignment.calendar_id
            existing.effective_from = assignment.effective_from
            existing.effective_to = assignment.effective_to
            existing.is_default = assignment.is_default
            existing.priority = assignment.priority
        else:
            self._session.add(site_assignment_to_orm(assignment))

    def delete_site_assignment(self, assignment_id: str) -> None:
        self._session.query(SiteCalendarAssignmentORM).filter_by(
            id=assignment_id
        ).delete()

    # --- Department ---

    def get_department_assignment(
        self, department_id: str, *, at_date: date | None = None
    ) -> DepartmentCalendarAssignment | None:
        stmt = select(DepartmentCalendarAssignmentORM).where(
            DepartmentCalendarAssignmentORM.department_id == department_id
        ).order_by(
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
        stmt = select(DepartmentCalendarAssignmentORM).where(
            DepartmentCalendarAssignmentORM.department_id == department_id
        ).order_by(DepartmentCalendarAssignmentORM.priority.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [dept_assignment_from_orm(r) for r in rows]

    def save_department_assignment(
        self, assignment: DepartmentCalendarAssignment
    ) -> None:
        existing = self._session.get(DepartmentCalendarAssignmentORM, assignment.id)
        if existing:
            existing.calendar_id = assignment.calendar_id
            existing.effective_from = assignment.effective_from
            existing.effective_to = assignment.effective_to
            existing.is_default = assignment.is_default
            existing.priority = assignment.priority
        else:
            self._session.add(dept_assignment_to_orm(assignment))

    def delete_department_assignment(self, assignment_id: str) -> None:
        self._session.query(DepartmentCalendarAssignmentORM).filter_by(
            id=assignment_id
        ).delete()

    # --- Employee ---

    def get_employee_assignment(
        self, employee_id: str, *, at_date: date | None = None
    ) -> EmployeeCalendarAssignment | None:
        stmt = select(EmployeeCalendarAssignmentORM).where(
            EmployeeCalendarAssignmentORM.employee_id == employee_id
        ).order_by(
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
        stmt = select(EmployeeCalendarAssignmentORM).where(
            EmployeeCalendarAssignmentORM.employee_id == employee_id
        ).order_by(EmployeeCalendarAssignmentORM.priority.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [employee_assignment_from_orm(r) for r in rows]

    def save_employee_assignment(
        self, assignment: EmployeeCalendarAssignment
    ) -> None:
        existing = self._session.get(EmployeeCalendarAssignmentORM, assignment.id)
        if existing:
            existing.calendar_id = assignment.calendar_id
            existing.effective_from = assignment.effective_from
            existing.effective_to = assignment.effective_to
            existing.is_default = assignment.is_default
            existing.priority = assignment.priority
        else:
            self._session.add(employee_assignment_to_orm(assignment))

    def delete_employee_assignment(self, assignment_id: str) -> None:
        self._session.query(EmployeeCalendarAssignmentORM).filter_by(
            id=assignment_id
        ).delete()

    # --- Count + list by calendar ---

    def count_active_assignments_for_calendar(self, calendar_id: str) -> int:
        site_count = (
            self._session.execute(
                select(func.count()).where(
                    SiteCalendarAssignmentORM.calendar_id == calendar_id
                )
            ).scalar()
            or 0
        )
        dept_count = (
            self._session.execute(
                select(func.count()).where(
                    DepartmentCalendarAssignmentORM.calendar_id == calendar_id
                )
            ).scalar()
            or 0
        )
        emp_count = (
            self._session.execute(
                select(func.count()).where(
                    EmployeeCalendarAssignmentORM.calendar_id == calendar_id
                )
            ).scalar()
            or 0
        )
        return site_count + dept_count + emp_count

    def list_sites_using_calendar(
        self, calendar_id: str
    ) -> list[SiteCalendarAssignment]:
        stmt = select(SiteCalendarAssignmentORM).where(
            SiteCalendarAssignmentORM.calendar_id == calendar_id
        )
        rows = self._session.execute(stmt).scalars().all()
        return [site_assignment_from_orm(r) for r in rows]

    def list_departments_using_calendar(
        self, calendar_id: str
    ) -> list[DepartmentCalendarAssignment]:
        stmt = select(DepartmentCalendarAssignmentORM).where(
            DepartmentCalendarAssignmentORM.calendar_id == calendar_id
        )
        rows = self._session.execute(stmt).scalars().all()
        return [dept_assignment_from_orm(r) for r in rows]

    def list_employees_using_calendar(
        self, calendar_id: str
    ) -> list[EmployeeCalendarAssignment]:
        stmt = select(EmployeeCalendarAssignmentORM).where(
            EmployeeCalendarAssignmentORM.calendar_id == calendar_id
        )
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
