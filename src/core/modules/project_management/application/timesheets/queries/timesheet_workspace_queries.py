from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.application.timesheets.timesheet_workspace_scope import (
    TimesheetWorkspaceScope,
)
from src.core.modules.project_management.contracts.reads import (
    ReadSort,
    ReadSortDirection,
)
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetEntryCriteria,
    TimesheetEntryReadPage,
    TimesheetHistoryCriteria,
    TimesheetHistoryReadPage,
    TimesheetPeriodFact,
    TimesheetResourceReadPage,
    TimesheetResourceSelectorCriteria,
    TimesheetScope,
    TimesheetWorkspaceAccessFact,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


class TimesheetWorkspaceQueryHandler(ProjectManagementModuleGuardMixin):
    """Resource-scoped Timesheet workspace reads: access, Resource selector,
    period summary, entries and history pages."""

    def __init__(
        self,
        *,
        scope: TimesheetWorkspaceScope,
        user_session: UserSessionContext | None,
        module_catalog_service: SupportsModuleEntitlements | None,
    ) -> None:
        self._scope = scope
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_timesheet_workspace_access(self) -> TimesheetWorkspaceAccessFact:
        context = self._scope.base_context(operation_label="open Timesheets")
        available = self._scope.available_scopes()
        if not available:
            require_any_permission(
                self._user_session,
                ("timesheet.read_own", "timesheet.read_team", "timesheet.read_all"),
                operation_label="open Timesheets",
            )
        mine = None
        if TimesheetScope.MINE in available:
            mine = self._scope.reader.resolve_mine_resource(
                user_id=context.actor_user_id,
                tenant_id=context.tenant_id,
                organization_id=context.organization_id,
            )
        default_scope = TimesheetScope.MINE if TimesheetScope.MINE in available else available[0]
        return TimesheetWorkspaceAccessFact(
            actor_user_id=context.actor_user_id,
            available_scopes=available,
            default_scope=default_scope,
            mine_resource=mine,
        )

    def query_timesheet_resources(
        self,
        *,
        scope: TimesheetScope | str,
        search_text: str = "",
        page: int = 1,
        page_size: int = 20,
        sort_key: str = "resource",
        sort_direction: str = "asc",
    ) -> TimesheetResourceReadPage:
        operation_label = "search Timesheet resources"
        resolved_scope = self._scope.require_read_scope(scope, operation_label=operation_label)
        context = self._scope.base_context(operation_label=operation_label)
        request = PageRequest(page=page, page_size=min(50, max(1, int(page_size))))
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={"resource", "code"},
            default_key="resource",
            default_direction=ReadSortDirection.ASCENDING,
        )
        criteria = TimesheetResourceSelectorCriteria(
            search_text=str(search_text or "").strip(), sort=sort
        )
        team_project_ids = self._scope.team_project_ids()

        def read(page_number: int) -> TimesheetResourceReadPage:
            return self._scope.reader.read_resource_page(
                scope=resolved_scope,
                actor_user_id=context.actor_user_id,
                explicit_team_project_ids=team_project_ids,
                tenant_id=context.tenant_id,
                organization_id=context.organization_id,
                criteria=criteria,
                page=page_number,
                page_size=request.page_size,
            )

        result = read(request.page)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.total
        )
        if normalized_page != result.page:
            result = read(normalized_page)
        return result

    def get_timesheet_period(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
    ) -> TimesheetPeriodFact:
        selected = self._scope.select_resource(
            scope=scope, resource_id=resource_id, operation_label="view Timesheet period"
        )
        return self._scope.read_period(selected, period_start=period_start)

    def query_timesheet_entries(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
        search_text: str = "",
        project_id: str | None = None,
        task_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "date",
        sort_direction: str = "desc",
    ) -> TimesheetEntryReadPage:
        selected = self._scope.select_resource(
            scope=scope, resource_id=resource_id, operation_label="list Timesheet entries"
        )
        visible_ids = self._scope.visible_project_ids()
        normalized_project_id = str(project_id or "").strip() or None
        if normalized_project_id and visible_ids is not None and normalized_project_id not in visible_ids:
            raise BusinessRuleError(
                "Project filter is outside the visible scope.", code="PERMISSION_DENIED"
            )
        request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={"date", "project", "task", "hours"},
            default_key="date",
            default_direction=ReadSortDirection.DESCENDING,
        )
        criteria = TimesheetEntryCriteria(
            period_start=period_start,
            search_text=str(search_text or "").strip(),
            project_id=normalized_project_id,
            task_id=str(task_id or "").strip() or None,
            sort=sort,
        )

        def read(page_number: int) -> TimesheetEntryReadPage:
            return self._scope.reader.read_entries(
                resource=selected.resource,
                tenant_id=selected.context.tenant_id,
                organization_id=selected.context.organization_id,
                visible_project_ids=visible_ids,
                criteria=criteria,
                page=page_number,
                page_size=request.page_size,
            )

        result = read(request.page)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.total
        )
        if normalized_page != result.page:
            result = read(normalized_page)
        period = self._scope.read_period(selected, period_start=period_start)
        return replace(
            result,
            items=tuple(
                replace(item, can_edit=period.can_edit_entry, can_delete=period.can_delete_entry)
                for item in result.items
            ),
        )

    def query_timesheet_history(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        page: int = 1,
        page_size: int = 12,
    ) -> TimesheetHistoryReadPage:
        selected = self._scope.select_resource(
            scope=scope, resource_id=resource_id, operation_label="list Timesheet history"
        )
        request = PageRequest(page=page, page_size=page_size)
        result = self._scope.reader.read_history(
            resource=selected.resource,
            tenant_id=selected.context.tenant_id,
            organization_id=selected.context.organization_id,
            criteria=TimesheetHistoryCriteria(),
            page=request.page,
            page_size=request.page_size,
        )
        return replace(
            result,
            items=tuple(self._scope.with_capabilities(item, selected) for item in result.items),
        )


__all__ = ["TimesheetWorkspaceQueryHandler"]
