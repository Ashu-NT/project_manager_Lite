from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.modules.project_management.contracts.reads.resources import (
    ResourceActivityReadPage,
    ResourceActivityReader,
    ResourceAssignmentReadPage,
    ResourceAssignmentsReader,
    ResourceProjectReadPage,
    ResourceProjectsReader,
)
from src.core.modules.project_management.domain.enums import ProjectStatus, TaskStatus
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class ResourceContextQueryMixin:
    _resource_projects_reader: ResourceProjectsReader | None
    _resource_assignments_reader: ResourceAssignmentsReader | None
    _resource_activity_reader: ResourceActivityReader | None

    def _project_scope_for(self, permission_code: str) -> tuple[str, ...] | None:
        session = self._user_session
        if session is None or not session.has_permission(permission_code):
            return ()
        if session.is_project_restricted():
            return tuple(sorted(session.project_ids_for(permission_code)))
        return None

    def _active_scope(self, operation_label: str):
        if self._tenant_context_service is None:
            raise RuntimeError("Resource context reader scope is not configured.")
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    @staticmethod
    def _page_request(page: int, page_size: int) -> PageRequest:
        return PageRequest(page=page, page_size=page_size)

    def query_resource_projects_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        active: bool | None = None,
        status: ProjectStatus | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "projectName",
        sort_direction: str = "asc",
    ) -> ResourceProjectReadPage:
        require_permission(
            self._user_session, "resource.read", operation_label="view resource projects"
        )
        require_permission(
            self._user_session, "project.read", operation_label="view resource projects"
        )
        if self._resource_projects_reader is None:
            raise RuntimeError("Resource Projects reader is not configured.")
        request = self._page_request(page, page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={
                "projectName",
                "projectCode",
                "statusLabel",
                "plannedHours",
                "startDate",
                "endDate",
            },
            default_key="projectName",
        )
        scope = self._active_scope("view resource projects")
        kwargs = dict(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            resource_id=str(resource_id or "").strip(),
            allowed_project_ids=self._project_scope_for("project.read"),
            search_text=str(search_text or "").strip(),
            active=active,
            status=status,
            page=request.page,
            page_size=request.page_size,
            sort=sort,
        )
        result = self._resource_projects_reader.read_projects_page(**kwargs)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.filtered_total
        )
        if normalized_page != result.page:
            kwargs["page"] = normalized_page
            result = self._resource_projects_reader.read_projects_page(**kwargs)
        return result

    def query_resource_assignments_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        project_id: str | None = None,
        task_status: TaskStatus | None = None,
        assignment_status: str | None = None,
        lifecycle: str = "current",
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "scheduledStart",
        sort_direction: str = "asc",
    ) -> ResourceAssignmentReadPage:
        require_permission(
            self._user_session, "resource.read", operation_label="view resource assignments"
        )
        require_permission(
            self._user_session, "task.read", operation_label="view resource assignments"
        )
        if self._resource_assignments_reader is None:
            raise RuntimeError("Resource Assignments reader is not configured.")
        request = self._page_request(page, page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={
                "projectName",
                "taskName",
                "scheduledStart",
                "scheduledFinish",
                "plannedHours",
                "allocationPercent",
                "actualHours",
                "statusLabel",
            },
            default_key="scheduledStart",
        )
        normalized_lifecycle = str(lifecycle or "current").strip().lower()
        if normalized_lifecycle not in {"all", "current", "history"}:
            normalized_lifecycle = "current"
        normalized_assignment_status = str(assignment_status or "").strip().lower() or None
        scope = self._active_scope("view resource assignments")
        kwargs = dict(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            resource_id=str(resource_id or "").strip(),
            allowed_project_ids=self._project_scope_for("task.read"),
            search_text=str(search_text or "").strip(),
            project_id=str(project_id or "").strip() or None,
            task_status=task_status,
            assignment_status=normalized_assignment_status,
            lifecycle=normalized_lifecycle,
            start_date=start_date,
            end_date=end_date,
            page=request.page,
            page_size=request.page_size,
            sort=sort,
        )
        result = self._resource_assignments_reader.read_assignments_page(**kwargs)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.filtered_total
        )
        if normalized_page != result.page:
            kwargs["page"] = normalized_page
            result = self._resource_assignments_reader.read_assignments_page(**kwargs)
        return result

    def query_resource_activity_page(
        self,
        resource_id: str,
        *,
        category: str = "all",
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> ResourceActivityReadPage:
        require_permission(
            self._user_session, "resource.read", operation_label="view resource activity"
        )
        if self._resource_activity_reader is None:
            raise RuntimeError("Resource Activity reader is not configured.")
        request = self._page_request(page, page_size)
        normalized_category = str(category or "all").strip().lower()
        if normalized_category not in {
            "all",
            "resource",
            "capability",
            "projects",
            "assignments",
            "work",
        }:
            normalized_category = "all"
        scope = self._active_scope("view resource activity")
        kwargs = dict(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            resource_id=str(resource_id or "").strip(),
            allowed_project_ids=self._project_scope_for("project.read"),
            allowed_task_project_ids=self._project_scope_for("task.read"),
            category=normalized_category,
            start_date=start_date,
            end_date=end_date,
            page=request.page,
            page_size=request.page_size,
        )
        result = self._resource_activity_reader.read_activity_page(**kwargs)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.filtered_total
        )
        if normalized_page != result.page:
            kwargs["page"] = normalized_page
            result = self._resource_activity_reader.read_activity_page(**kwargs)
        return result


__all__ = ["ResourceContextQueryMixin"]
