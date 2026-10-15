"""Calendar calendar assignment operations."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.time_management.calendar._input import (
    parse_date as _parse_date,
)
from src.core.platform.application.time_management.calendar.assignment.dto.commands.calendar_assignments import (
    DeptCalendarAssignCommand,
    EmpCalendarAssignCommand,
    ProjectCalendarAssignCommand,
    ResourceCalendarAssignCommand,
    SiteCalendarAssignCommand,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.contract.port.time_management.calendar.external_assignment_port import (
    ExternalCalendarAssignment,
    ProjectCalendarAssignmentPort,
    ResourceCalendarAssignmentPort,
)
from src.core.platform.contract.repositories.time_management.calendar.contracts import (
    CalendarAssignmentRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    DepartmentCalendarAssignment,
    EmployeeCalendarAssignment,
    PlatformCalendar,
    SiteCalendarAssignment,
)
from src.core.shared.activity import record_activity

ProjectAssignmentT = TypeVar("ProjectAssignmentT", bound=ExternalCalendarAssignment)
ResourceAssignmentT = TypeVar("ResourceAssignmentT", bound=ExternalCalendarAssignment)


class CalendarAssignmentCommandHandler(
    Generic[ProjectAssignmentT, ResourceAssignmentT]
):
    """Transactional writes for calendar assignment."""

    def __init__(
        self,
        *,
        session: Session,
        calendar_repo: PlatformCalendarRepository,
        assignment_repo: CalendarAssignmentRepository,
        project_assignment_repo: ProjectCalendarAssignmentPort[ProjectAssignmentT],
        resource_assignment_repo: ResourceCalendarAssignmentPort[ResourceAssignmentT],
        user_session: Any = None,
        activity_service: Any = None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._assignment_repo = assignment_repo
        self._project_assignment_repo = project_assignment_repo
        self._resource_assignment_repo = resource_assignment_repo
        self._user_session = user_session
        self._activity_service = activity_service

    def _require_calendar(self, calendar_id: str) -> PlatformCalendar:
        cal = self._calendar_repo.get(calendar_id)
        if cal is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")
        if not cal.is_active:
            raise ValidationError(f"Calendar '{cal.name}' is not active.")
        return cal

    def _record_assignment_activity(
        self,
        *,
        action: str,
        target_entity_type: str,
        target_entity_id: str,
        calendar: PlatformCalendar,
        message: str,
    ) -> None:
        # Dual-recorded per the ownership rule: visible on the target
        # entity's own Activity feed (what most users look at first) AND on
        # the Calendar's own Activity (useful for understanding usage/
        # impact before editing a heavily-assigned calendar) -- never a
        # third, independent feed, and never duplicated beyond these two.
        record_activity(
            self,
            action=action,
            entity_type=target_entity_type,
            entity_id=target_entity_id,
            module="platform",
            organization_id=calendar.organization_id,
            message=message,
            icon="calendar",
            commit=False,
        )
        record_activity(
            self,
            action=action,
            entity_type="calendar",
            entity_id=calendar.id,
            module="platform",
            organization_id=calendar.organization_id,
            message=message,
            icon="calendar",
            commit=False,
        )

    # --- Site ---

    def assign_site_calendar(
        self, command: SiteCalendarAssignCommand
    ) -> SiteCalendarAssignment:
        site_id = command.site_id
        calendar_id = command.calendar_id
        effective_from = _parse_date(command.effective_from)
        effective_to = _parse_date(command.effective_to)
        is_default = command.is_default
        priority = command.priority

        require_permission(
            self._user_session,
            "calendar.manage",
            operation_label="assign site calendar",
        )
        require_permission(
            self._user_session, "site.manage", operation_label="assign site calendar"
        )
        assignment = SiteCalendarAssignment.create(
            site_id=site_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )
        calendar = self._require_calendar(assignment.calendar_id)
        self._assignment_repo.save_site_assignment(assignment)
        self._record_assignment_activity(
            action="site.calendar_assigned",
            target_entity_type="site",
            target_entity_id=site_id,
            calendar=calendar,
            message=f"Calendar override assigned — {calendar.name}",
        )
        self._session.commit()
        return assignment

    def remove_site_assignment(self, assignment_id: str) -> None:
        require_permission(
            self._user_session,
            "calendar.manage",
            operation_label="remove site calendar assignment",
        )
        require_permission(
            self._user_session,
            "site.manage",
            operation_label="remove site calendar assignment",
        )
        deleted = self._assignment_repo.delete_site_assignment(assignment_id)
        if deleted is not None:
            calendar = self._calendar_repo.get(deleted.calendar_id)
            if calendar is not None:
                self._record_assignment_activity(
                    action="site.calendar_unassigned",
                    target_entity_type="site",
                    target_entity_id=deleted.site_id,
                    calendar=calendar,
                    message=f"Calendar override removed — {calendar.name}",
                )
        self._session.commit()

    # --- Department ---

    def assign_department_calendar(
        self, command: DeptCalendarAssignCommand
    ) -> DepartmentCalendarAssignment:
        department_id = command.department_id
        calendar_id = command.calendar_id
        effective_from = _parse_date(command.effective_from)
        effective_to = _parse_date(command.effective_to)
        is_default = command.is_default
        priority = command.priority

        require_permission(
            self._user_session,
            "calendar.manage",
            operation_label="assign department calendar",
        )
        require_permission(
            self._user_session,
            "department.manage",
            operation_label="assign department calendar",
        )
        assignment = DepartmentCalendarAssignment.create(
            department_id=department_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )
        calendar = self._require_calendar(assignment.calendar_id)
        self._assignment_repo.save_department_assignment(assignment)
        self._record_assignment_activity(
            action="department.calendar_assigned",
            target_entity_type="department",
            target_entity_id=department_id,
            calendar=calendar,
            message=f"Calendar override assigned — {calendar.name}",
        )
        self._session.commit()
        return assignment

    def remove_department_assignment(self, assignment_id: str) -> None:
        require_permission(
            self._user_session,
            "calendar.manage",
            operation_label="remove department calendar assignment",
        )
        require_permission(
            self._user_session,
            "department.manage",
            operation_label="remove department calendar assignment",
        )
        deleted = self._assignment_repo.delete_department_assignment(assignment_id)
        if deleted is not None:
            calendar = self._calendar_repo.get(deleted.calendar_id)
            if calendar is not None:
                self._record_assignment_activity(
                    action="department.calendar_unassigned",
                    target_entity_type="department",
                    target_entity_id=deleted.department_id,
                    calendar=calendar,
                    message=f"Calendar override removed — {calendar.name}",
                )
        self._session.commit()

    # --- Employee ---

    def assign_employee_calendar(
        self, command: EmpCalendarAssignCommand
    ) -> EmployeeCalendarAssignment:
        employee_id = command.employee_id
        calendar_id = command.calendar_id
        effective_from = _parse_date(command.effective_from)
        effective_to = _parse_date(command.effective_to)
        is_default = command.is_default
        priority = command.priority

        require_permission(
            self._user_session,
            "calendar.manage",
            operation_label="assign employee calendar",
        )
        require_permission(
            self._user_session,
            "employee.manage",
            operation_label="assign employee calendar",
        )
        assignment = EmployeeCalendarAssignment.create(
            employee_id=employee_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )
        calendar = self._require_calendar(assignment.calendar_id)
        self._assignment_repo.save_employee_assignment(assignment)
        self._record_assignment_activity(
            action="employee.calendar_assigned",
            target_entity_type="employee",
            target_entity_id=employee_id,
            calendar=calendar,
            message=f"Calendar override assigned — {calendar.name}",
        )
        self._session.commit()
        return assignment

    def remove_employee_assignment(self, assignment_id: str) -> None:
        require_permission(
            self._user_session,
            "calendar.manage",
            operation_label="remove employee calendar assignment",
        )
        require_permission(
            self._user_session,
            "employee.manage",
            operation_label="remove employee calendar assignment",
        )
        deleted = self._assignment_repo.delete_employee_assignment(assignment_id)
        if deleted is not None:
            calendar = self._calendar_repo.get(deleted.calendar_id)
            if calendar is not None:
                self._record_assignment_activity(
                    action="employee.calendar_unassigned",
                    target_entity_type="employee",
                    target_entity_id=deleted.employee_id,
                    calendar=calendar,
                    message=f"Calendar override removed — {calendar.name}",
                )
        self._session.commit()

    # --- Project (PM-side, delegates to PM repo) ---

    def assign_project_calendar(
        self, command: ProjectCalendarAssignCommand
    ) -> ProjectAssignmentT:
        project_id = command.project_id
        calendar_id = command.calendar_id
        effective_from = _parse_date(command.effective_from)
        effective_to = _parse_date(command.effective_to)
        is_default = command.is_default
        priority = command.priority

        require_permission(
            self._user_session, "task.manage", operation_label="assign project calendar"
        )
        assignment = self._project_assignment_repo.create(
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
        self, command: ResourceCalendarAssignCommand
    ) -> ResourceAssignmentT:
        resource_id = command.resource_id
        calendar_id = command.calendar_id
        effective_from = _parse_date(command.effective_from)
        effective_to = _parse_date(command.effective_to)
        is_default = command.is_default
        priority = command.priority

        require_permission(
            self._user_session,
            "task.manage",
            operation_label="assign resource calendar",
        )
        assignment = self._resource_assignment_repo.create(
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

    def remove_resource_assignment(self, assignment_id: str) -> None:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="remove resource calendar assignment",
        )
        self._resource_assignment_repo.delete(assignment_id)
        self._session.commit()

    # --- Usage summary ---


__all__ = ["CalendarAssignmentCommandHandler"]
