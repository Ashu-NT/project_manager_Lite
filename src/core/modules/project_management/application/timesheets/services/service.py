from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.access.scope_permissions import (
    require_any_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.platform.application.time_management.time import TimeService
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetReviewCriteria,
    TimesheetReviewInspectorFact,
    TimesheetReviewInspectorReader,
    TimesheetReviewQueueFact,
    TimesheetReviewReadPage,
    TimesheetReviewReader,
)
from src.core.modules.project_management.contracts.reads import ReadSort, ReadSortDirection
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.application.security.authorization import get_authorization_engine
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


class TimesheetService(
    ProjectManagementModuleGuardMixin,
    TimeService,
):
    """Project-management timesheet workflows backed by shared platform time logic."""

    def __init__(
        self,
        *args,
        timesheet_review_reader: TimesheetReviewReader | None = None,
        timesheet_review_inspector_reader: TimesheetReviewInspectorReader | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._timesheet_review_reader = timesheet_review_reader
        self._timesheet_review_inspector_reader = (
            timesheet_review_inspector_reader or timesheet_review_reader
        )

    def _require_time_project_scope(
        self,
        *,
        work_allocation,
        work_owner,
        operation_label: str,
    ) -> None:
        project_id = self._resolve_entry_project_id(
            work_allocation=work_allocation, work_owner=work_owner
        )
        if not project_id:
            return
        require_any_project_permission(
            self._user_session,
            project_id,
            ("time.manage", "task.manage"),
            operation_label=operation_label,
        )

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
        require_any_permission(
            self._user_session,
            ("timesheet.approve", "timesheet.lock"),
            operation_label="view timesheet review queue",
        )
        if self._timesheet_review_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Timesheet review reader is not configured.")
        page_request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={
                "resource",
                "title",
                "period",
                "status",
                "statusLabel",
                "totalHours",
                "supportingText",
                "submittedAt",
                "metaText",
            },
            default_key="submittedAt",
            default_direction=ReadSortDirection.DESCENDING,
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view timesheet review queue"
        )
        allowed_project_ids = self._review_allowed_project_ids()
        read_kwargs = dict(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            allowed_project_ids=allowed_project_ids,
            criteria=TimesheetReviewCriteria(
                status=status,
                search_text=str(search_text or "").strip(),
                project_id=str(project_id or "").strip() or None,
                resource_id=str(resource_id or "").strip() or None,
                period_start_from=period_start_from,
                period_start_to=period_start_to,
                sort=sort,
            ),
            page=page_request.page,
            page_size=page_request.page_size,
        )
        result = self._timesheet_review_reader.read_page(**read_kwargs)
        normalized_page = normalize_page_for_total(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
        )
        if normalized_page != result.page:
            read_kwargs["page"] = normalized_page
            result = self._timesheet_review_reader.read_page(**read_kwargs)
        return replace(
            result,
            items=tuple(self._with_review_capabilities(item) for item in result.items),
        )

    def get_review_queue_inspector(
        self,
        item_id: str,
    ) -> TimesheetReviewInspectorFact:
        require_any_permission(
            self._user_session,
            ("timesheet.approve", "timesheet.lock"),
            operation_label="view timesheet review inspector",
        )
        reader = self._timesheet_review_inspector_reader
        if reader is None or self._tenant_context_service is None:
            raise RuntimeError("Timesheet review inspector reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view timesheet review inspector"
        )
        fact = reader.read_item(
            item_id=str(item_id or "").strip(),
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            allowed_project_ids=self._review_allowed_project_ids(),
        )
        if fact is None:
            raise NotFoundError(
                "Timesheet review item was not found in the active scope.",
                code="TIMESHEET_REVIEW_ITEM_NOT_FOUND",
            )
        return replace(fact, summary=self._with_review_capabilities(fact.summary))

    def _review_allowed_project_ids(self) -> tuple[str, ...] | None:
        if self._user_session is None or not self._user_session.is_project_restricted():
            return None
        return tuple(
            sorted(
                self._user_session.project_ids_for("timesheet.approve")
                | self._user_session.project_ids_for("timesheet.lock")
            )
        )

    def _with_review_capabilities(
        self,
        item: TimesheetReviewQueueFact,
    ) -> TimesheetReviewQueueFact:
        engine = get_authorization_engine()
        can_decide = engine.has_permission(self._user_session, "timesheet.approve")
        can_lock = engine.has_permission(self._user_session, "timesheet.lock")
        return replace(
            item,
            can_approve=can_decide and item.status == TimesheetPeriodStatus.SUBMITTED,
            can_reject=can_decide and item.status == TimesheetPeriodStatus.SUBMITTED,
            can_lock=can_lock and item.status == TimesheetPeriodStatus.APPROVED,
            can_unlock=can_lock and item.status == TimesheetPeriodStatus.LOCKED,
        )


__all__ = ["TimesheetService"]
