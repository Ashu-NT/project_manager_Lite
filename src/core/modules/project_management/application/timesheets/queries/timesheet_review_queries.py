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
from src.core.modules.project_management.contracts.reads import (
    ReadSort,
    ReadSortDirection,
)
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetReviewCriteria,
    TimesheetReviewInspectorFact,
    TimesheetReviewInspectorReader,
    TimesheetReviewQueueFact,
    TimesheetReviewReader,
    TimesheetReviewReadPage,
)
from src.core.platform.application.security.authorization import (
    get_authorization_engine,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus

_REVIEW_PERMISSIONS = ("timesheet.approve", "timesheet.lock")
_REVIEW_SORT_KEYS = frozenset(
    {
        "resource",
        "title",
        "period",
        "status",
        "statusLabel",
        "totalHours",
        "supportingText",
        "submittedAt",
        "metaText",
    }
)


class TimesheetReviewQueryHandler(ProjectManagementModuleGuardMixin):
    """Reviewer-facing Timesheet reads: the review queue page and its inspector,
    each annotated with the decisions the current reviewer may take."""

    def __init__(
        self,
        *,
        review_reader: TimesheetReviewReader,
        inspector_reader: TimesheetReviewInspectorReader,
        tenant_context_service: TenantContextService,
        user_session: UserSessionContext | None,
        module_catalog_service: SupportsModuleEntitlements | None,
    ) -> None:
        self._review_reader = review_reader
        self._inspector_reader = inspector_reader
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def query_review_queue_page(
        self,
        *,
        status: TimesheetPeriodStatus | None = TimesheetPeriodStatus.SUBMITTED,
        search_text: str = "",
        project_id: str | None = None,
        resource_id: str | None = None,
        period_start_from: date | None = None,
        period_start_to: date | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "submittedAt",
        sort_direction: str = "desc",
    ) -> TimesheetReviewReadPage:
        operation_label = "view timesheet review queue"
        require_any_permission(self._user_session, _REVIEW_PERMISSIONS, operation_label=operation_label)
        page_request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys=set(_REVIEW_SORT_KEYS),
            default_key="submittedAt",
            default_direction=ReadSortDirection.DESCENDING,
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )
        allowed_project_ids = self._allowed_project_ids()
        criteria = TimesheetReviewCriteria(
            status=status,
            search_text=str(search_text or "").strip(),
            project_id=str(project_id or "").strip() or None,
            resource_id=str(resource_id or "").strip() or None,
            period_start_from=period_start_from,
            period_start_to=period_start_to,
            sort=sort,
        )

        def read(page_number: int) -> TimesheetReviewReadPage:
            return self._review_reader.read_page(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                allowed_project_ids=allowed_project_ids,
                criteria=criteria,
                page=page_number,
                page_size=page_request.page_size,
            )

        result = read(page_request.page)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.total
        )
        if normalized_page != result.page:
            result = read(normalized_page)
        return replace(result, items=tuple(self._with_capabilities(item) for item in result.items))

    def get_review_queue_inspector(self, item_id: str) -> TimesheetReviewInspectorFact:
        operation_label = "view timesheet review inspector"
        require_any_permission(self._user_session, _REVIEW_PERMISSIONS, operation_label=operation_label)
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )
        fact = self._inspector_reader.read_item(
            item_id=str(item_id or "").strip(),
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            allowed_project_ids=self._allowed_project_ids(),
        )
        if fact is None:
            raise NotFoundError(
                "Timesheet review item was not found in the active scope.",
                code="TIMESHEET_REVIEW_ITEM_NOT_FOUND",
            )
        return replace(fact, summary=self._with_capabilities(fact.summary))

    def _allowed_project_ids(self) -> tuple[str, ...] | None:
        session = self._user_session
        if session is None or not session.is_project_restricted():
            return None
        return tuple(
            sorted(
                session.project_ids_for("timesheet.approve")
                | session.project_ids_for("timesheet.lock")
            )
        )

    def _has_project_permission(self, item: TimesheetReviewQueueFact, permission_code: str) -> bool:
        session = self._user_session
        if session is None:
            return False
        if not session.is_project_restricted():
            return True
        project_ids = set(item.project_ids)
        return bool(project_ids) and project_ids.issubset(session.project_ids_for(permission_code))

    def _with_capabilities(self, item: TimesheetReviewQueueFact) -> TimesheetReviewQueueFact:
        engine = get_authorization_engine()
        can_decide = engine.has_permission(
            self._user_session, "timesheet.approve"
        ) and self._has_project_permission(item, "timesheet.approve")
        can_lock = engine.has_permission(
            self._user_session, "timesheet.lock"
        ) and self._has_project_permission(item, "timesheet.lock")
        return replace(
            item,
            can_approve=can_decide and item.status == TimesheetPeriodStatus.SUBMITTED,
            can_reject=can_decide and item.status == TimesheetPeriodStatus.SUBMITTED,
            can_lock=can_lock and item.status == TimesheetPeriodStatus.APPROVED,
            can_unlock=can_lock and item.status == TimesheetPeriodStatus.LOCKED,
        )


__all__ = ["TimesheetReviewQueryHandler"]
