from __future__ import annotations

from datetime import UTC, datetime

from src.core.modules.project_management.access.scope_permissions import (
    require_any_project_permission,
    require_project_permission,
)
from src.core.modules.project_management.domain.resources import (
    TimeReportingEligibilityPolicy,
)
from src.core.platform.application.security.authorization import (
    get_authorization_engine,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.application.time_management.time import TimesheetSupport
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.interface.time_management.time.contracts import (
    WorkAllocationRecord,
    WorkOwnerRecord,
)
from src.core.platform.contract.repositories.master_data.employee.contracts import (
    EmployeeRepository,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    WorkResourceRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.time_management.time import TimeEntry


class ProjectTimesheetAccessPolicy:
    """PM's Time access policy: project-scoped, owner-aware Time authorization.

    Implements the Platform `TimeAccessPolicy` port. Closes the gap where a
    user with only the global time.manage capability could otherwise write
    time against any project's tasks, and restricts project-scoped reviewers
    to periods whose every entry is in their projects.
    """

    def __init__(
        self,
        *,
        user_session: UserSessionContext | None,
        resource_repo: WorkResourceRepository,
        employee_repo: EmployeeRepository | None,
        support: TimesheetSupport,
    ) -> None:
        self._user_session = user_session
        self._resource_repo = resource_repo
        self._employee_repo = employee_repo
        self._support = support

    def require_read_permission(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("time.read", "task.read"),
            operation_label=operation_label,
        )

    def require_manage_permission(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            (
                "time.manage",
                "task.manage",
                "timesheet.edit_own",
                "timesheet.edit_team",
                "timesheet.edit_all",
            ),
            operation_label=operation_label,
        )

    def require_project_scope(
        self,
        *,
        work_allocation: WorkAllocationRecord | None,
        work_owner: WorkOwnerRecord | None,
        operation_label: str,
    ) -> None:
        engine = get_authorization_engine()
        can_manage_shared_time = engine.has_permission(
            self._user_session, "time.manage"
        ) or engine.has_permission(
            self._user_session, "task.manage"
        ) or engine.has_permission(
            self._user_session, "timesheet.edit_team"
        ) or engine.has_permission(
            self._user_session, "timesheet.edit_all"
        ) or engine.has_permission(
            self._user_session, "timesheet.submit_on_behalf"
        )
        resource_id = str(getattr(work_allocation, "resource_id", "") or "").strip()
        resource = self._resource_repo.get(resource_id)
        if resource is None or not TimeReportingEligibilityPolicy.can_report_time(resource):
            raise BusinessRuleError(
                "The selected Resource is not eligible to report time.",
                code="RESOURCE_TIME_REPORTING_INELIGIBLE",
            )
        if not can_manage_shared_time:
            require_any_permission(
                self._user_session,
                ("timesheet.submit",),
                operation_label=operation_label,
            )
            self._require_current_principal_resource(resource_id)
        project_id = self._support.resolve_entry_project_id(
            work_allocation=work_allocation, work_owner=work_owner
        )
        if not project_id:
            return
        require_any_project_permission(
            self._user_session,
            project_id,
            (
                ("time.manage", "task.manage")
                if can_manage_shared_time
                else ("timesheet.submit", "task.read")
            ),
            operation_label=operation_label,
        )

    def require_review_scope(self, permission_code: str, entries: list[TimeEntry]) -> None:
        session = self._user_session
        if session is None or not session.is_project_restricted():
            return
        project_ids = self._support.project_ids_for_entries(entries)
        if not project_ids:
            raise BusinessRuleError(
                "Project-scoped reviewers cannot decide an unscoped timesheet period.",
                code="PERMISSION_DENIED",
            )
        for project_id in project_ids:
            require_project_permission(
                session,
                project_id,
                permission_code,
                operation_label="review timesheet period",
            )

    def _require_current_principal_resource(self, resource_id: str) -> None:
        resource = self._resource_repo.get(resource_id)
        employee_id = str(getattr(resource, "employee_id", "") or "").strip()
        employee = self._employee_repo.get(employee_id) if employee_id and self._employee_repo else None
        principal_user_id = str(
            getattr(getattr(self._user_session, "principal", None), "user_id", "") or ""
        ).strip()
        if not employee or str(getattr(employee, "user_id", "") or "").strip() != principal_user_id:
            raise BusinessRuleError(
                "Time entries can only be changed by their owner.",
                code="TIMESHEET_OWNER_SCOPE_DENIED",
            )


def build_task_assignment_hours_synced_event(
    *,
    tenant_id: str,
    organization_id: str,
    project_id: str,
    work_allocation: WorkAllocationRecord,
) -> object:
    """PM's fact for a TimeEntry-driven TaskAssignment `hours_logged` change."""
    # Lazy import: application.tasks imports this package (TaskTimeEntryHandler).
    from src.core.modules.project_management.application.tasks.task_events import (
        TaskAssignmentChanged,
        TaskAssignmentChangeType,
    )

    return TaskAssignmentChanged(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=project_id,
        task_id=getattr(work_allocation, "task_id", "") or "",
        assignment_id=work_allocation.id,
        resource_id=getattr(work_allocation, "resource_id", "") or "",
        change_type=TaskAssignmentChangeType.HOURS_LOGGED_CHANGED,
        occurred_at=datetime.now(UTC),
    )


__all__ = ["ProjectTimesheetAccessPolicy", "build_task_assignment_hours_synced_event"]
