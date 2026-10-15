from __future__ import annotations

from dataclasses import replace

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.modules.project_management.contracts.reads.tasks import (
    TaskActivityPage,
    TaskAssignmentReadPage,
    TaskDependencyReadPage,
    TaskWorkspaceReader,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.platform.application.security.authorization import (
    get_authorization_engine,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import ConfigurationError, ValidationError
from src.core.platform.domain.security.auth.session import UserSessionContext


class TaskDetailPageQueryHandler(ProjectManagementModuleGuardMixin):
    """Scoped, server-paged Task Detail reads and row capabilities."""

    def __init__(
        self,
        *,
        module_catalog_service=None,
        task_repo: TaskRepository,
        task_workspace_reader: TaskWorkspaceReader | None,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
    ) -> None:
        self._module_catalog_service = module_catalog_service
        self._task_repo = task_repo
        self._task_workspace_reader = task_workspace_reader
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def get_task(self, task_id: str) -> Task | None:
        require_permission(self._user_session, "task.read", operation_label="view task")
        task = self._task_repo.get(task_id)
        if task is None:
            return None
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="view task",
        )
        return task

    def _require_detail_task(self, task_id: str) -> Task:
        task = self.get_task(str(task_id or "").strip())
        if task is None:
            raise ValidationError("Task not found.", code="TASK_NOT_FOUND")
        return task

    def list_tasks_by_ids(self, task_ids: list[str]) -> list[Task]:
        require_permission(self._user_session, "task.read", operation_label="view task")
        ids = list(dict.fromkeys(task_ids))
        if not ids:
            return []
        tasks = self._task_repo.list_by_ids(ids)
        for task in tasks:
            require_project_permission(
                self._user_session, task.project_id, "task.read", operation_label="view task"
            )
        return tasks

    def query_task_assignments_page(
        self,
        task_id: str,
        *,
        search_text: str = "",
        response_status: str = "all",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "resourceName",
        sort_direction: str = "asc",
    ) -> TaskAssignmentReadPage:
        task = self._require_detail_task(task_id)
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="view task assignments",
        )
        if self._task_workspace_reader is None or self._tenant_context_service is None:
            raise ConfigurationError("Task workspace reader is not configured.")
        request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={
                "resourceName",
                "resourceCode",
                "role",
                "allocationPercent",
                "plannedHours",
                "actualHours",
                "remainingHours",
                "responseStatus",
            },
            default_key="resourceName",
        )
        normalized_status = str(response_status or "all").strip().lower()
        status = (
            normalized_status
            if normalized_status in {"pending", "accepted", "declined"}
            else None
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view task assignments"
        )
        reader = self._task_workspace_reader

        def read_page(page_number: int) -> TaskAssignmentReadPage:
            return reader.read_assignments_page(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                task_id=task.id,
                search_text=str(search_text or "").strip(),
                response_status=status,
                page=page_number,
                page_size=request.page_size,
                sort=sort,
            )

        result = read_page(request.page)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.filtered_total
        )
        if normalized_page != result.page:
            result = read_page(normalized_page)
        engine = get_authorization_engine()
        can_manage = engine.has_permission(
            self._user_session, "task.manage"
        ) and engine.has_scope_permission(
            self._user_session, "project", task.project_id, "task.manage"
        )
        principal = (
            self._user_session.principal if self._user_session is not None else None
        )
        principal_user_id = str(getattr(principal, "user_id", "") or "").strip()
        return replace(
            result,
            items=tuple(
                replace(
                    item,
                    can_manage=bool(can_manage),
                    can_accept=bool(
                        principal_user_id
                        and principal_user_id == str(item.assignee_user_id or "")
                        and item.response_status == "pending"
                    ),
                    can_decline=bool(
                        principal_user_id
                        and principal_user_id == str(item.assignee_user_id or "")
                        and item.response_status == "pending"
                    ),
                )
                for item in result.items
            ),
        )

    def query_task_dependencies_page(
        self,
        task_id: str,
        *,
        search_text: str = "",
        direction: str = "all",
        dependency_type: str = "all",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "linkedTask",
        sort_direction: str = "asc",
    ) -> TaskDependencyReadPage:
        task = self._require_detail_task(task_id)
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="view task dependencies",
        )
        if self._task_workspace_reader is None or self._tenant_context_service is None:
            raise ConfigurationError("Task workspace reader is not configured.")
        request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={
                "direction",
                "linkedTask",
                "taskCode",
                "dependencyType",
                "lagDays",
                "startDate",
                "endDate",
                "statusLabel",
            },
            default_key="linkedTask",
        )
        normalized_direction = str(direction or "all").strip().upper()
        if normalized_direction not in {"ALL", "PREDECESSOR", "SUCCESSOR"}:
            normalized_direction = "ALL"
        normalized_type = str(dependency_type or "all").strip().upper()
        dep_type = (
            normalized_type if normalized_type in {"FS", "FF", "SS", "SF"} else None
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view task dependencies"
        )
        reader = self._task_workspace_reader

        def read_page(page_number: int) -> TaskDependencyReadPage:
            return reader.read_dependencies_page(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                task_id=task.id,
                search_text=str(search_text or "").strip(),
                direction=normalized_direction,
                dependency_type=dep_type,
                page=page_number,
                page_size=request.page_size,
                sort=sort,
            )

        result = read_page(request.page)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.filtered_total
        )
        if normalized_page != result.page:
            result = read_page(normalized_page)
        return result

    def query_task_activity_page(
        self,
        task_id: str,
        *,
        search_text: str = "",
        category: str = "all",
        page: int = 1,
        page_size: int = 25,
    ) -> TaskActivityPage:
        task = self._require_detail_task(task_id)
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="view task activity",
        )
        if self._task_workspace_reader is None or self._tenant_context_service is None:
            raise ConfigurationError("Task workspace reader is not configured.")
        request = PageRequest(page=page, page_size=page_size)
        normalized_category = str(category or "all").strip().lower()
        if normalized_category not in {"all", "task", "assignments"}:
            normalized_category = "all"
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view task activity"
        )
        reader = self._task_workspace_reader

        def read_page(page_number: int) -> TaskActivityPage:
            return reader.read_activity_page(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                task_id=task.id,
                search_text=str(search_text or "").strip(),
                category=normalized_category,
                page=page_number,
                page_size=request.page_size,
            )

        result = read_page(request.page)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.filtered_total
        )
        if normalized_page != result.page:
            result = read_page(normalized_page)
        return result


__all__ = ["TaskDetailPageQueryHandler"]
