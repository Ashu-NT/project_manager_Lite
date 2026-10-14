"""Calendar calendar assignment operations."""

from __future__ import annotations

from datetime import date
from typing import Any, Generic, TypeVar

from src.core.platform.contract.port.time_management.calendar.external_assignment_port import (
    ExternalCalendarAssignment,
    ProjectCalendarAssignmentPort,
    ResourceCalendarAssignmentPort,
)
from src.core.platform.contract.repositories.time_management.calendar.contracts import (
    CalendarAssignmentRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    DepartmentCalendarAssignment,
    EmployeeCalendarAssignment,
    SiteCalendarAssignment,
)

ProjectAssignmentT = TypeVar("ProjectAssignmentT", bound=ExternalCalendarAssignment)
ResourceAssignmentT = TypeVar("ResourceAssignmentT", bound=ExternalCalendarAssignment)


class CalendarAssignmentQueryHandler(Generic[ProjectAssignmentT, ResourceAssignmentT]):
    """Read-only lookups for calendar assignment."""

    def __init__(
        self,
        *,
        assignment_repo: CalendarAssignmentRepository,
        project_assignment_repo: ProjectCalendarAssignmentPort[ProjectAssignmentT],
        resource_assignment_repo: ResourceCalendarAssignmentPort[ResourceAssignmentT],
    ) -> None:
        self._assignment_repo = assignment_repo
        self._project_assignment_repo = project_assignment_repo
        self._resource_assignment_repo = resource_assignment_repo

    def get_site_calendar(
        self, site_id: str, *, at_date: date | None = None
    ) -> SiteCalendarAssignment | None:
        return self._assignment_repo.get_site_assignment(site_id, at_date=at_date)

    def list_site_assignments(self, site_id: str) -> list[SiteCalendarAssignment]:
        return self._assignment_repo.list_site_assignments(site_id)

    def get_department_calendar(
        self, department_id: str, *, at_date: date | None = None
    ) -> DepartmentCalendarAssignment | None:
        return self._assignment_repo.get_department_assignment(
            department_id, at_date=at_date
        )

    def list_department_assignments(
        self, department_id: str
    ) -> list[DepartmentCalendarAssignment]:
        return self._assignment_repo.list_department_assignments(department_id)

    def get_employee_calendar(
        self, employee_id: str, *, at_date: date | None = None
    ) -> EmployeeCalendarAssignment | None:
        return self._assignment_repo.get_employee_assignment(
            employee_id, at_date=at_date
        )

    def list_employee_assignments(
        self, employee_id: str
    ) -> list[EmployeeCalendarAssignment]:
        return self._assignment_repo.list_employee_assignments(employee_id)

    def get_project_calendar(
        self, project_id: str, *, at_date: date | None = None
    ) -> ProjectAssignmentT | None:
        return self._project_assignment_repo.get(project_id, at_date=at_date)

    def get_resource_calendar(
        self, resource_id: str, *, at_date: date | None = None
    ) -> ResourceAssignmentT | None:
        return self._resource_assignment_repo.get(resource_id, at_date=at_date)

    def list_calendar_assignments(self, calendar_id: str) -> dict[str, Any]:
        return {
            "sites": self._assignment_repo.list_sites_using_calendar(calendar_id),
            "departments": self._assignment_repo.list_departments_using_calendar(
                calendar_id
            ),
            "employees": self._assignment_repo.list_employees_using_calendar(
                calendar_id
            ),
            "projects": self._project_assignment_repo.list_for_calendar(calendar_id),
            "resources": self._resource_assignment_repo.list_for_calendar(calendar_id),
        }


__all__ = ["CalendarAssignmentQueryHandler"]
