from __future__ import annotations

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.platform.application.time_management.time import TimeService
from src.core.modules.project_management.application.common.pagination import PageRequest
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetReviewReadPage,
    TimesheetReviewReader,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
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
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._timesheet_review_reader = timesheet_review_reader

    def query_review_queue_page(
        self,
        *,
        status: TimesheetPeriodStatus | None = TimesheetPeriodStatus.SUBMITTED,
        page: int = 1,
        page_size: int = 25,
    ) -> TimesheetReviewReadPage:
        require_any_permission(
            self._user_session,
            ("timesheet.approve", "timesheet.lock"),
            operation_label="view timesheet review queue",
        )
        if self._timesheet_review_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Timesheet review reader is not configured.")
        page_request = PageRequest(page=page, page_size=page_size)
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view timesheet review queue"
        )
        allowed_project_ids: tuple[str, ...] | None = None
        if self._user_session is not None and self._user_session.is_project_restricted():
            allowed_project_ids = tuple(
                sorted(
                    self._user_session.project_ids_for("timesheet.approve")
                    | self._user_session.project_ids_for("timesheet.lock")
                )
            )
        return self._timesheet_review_reader.read_page(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            allowed_project_ids=allowed_project_ids,
            status=status,
            page=page_request.page,
            page_size=page_request.page_size,
        )


__all__ = ["TimesheetService"]
