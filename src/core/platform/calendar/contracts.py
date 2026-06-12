from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
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


class PlatformCalendarRepository(ABC):
    @abstractmethod
    def get(self, calendar_id: str) -> PlatformCalendar | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, code: str) -> PlatformCalendar | None: ...

    @abstractmethod
    def get_global(self, organization_id: str) -> PlatformCalendar | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        calendar_type: str | None = None,
        active_only: bool | None = None,
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
    def get(self, rule_id: str) -> CalendarWorkingRule | None: ...

    @abstractmethod
    def get_for_weekday(
        self, calendar_id: str, weekday: int
    ) -> CalendarWorkingRule | None: ...

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
        start: date | None = None,
        end: date | None = None,
    ) -> list[CalendarException]: ...

    @abstractmethod
    def list_for_date(
        self, calendar_id: str, target_date: date
    ) -> list[CalendarException]: ...

    @abstractmethod
    def get(self, exception_id: str) -> CalendarException | None: ...

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
    def get(self, event_id: str) -> CalendarRecurringEvent | None: ...

    @abstractmethod
    def add(self, event: CalendarRecurringEvent) -> None: ...

    @abstractmethod
    def update(self, event: CalendarRecurringEvent) -> None: ...

    @abstractmethod
    def delete(self, event_id: str) -> None: ...


class ShiftPatternRepository(ABC):
    @abstractmethod
    def list_for_organization(
        self, organization_id: str, *, active_only: bool | None = None
    ) -> list[ShiftPattern]: ...

    @abstractmethod
    def get(self, pattern_id: str) -> ShiftPattern | None: ...

    @abstractmethod
    def get_by_code(
        self, organization_id: str, code: str
    ) -> ShiftPattern | None: ...

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
        self, site_id: str, *, at_date: date | None = None
    ) -> SiteCalendarAssignment | None: ...

    @abstractmethod
    def list_site_assignments(self, site_id: str) -> list[SiteCalendarAssignment]: ...

    @abstractmethod
    def save_site_assignment(self, assignment: SiteCalendarAssignment) -> None: ...

    @abstractmethod
    def delete_site_assignment(self, assignment_id: str) -> None: ...

    @abstractmethod
    def get_department_assignment(
        self, department_id: str, *, at_date: date | None = None
    ) -> DepartmentCalendarAssignment | None: ...

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
        self, employee_id: str, *, at_date: date | None = None
    ) -> EmployeeCalendarAssignment | None: ...

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
]
