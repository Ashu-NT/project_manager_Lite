from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from src.core.platform.calendar.domain.calendar import Holiday, WorkingCalendar
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


class WorkingCalendarRepository(ABC):
    @abstractmethod
    def get(self, calendar_id: str) -> WorkingCalendar | None: ...

    @abstractmethod
    def get_default(self) -> WorkingCalendar | None: ...

    @abstractmethod
    def upsert(self, calendar: WorkingCalendar) -> None: ...

    @abstractmethod
    def list_holidays(self, calendar_id: str) -> list[Holiday]: ...

    @abstractmethod
    def add_holiday(self, holiday: Holiday) -> None: ...

    @abstractmethod
    def delete_holiday(self, holiday_id: str) -> None: ...


class PlatformCalendarRepository(ABC):
    @abstractmethod
    def get(self, calendar_id: str) -> Optional[PlatformCalendar]: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, code: str) -> Optional[PlatformCalendar]: ...

    @abstractmethod
    def get_global(self, organization_id: str) -> Optional[PlatformCalendar]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        calendar_type: Optional[str] = None,
        active_only: Optional[bool] = None,
    ) -> list[PlatformCalendar]: ...

    @abstractmethod
    def add(self, calendar: PlatformCalendar) -> None: ...

    @abstractmethod
    def update(self, calendar: PlatformCalendar) -> None: ...

    @abstractmethod
    def delete(self, calendar_id: str) -> None: ...


class CalendarWorkingRuleRepository(ABC):
    @abstractmethod
    def list_for_calendar(self, calendar_id: str) -> list[CalendarWorkingRule]: ...

    @abstractmethod
    def get(self, rule_id: str) -> Optional[CalendarWorkingRule]: ...

    @abstractmethod
    def get_for_weekday(
        self, calendar_id: str, weekday: int
    ) -> Optional[CalendarWorkingRule]: ...

    @abstractmethod
    def save(self, rule: CalendarWorkingRule) -> None: ...

    @abstractmethod
    def delete(self, rule_id: str) -> None: ...

    @abstractmethod
    def delete_for_calendar(self, calendar_id: str) -> None: ...


class CalendarExceptionRepository(ABC):
    @abstractmethod
    def list_for_calendar(
        self,
        calendar_id: str,
        *,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> list[CalendarException]: ...

    @abstractmethod
    def list_for_date(
        self, calendar_id: str, target_date: date
    ) -> list[CalendarException]: ...

    @abstractmethod
    def get(self, exception_id: str) -> Optional[CalendarException]: ...

    @abstractmethod
    def add(self, exc: CalendarException) -> None: ...

    @abstractmethod
    def update(self, exc: CalendarException) -> None: ...

    @abstractmethod
    def delete(self, exception_id: str) -> None: ...

    @abstractmethod
    def count_for_calendar(self, calendar_id: str) -> int: ...


class CalendarRecurringEventRepository(ABC):
    @abstractmethod
    def list_for_calendar(
        self, calendar_id: str, *, active_only: bool = True
    ) -> list[CalendarRecurringEvent]: ...

    @abstractmethod
    def get(self, event_id: str) -> Optional[CalendarRecurringEvent]: ...

    @abstractmethod
    def add(self, event: CalendarRecurringEvent) -> None: ...

    @abstractmethod
    def update(self, event: CalendarRecurringEvent) -> None: ...

    @abstractmethod
    def delete(self, event_id: str) -> None: ...


class ShiftPatternRepository(ABC):
    @abstractmethod
    def list_for_organization(
        self, organization_id: str, *, active_only: Optional[bool] = None
    ) -> list[ShiftPattern]: ...

    @abstractmethod
    def get(self, pattern_id: str) -> Optional[ShiftPattern]: ...

    @abstractmethod
    def get_by_code(
        self, organization_id: str, code: str
    ) -> Optional[ShiftPattern]: ...

    @abstractmethod
    def add(self, pattern: ShiftPattern) -> None: ...

    @abstractmethod
    def update(self, pattern: ShiftPattern) -> None: ...

    @abstractmethod
    def delete(self, pattern_id: str) -> None: ...

    @abstractmethod
    def list_days(self, pattern_id: str) -> list[ShiftPatternDay]: ...

    @abstractmethod
    def save_day(self, day: ShiftPatternDay) -> None: ...

    @abstractmethod
    def delete_day(self, day_id: str) -> None: ...


class CalendarAssignmentRepository(ABC):
    @abstractmethod
    def get_site_assignment(
        self, site_id: str, *, at_date: Optional[date] = None
    ) -> Optional[SiteCalendarAssignment]: ...

    @abstractmethod
    def list_site_assignments(self, site_id: str) -> list[SiteCalendarAssignment]: ...

    @abstractmethod
    def save_site_assignment(self, assignment: SiteCalendarAssignment) -> None: ...

    @abstractmethod
    def delete_site_assignment(self, assignment_id: str) -> None: ...

    @abstractmethod
    def get_department_assignment(
        self, department_id: str, *, at_date: Optional[date] = None
    ) -> Optional[DepartmentCalendarAssignment]: ...

    @abstractmethod
    def list_department_assignments(
        self, department_id: str
    ) -> list[DepartmentCalendarAssignment]: ...

    @abstractmethod
    def save_department_assignment(
        self, assignment: DepartmentCalendarAssignment
    ) -> None: ...

    @abstractmethod
    def delete_department_assignment(self, assignment_id: str) -> None: ...

    @abstractmethod
    def get_employee_assignment(
        self, employee_id: str, *, at_date: Optional[date] = None
    ) -> Optional[EmployeeCalendarAssignment]: ...

    @abstractmethod
    def list_employee_assignments(
        self, employee_id: str
    ) -> list[EmployeeCalendarAssignment]: ...

    @abstractmethod
    def save_employee_assignment(
        self, assignment: EmployeeCalendarAssignment
    ) -> None: ...

    @abstractmethod
    def delete_employee_assignment(self, assignment_id: str) -> None: ...

    @abstractmethod
    def count_active_assignments_for_calendar(self, calendar_id: str) -> int: ...

    @abstractmethod
    def list_sites_using_calendar(self, calendar_id: str) -> list[SiteCalendarAssignment]: ...

    @abstractmethod
    def list_departments_using_calendar(
        self, calendar_id: str
    ) -> list[DepartmentCalendarAssignment]: ...

    @abstractmethod
    def list_employees_using_calendar(
        self, calendar_id: str
    ) -> list[EmployeeCalendarAssignment]: ...


__all__ = [
    "CalendarAssignmentRepository",
    "CalendarExceptionRepository",
    "CalendarRecurringEventRepository",
    "CalendarWorkingRuleRepository",
    "PlatformCalendarRepository",
    "ShiftPatternRepository",
    "WorkingCalendarRepository",
]
