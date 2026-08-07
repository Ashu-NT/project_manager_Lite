"""Calendar assignment service — assign/unassign calendars to entities."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.contract.time_management.calendar.contracts import (
    CalendarAssignmentRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    DepartmentCalendarAssignment,
    EmployeeCalendarAssignment,
    SiteCalendarAssignment,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError


class CalendarAssignmentService:
    """Assign/unassign platform calendars to sites, departments, and employees."""

    def __init__(
        self,
        session: Session,
        calendar_repo: PlatformCalendarRepository,
        assignment_repo: CalendarAssignmentRepository,
        project_assignment_repo: Any,
        resource_assignment_repo: Any,
        user_session: Any = None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._assignment_repo = assignment_repo
        self._project_assignment_repo = project_assignment_repo
        self._resource_assignment_repo = resource_assignment_repo
        self._user_session = user_session

    def _require_calendar(self, calendar_id: str) -> None:
        cal = self._calendar_repo.get(calendar_id)
        if cal is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")
        if not cal.is_active:
            raise ValidationError(f"Calendar '{cal.name}' is not active.")

    # --- Site ---

    def assign_site_calendar(
        self,
        site_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = True,
        priority: int = 0,
    ) -> SiteCalendarAssignment:
        require_permission(
            self._user_session, "task.manage", operation_label="assign site calendar"
        )
        assignment = SiteCalendarAssignment.create(
            site_id=site_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )
        self._require_calendar(assignment.calendar_id)
        self._assignment_repo.save_site_assignment(assignment)
        self._session.commit()
        return assignment

    def get_site_calendar(
        self, site_id: str, *, at_date: date | None = None
    ) -> SiteCalendarAssignment | None:
        return self._assignment_repo.get_site_assignment(site_id, at_date=at_date)

    def list_site_assignments(self, site_id: str) -> list[SiteCalendarAssignment]:
        return self._assignment_repo.list_site_assignments(site_id)

    def remove_site_assignment(self, assignment_id: str) -> None:
        require_permission(
            self._user_session, "task.manage", operation_label="remove site calendar assignment"
        )
        self._assignment_repo.delete_site_assignment(assignment_id)
        self._session.commit()

    # --- Department ---

    def assign_department_calendar(
        self,
        department_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = True,
        priority: int = 0,
    ) -> DepartmentCalendarAssignment:
        require_permission(
            self._user_session, "task.manage", operation_label="assign department calendar"
        )
        assignment = DepartmentCalendarAssignment.create(
            department_id=department_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )
        self._require_calendar(assignment.calendar_id)
        self._assignment_repo.save_department_assignment(assignment)
        self._session.commit()
        return assignment

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

    def remove_department_assignment(self, assignment_id: str) -> None:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="remove department calendar assignment",
        )
        self._assignment_repo.delete_department_assignment(assignment_id)
        self._session.commit()

    # --- Employee ---

    def assign_employee_calendar(
        self,
        employee_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = True,
        priority: int = 0,
    ) -> EmployeeCalendarAssignment:
        require_permission(
            self._user_session, "task.manage", operation_label="assign employee calendar"
        )
        assignment = EmployeeCalendarAssignment.create(
            employee_id=employee_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )
        self._require_calendar(assignment.calendar_id)
        self._assignment_repo.save_employee_assignment(assignment)
        self._session.commit()
        return assignment

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

    def remove_employee_assignment(self, assignment_id: str) -> None:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="remove employee calendar assignment",
        )
        self._assignment_repo.delete_employee_assignment(assignment_id)
        self._session.commit()

    # --- Project (PM-side, delegates to PM repo) ---

    def assign_project_calendar(
        self,
        project_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = True,
        priority: int = 0,
    ) -> Any:
        require_permission(
            self._user_session, "task.manage", operation_label="assign project calendar"
        )
        from src.core.modules.project_management.domain.calendar.assignment import (
            ProjectCalendarAssignment,
        )
        assignment = ProjectCalendarAssignment.create(
            project_id=project_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )
        self._require_calendar(assignment.calendar_id)
        self._project_assignment_repo.save(assignment)
        self._session.commit()
        return assignment

    def get_project_calendar(self, project_id: str, *, at_date: date | None = None) -> Any:
        return self._project_assignment_repo.get(project_id, at_date=at_date)

    def remove_project_assignment(self, assignment_id: str) -> None:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="remove project calendar assignment",
        )
        self._project_assignment_repo.delete(assignment_id)
        self._session.commit()

    # --- Resource (PM-side, delegates to PM repo) ---

    def assign_resource_calendar(
        self,
        resource_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = True,
        priority: int = 0,
    ) -> Any:
        require_permission(
            self._user_session, "task.manage", operation_label="assign resource calendar"
        )
        from src.core.modules.project_management.domain.calendar.assignment import (
            ResourceCalendarAssignment,
        )
        assignment = ResourceCalendarAssignment.create(
            resource_id=resource_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )
        self._require_calendar(assignment.calendar_id)
        self._resource_assignment_repo.save(assignment)
        self._session.commit()
        return assignment

    def get_resource_calendar(self, resource_id: str, *, at_date: date | None = None) -> Any:
        return self._resource_assignment_repo.get(resource_id, at_date=at_date)

    def remove_resource_assignment(self, assignment_id: str) -> None:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="remove resource calendar assignment",
        )
        self._resource_assignment_repo.delete(assignment_id)
        self._session.commit()

    # --- Usage summary ---

    def list_calendar_assignments(self, calendar_id: str) -> dict[str, Any]:
        return {
            "sites": self._assignment_repo.list_sites_using_calendar(calendar_id),
            "departments": self._assignment_repo.list_departments_using_calendar(calendar_id),
            "employees": self._assignment_repo.list_employees_using_calendar(calendar_id),
            "projects": self._project_assignment_repo.list_for_calendar(calendar_id),
            "resources": self._resource_assignment_repo.list_for_calendar(calendar_id),
        }


__all__ = ["CalendarAssignmentService"]
