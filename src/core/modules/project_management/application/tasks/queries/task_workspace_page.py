from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.application.tasks.workspace_filters import (
    build_task_workspace_criteria,
)
from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.modules.project_management.contracts.reads.tasks import (
    TaskWorkspaceReader,
    TaskWorkspaceReadPage,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import ConfigurationError
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


class TaskWorkspacePageQueryHandler:
    """Authorized server-page Task workspace read with summary duration mapping."""

    def __init__(
        self,
        *,
        task_workspace_reader: TaskWorkspaceReader | None,
        work_calendar_engine: CalendarProtocol,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
    ) -> None:
        self._task_workspace_reader = task_workspace_reader
        self._work_calendar_engine = work_calendar_engine
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

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
        require_permission(
            self._user_session, "task.read", operation_label="list task workspace"
        )
        normalized_project_id = str(project_id or "").strip() or None
        if normalized_project_id is not None:
            require_project_permission(
                self._user_session,
                normalized_project_id,
                "task.read",
                operation_label="list task workspace",
            )
        if self._task_workspace_reader is None or self._tenant_context_service is None:
            raise ConfigurationError("Task workspace reader is not configured.")

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
        if (
            self._user_session is not None
            and self._user_session.is_project_restricted()
        ):
            allowed_project_ids = tuple(
                sorted(self._user_session.project_ids_for("task.read"))
            )
        criteria = build_task_workspace_criteria(
            project_id=normalized_project_id,
            search_text=search_text,
            status=status,
            priority=priority,
            schedule=schedule,
            milestones_only=milestones_only,
            as_of=as_of or date.today(),  # noqa: DTZ011
        )
        reader = self._task_workspace_reader

        def read_page(page_number: int) -> TaskWorkspaceReadPage:
            return reader.read_page(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                allowed_project_ids=allowed_project_ids,
                criteria=criteria,
                page=page_number,
                page_size=page_request.page_size,
                sort=sort,
            )

        result = read_page(page_request.page)
        normalized_page = normalize_page_for_total(
            page=result.page,
            page_size=result.page_size,
            total=result.filtered_total,
        )
        if normalized_page != result.page:
            result = read_page(normalized_page)
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
            if item.is_summary
            and item.start_date is not None
            and item.end_date is not None
            else item
            for item in result.items
        )
        return replace(result, items=items)


__all__ = ["TaskWorkspacePageQueryHandler"]
