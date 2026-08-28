from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
    TimesheetAssignmentContext,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import ValidationError
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.application.tasks.workspace_filters import (
    build_task_workspace_criteria,
)
from src.core.modules.project_management.contracts.reads.tasks import (
    TaskActivityPage,
    TaskAssignmentReadPage,
    TaskDependencyReadPage,
    TaskWorkspaceReadPage,
    TaskWorkspaceReader,
)
from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.platform.application.security.authorization import get_authorization_engine


class TaskQueryMixin:
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository
    _task_workspace_reader: TaskWorkspaceReader | None

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

    def _require_detail_task(self, task_id: str, operation_label: str) -> Task:
        task = self.get_task(str(task_id or "").strip())
        if task is None:
            raise ValidationError("Task not found.", code="TASK_NOT_FOUND")
        return task

    def query_task_assignments_page(
        self, task_id: str, *, search_text: str = "", response_status: str = "all",
        page: int = 1, page_size: int = 25, sort_key: str = "resourceName",
        sort_direction: str = "asc",
    ) -> TaskAssignmentReadPage:
        task = self._require_detail_task(task_id, "view task assignments")
        require_project_permission(self._user_session, task.project_id, "task.read",
                                   operation_label="view task assignments")
        if self._task_workspace_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Task workspace reader is not configured.")
        request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(key=sort_key, direction=sort_direction,
            allowed_keys={"resourceName", "resourceCode", "role", "allocationPercent",
                          "plannedHours", "actualHours", "remainingHours", "responseStatus"},
            default_key="resourceName")
        normalized_status = str(response_status or "all").strip().lower()
        status = normalized_status if normalized_status in {"pending", "accepted", "declined"} else None
        scope = self._tenant_context_service.require_active_scope_ids(operation_label="view task assignments")
        kwargs = dict(tenant_id=scope.tenant_id, organization_id=scope.organization_id,
                      task_id=task.id, search_text=str(search_text or "").strip(),
                      response_status=status, page=request.page, page_size=request.page_size, sort=sort)
        result = self._task_workspace_reader.read_assignments_page(**kwargs)
        normalized_page = normalize_page_for_total(page=result.page, page_size=result.page_size,
                                                   total=result.filtered_total)
        if normalized_page != result.page:
            kwargs["page"] = normalized_page
            result = self._task_workspace_reader.read_assignments_page(**kwargs)
        engine = get_authorization_engine()
        can_manage = engine.has_permission(
            self._user_session, "task.manage"
        ) and engine.has_scope_permission(
            self._user_session, "project", task.project_id, "task.manage"
        )
        principal = self._user_session.principal if self._user_session is not None else None
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
        self, task_id: str, *, search_text: str = "", direction: str = "all",
        dependency_type: str = "all", page: int = 1, page_size: int = 25,
        sort_key: str = "linkedTask", sort_direction: str = "asc",
    ) -> TaskDependencyReadPage:
        task = self._require_detail_task(task_id, "view task dependencies")
        require_project_permission(self._user_session, task.project_id, "task.read",
                                   operation_label="view task dependencies")
        if self._task_workspace_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Task workspace reader is not configured.")
        request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(key=sort_key, direction=sort_direction,
            allowed_keys={"direction", "linkedTask", "taskCode", "dependencyType", "lagDays",
                          "startDate", "endDate", "statusLabel"}, default_key="linkedTask")
        normalized_direction = str(direction or "all").strip().upper()
        if normalized_direction not in {"ALL", "PREDECESSOR", "SUCCESSOR"}: normalized_direction = "ALL"
        normalized_type = str(dependency_type or "all").strip().upper()
        dep_type = normalized_type if normalized_type in {"FS", "FF", "SS", "SF"} else None
        scope = self._tenant_context_service.require_active_scope_ids(operation_label="view task dependencies")
        kwargs = dict(tenant_id=scope.tenant_id, organization_id=scope.organization_id,
                      task_id=task.id, search_text=str(search_text or "").strip(),
                      direction=normalized_direction, dependency_type=dep_type,
                      page=request.page, page_size=request.page_size, sort=sort)
        result = self._task_workspace_reader.read_dependencies_page(**kwargs)
        normalized_page = normalize_page_for_total(page=result.page, page_size=result.page_size,
                                                   total=result.filtered_total)
        if normalized_page != result.page:
            kwargs["page"] = normalized_page
            result = self._task_workspace_reader.read_dependencies_page(**kwargs)
        return result

    def query_task_activity_page(
        self, task_id: str, *, search_text: str = "", category: str = "all",
        page: int = 1, page_size: int = 25,
    ) -> TaskActivityPage:
        task = self._require_detail_task(task_id, "view task activity")
        require_project_permission(self._user_session, task.project_id, "task.read",
                                   operation_label="view task activity")
        if self._task_workspace_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Task workspace reader is not configured.")
        request = PageRequest(page=page, page_size=page_size)
        normalized_category = str(category or "all").strip().lower()
        if normalized_category not in {"all", "task", "assignments"}: normalized_category = "all"
        scope = self._tenant_context_service.require_active_scope_ids(operation_label="view task activity")
        kwargs = dict(tenant_id=scope.tenant_id, organization_id=scope.organization_id,
                      task_id=task.id, search_text=str(search_text or "").strip(),
                      category=normalized_category, page=request.page, page_size=request.page_size)
        result = self._task_workspace_reader.read_activity_page(**kwargs)
        normalized_page = normalize_page_for_total(page=result.page, page_size=result.page_size,
                                                   total=result.filtered_total)
        if normalized_page != result.page:
            kwargs["page"] = normalized_page
            result = self._task_workspace_reader.read_activity_page(**kwargs)
        return result

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        require_permission(self._user_session, "task.read", operation_label="list project tasks")
        require_project_permission(
            self._user_session,
            project_id,
            "task.read",
            operation_label="list project tasks",
        )
        return self._task_repo.list_by_project(project_id)

    def query_workspace_page(
        self,
        *,
        project_id: str | None = None,
        resource_id: str | None = None,
        search_text: str = "",
        status: str = "all",
        priority: str = "all",
        schedule: str = "all",
        milestones_only: bool = False,
        page: int = 1,
        page_size: int = 25,
        as_of: date | None = None,
        sort_key: str = "wbsCode",
        sort_direction: str = "asc",
    ) -> TaskWorkspaceReadPage:
        require_permission(self._user_session, "task.read", operation_label="list task workspace")
        normalized_project_id = str(project_id or "").strip() or None
        if normalized_project_id is not None:
            require_project_permission(
                self._user_session,
                normalized_project_id,
                "task.read",
                operation_label="list task workspace",
            )
        if self._task_workspace_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Task workspace reader is not configured.")

        page_request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={
                "wbsCode",
                "title",
                "taskName",
                "statusLabel",
                "projectName",
                "priorityLabel",
                "priority",
                "startDateLabel",
                "startDate",
                "endDateLabel",
                "endDate",
                "progressValue",
            },
            default_key="wbsCode",
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="list task workspace"
        )
        allowed_project_ids: tuple[str, ...] | None = None
        if self._user_session is not None and self._user_session.is_project_restricted():
            allowed_project_ids = tuple(sorted(self._user_session.project_ids_for("task.read")))
        criteria = build_task_workspace_criteria(
            project_id=normalized_project_id,
            search_text=search_text,
            status=status,
            priority=priority,
            schedule=schedule,
            milestones_only=milestones_only,
            as_of=as_of or date.today(),
        )
        read_kwargs = dict(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            allowed_project_ids=allowed_project_ids,
            criteria=criteria,
            page=page_request.page,
            page_size=page_request.page_size,
            sort=sort,
        )
        result = self._task_workspace_reader.read_page(**read_kwargs)
        normalized_page = normalize_page_for_total(
            page=result.page,
            page_size=result.page_size,
            total=result.filtered_total,
        )
        if normalized_page != result.page:
            read_kwargs["page"] = normalized_page
            result = self._task_workspace_reader.read_page(**read_kwargs)
        items = tuple(
            replace(
                item,
                duration_days=max(
                    0,
                    int(
                        self._work_calendar_engine.working_days_between(
                            item.start_date,
                            item.end_date,
                        )
                    ),
                ),
            )
            if item.is_summary and item.start_date is not None and item.end_date is not None
            else item
            for item in result.items
        )
        return replace(result, items=items)

    def list_tasks_for_resource(self, resource_id: str) -> list[Task]:
        require_permission(self._user_session, "task.read", operation_label="list resource tasks")
        assignments = self._assignment_repo.list_by_resource(resource_id)
        task_ids = {assignment.task_id for assignment in assignments}
        tasks: list[Task] = []
        for task_id in task_ids:
            task = self._task_repo.get(task_id)
            if task and self._user_session.has_project_permission(task.project_id, "task.read"):
                tasks.append(task)
        return tasks

    def list_assignments_for_resource(self, resource_id: str) -> list[TaskAssignment]:
        require_permission(
            self._user_session,
            "task.read",
            operation_label="list resource assignments",
        )
        assignments = self._assignment_repo.list_by_resource(resource_id)
        allowed: list[TaskAssignment] = []
        for assignment in assignments:
            task = self._task_repo.get(assignment.task_id)
            if task and self._user_session.has_project_permission(task.project_id, "task.read"):
                allowed.append(assignment)
        return allowed

    def list_assignments_for_tasks(self, task_ids: list[str]) -> list[TaskAssignment]:
        require_permission(self._user_session, "task.read", operation_label="list task assignments")
        if not task_ids:
            return []
        allowed_ids: list[str] = []
        for task_id in task_ids:
            task = self._task_repo.get(task_id)
            if task is None:
                continue
            if self._user_session.has_project_permission(task.project_id, "task.read"):
                allowed_ids.append(task_id)
        return self._assignment_repo.list_by_tasks(allowed_ids)

    def list_timesheet_assignment_contexts(
        self,
        *,
        project_id: str | None = None,
        resource_id: str | None = None,
    ) -> list[TimesheetAssignmentContext]:
        require_permission(
            self._user_session,
            "task.read",
            operation_label="list timesheet assignments",
        )
        normalized_project_id = str(project_id or "").strip() or None
        if normalized_project_id is not None:
            require_project_permission(
                self._user_session,
                normalized_project_id,
                "task.read",
                operation_label="list timesheet assignments",
            )
        rows = self._assignment_repo.list_timesheet_contexts(
            project_id=normalized_project_id,
            resource_id=str(resource_id or "").strip() or None,
        )
        if normalized_project_id is not None:
            return rows
        return [
            row
            for row in rows
            if self._user_session.has_project_permission(row.project_id, "task.read")
        ]

    def get_timesheet_assignment_context(
        self,
        assignment_id: str,
    ) -> TimesheetAssignmentContext | None:
        require_permission(
            self._user_session,
            "task.read",
            operation_label="view timesheet assignment",
        )
        rows = self._assignment_repo.list_timesheet_contexts(
            assignment_id=str(assignment_id or "").strip()
        )
        if not rows:
            return None
        row = rows[0]
        require_project_permission(
            self._user_session,
            row.project_id,
            "task.read",
            operation_label="view timesheet assignment",
        )
        return row

    def query_tasks(
        self,
        project_id: str | None = None,
        status: TaskStatus | None = None,
        resource_id: str | None = None,
        start_from: date | None = None,
        start_to: date | None = None,
        end_from: date | None = None,
        end_to: date | None = None,
    ) -> list[Task]:
        require_permission(self._user_session, "task.read", operation_label="query tasks")
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "task.read",
                operation_label="query tasks",
            )
            tasks = self._task_repo.list_by_project(project_id)
        else:
            raise ValidationError("project_id is required for query_tasks currently.")

        if status:
            tasks = [task for task in tasks if task.status == status]

        if start_from:
            tasks = [task for task in tasks if task.start_date and task.start_date >= start_from]
        if start_to:
            tasks = [task for task in tasks if task.start_date and task.start_date <= start_to]
        if end_from:
            tasks = [task for task in tasks if task.end_date and task.end_date >= end_from]
        if end_to:
            tasks = [task for task in tasks if task.end_date and task.end_date <= end_to]

        if resource_id:
            assignments = self._assignment_repo.list_by_resource(resource_id)
            task_ids = {assignment.task_id for assignment in assignments}
            tasks = [task for task in tasks if task.id in task_ids]

        return tasks


__all__ = ["TaskQueryMixin"]
