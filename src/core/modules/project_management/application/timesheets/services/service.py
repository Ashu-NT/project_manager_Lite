from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.access.scope_permissions import (
    require_any_project_permission,
    require_project_permission,
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
    OwnerTimesheetEntryCriteria,
    OwnerTimesheetEntryFact,
    OwnerTimesheetEntryReadPage,
    OwnerTimesheetHistoryCriteria,
    OwnerTimesheetHistoryReadPage,
    OwnerTimesheetIdentityFact,
    OwnerTimesheetPeriodFact,
    OwnerTimesheetReader,
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
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


class TimesheetService(
    ProjectManagementModuleGuardMixin,
    TimeService,
):
    """Project-management timesheet workflows backed by shared platform time logic."""

    def __init__(
        self,
        *args,
        owner_timesheet_reader: OwnerTimesheetReader | None = None,
        timesheet_review_reader: TimesheetReviewReader | None = None,
        timesheet_review_inspector_reader: TimesheetReviewInspectorReader | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._owner_timesheet_reader = owner_timesheet_reader
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
        engine = get_authorization_engine()
        can_manage_shared_time = engine.has_permission(
            self._user_session, "time.manage"
        ) or engine.has_permission(self._user_session, "task.manage")
        if not can_manage_shared_time:
            require_any_permission(
                self._user_session,
                ("timesheet.submit",),
                operation_label=operation_label,
            )
            self._require_current_principal_resource(
                str(getattr(work_allocation, "resource_id", "") or "").strip()
            )
        project_id = self._resolve_entry_project_id(
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

    def _require_time_manage_permission(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("time.manage", "task.manage", "timesheet.submit"),
            operation_label=operation_label,
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

    def _owner_context(
        self, *, operation_label: str
    ) -> tuple[OwnerTimesheetIdentityFact, str, str]:
        require_any_permission(
            self._user_session,
            ("time.read", "time.manage", "task.read", "task.manage", "timesheet.submit"),
            operation_label=operation_label,
        )
        if self._owner_timesheet_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Owner timesheet reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )
        user_id = str(
            getattr(getattr(self._user_session, "principal", None), "user_id", "") or ""
        ).strip()
        identity = self._owner_timesheet_reader.resolve_identity(
            user_id=user_id,
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
        )
        if identity is None:
            raise NotFoundError(
                "No active project resource is linked to the signed-in user in this organization.",
                code="TIMESHEET_OWNER_RESOURCE_NOT_FOUND",
            )
        return identity, scope.tenant_id, scope.organization_id

    def _owner_allowed_project_ids(self) -> tuple[str, ...] | None:
        session = self._user_session
        if session is None or not session.is_project_restricted():
            return None
        permissions = (
            "time.read",
            "time.manage",
            "task.read",
            "task.manage",
            "timesheet.submit",
        )
        project_ids: set[str] = set()
        for permission in permissions:
            project_ids.update(session.project_ids_for(permission))
        return tuple(sorted(project_ids))

    def _with_owner_capabilities(
        self, fact: OwnerTimesheetPeriodFact
    ) -> OwnerTimesheetPeriodFact:
        engine = get_authorization_engine()
        editable = fact.status in {
            TimesheetPeriodStatus.OPEN,
            TimesheetPeriodStatus.REJECTED,
        }
        can_manage = engine.has_permission(
            self._user_session, "time.manage"
        ) or engine.has_permission(self._user_session, "task.manage")
        can_submit_permission = engine.has_permission(
            self._user_session, "timesheet.submit"
        )
        can_change_entries = editable and (can_manage or can_submit_permission)
        can_submit = editable and can_submit_permission and fact.entry_count > 0
        return replace(
            fact,
            can_add_entry=can_change_entries,
            can_edit_entry=can_change_entries,
            can_delete_entry=can_change_entries,
            can_submit=can_submit,
            can_resubmit=can_submit and fact.status == TimesheetPeriodStatus.REJECTED,
            can_view_return_reason=(
                fact.status == TimesheetPeriodStatus.REJECTED
                and bool(fact.decision_note)
            ),
        )

    def get_owner_timesheet_period(
        self, *, period_start: date
    ) -> OwnerTimesheetPeriodFact:
        identity, tenant_id, organization_id = self._owner_context(
            operation_label="view own timesheet period"
        )
        fact = self._owner_timesheet_reader.read_period(  # type: ignore[union-attr]
            identity=identity,
            tenant_id=tenant_id,
            organization_id=organization_id,
            period_start=period_start,
            allowed_project_ids=self._owner_allowed_project_ids(),
        )
        return self._with_owner_capabilities(fact)

    def query_owner_time_entries(
        self,
        *,
        period_start: date,
        search_text: str = "",
        project_id: str | None = None,
        task_id: str | None = None,
        work_date_from: date | None = None,
        work_date_to: date | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "date",
        sort_direction: str = "desc",
    ) -> OwnerTimesheetEntryReadPage:
        identity, tenant_id, organization_id = self._owner_context(
            operation_label="list own timesheet entries"
        )
        request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={"date", "project", "task", "hours"},
            default_key="date",
            default_direction=ReadSortDirection.DESCENDING,
        )
        criteria = OwnerTimesheetEntryCriteria(
            period_start=period_start,
            search_text=str(search_text or "").strip(),
            project_id=str(project_id or "").strip() or None,
            task_id=str(task_id or "").strip() or None,
            work_date_from=work_date_from,
            work_date_to=work_date_to,
            sort=sort,
        )
        read_kwargs = dict(
            identity=identity,
            tenant_id=tenant_id,
            organization_id=organization_id,
            allowed_project_ids=self._owner_allowed_project_ids(),
            criteria=criteria,
            page=request.page,
            page_size=request.page_size,
        )
        result = self._owner_timesheet_reader.read_entries(**read_kwargs)  # type: ignore[union-attr]
        normalized_page = normalize_page_for_total(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
        )
        if normalized_page != result.page:
            read_kwargs["page"] = normalized_page
            result = self._owner_timesheet_reader.read_entries(**read_kwargs)  # type: ignore[union-attr]
        period = self.get_owner_timesheet_period(period_start=period_start)
        return replace(
            result,
            items=tuple(
                replace(
                    item,
                    can_edit=period.can_edit_entry,
                    can_delete=period.can_delete_entry,
                )
                for item in result.items
            ),
        )

    def query_owner_timesheet_history(
        self,
        *,
        status: TimesheetPeriodStatus | None = None,
        page: int = 1,
        page_size: int = 12,
        sort_key: str = "period",
        sort_direction: str = "desc",
    ) -> OwnerTimesheetHistoryReadPage:
        identity, tenant_id, organization_id = self._owner_context(
            operation_label="list own timesheet history"
        )
        request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={"period", "status", "totalHours", "submittedAt"},
            default_key="period",
            default_direction=ReadSortDirection.DESCENDING,
        )
        criteria = OwnerTimesheetHistoryCriteria(status=status, sort=sort)
        read_kwargs = dict(
            identity=identity,
            tenant_id=tenant_id,
            organization_id=organization_id,
            allowed_project_ids=self._owner_allowed_project_ids(),
            criteria=criteria,
            page=request.page,
            page_size=request.page_size,
        )
        result = self._owner_timesheet_reader.read_history(**read_kwargs)  # type: ignore[union-attr]
        normalized_page = normalize_page_for_total(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
        )
        if normalized_page != result.page:
            read_kwargs["page"] = normalized_page
            result = self._owner_timesheet_reader.read_history(**read_kwargs)  # type: ignore[union-attr]
        return replace(
            result,
            items=tuple(self._with_owner_capabilities(item) for item in result.items),
        )

    def add_owner_time_entry(
        self,
        assignment_id: str,
        *,
        entry_date: date,
        hours: float,
        note: str = "",
    ):
        allocation, _, _ = self._load_work_allocation_context(assignment_id)
        self._require_current_principal_resource(str(allocation.resource_id))
        return self.add_time_entry(
            assignment_id,
            entry_date=entry_date,
            hours=hours,
            note=note,
        )

    def update_owner_time_entry(
        self,
        entry_id: str,
        *,
        entry_date: date | None = None,
        hours: float | None = None,
        note: str | None = None,
    ):
        entry = self._require_time_entry(entry_id)
        allocation, _, _ = self._load_work_allocation_context(entry.work_allocation_id)
        self._require_current_principal_resource(str(allocation.resource_id))
        return self.update_time_entry(
            entry_id,
            entry_date=entry_date,
            hours=hours,
            note=note,
        )

    def delete_owner_time_entry(self, entry_id: str) -> None:
        entry = self._require_time_entry(entry_id)
        allocation, _, _ = self._load_work_allocation_context(entry.work_allocation_id)
        self._require_current_principal_resource(str(allocation.resource_id))
        self.delete_time_entry(entry_id)

    def submit_owner_timesheet_period(
        self,
        *,
        period_start: date,
        expected_version: int,
        note: str = "",
    ):
        identity, _, _ = self._owner_context(operation_label="submit own timesheet")
        entries = self.list_time_entries_for_resource_period(
            identity.resource_id,
            period_start=period_start,
        )
        for entry in entries:
            allocation, owner, _ = self._load_work_allocation_context(
                entry.work_allocation_id
            )
            self._require_time_project_scope(
                work_allocation=allocation,
                work_owner=owner,
                operation_label="submit own timesheet",
            )
        return self.submit_timesheet_period(
            identity.resource_id,
            period_start=period_start,
            expected_version=expected_version,
            note=note,
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

    def _require_timesheet_review_scope(
        self, permission_code: str, entries: list
    ) -> None:
        session = self._user_session
        if session is None or not session.is_project_restricted():
            return
        project_ids = self._project_ids_for_entries(entries)
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

    def _has_review_project_permission(
        self, item: TimesheetReviewQueueFact, permission_code: str
    ) -> bool:
        session = self._user_session
        if session is None:
            return False
        if not session.is_project_restricted():
            return True
        project_ids = set(item.project_ids)
        return bool(project_ids) and project_ids.issubset(
            session.project_ids_for(permission_code)
        )

    def _with_review_capabilities(
        self,
        item: TimesheetReviewQueueFact,
    ) -> TimesheetReviewQueueFact:
        engine = get_authorization_engine()
        can_decide = (
            engine.has_permission(self._user_session, "timesheet.approve")
            and self._has_review_project_permission(item, "timesheet.approve")
        )
        can_lock = (
            engine.has_permission(self._user_session, "timesheet.lock")
            and self._has_review_project_permission(item, "timesheet.lock")
        )
        return replace(
            item,
            can_approve=can_decide and item.status == TimesheetPeriodStatus.SUBMITTED,
            can_reject=can_decide and item.status == TimesheetPeriodStatus.SUBMITTED,
            can_lock=can_lock and item.status == TimesheetPeriodStatus.APPROVED,
            can_unlock=can_lock and item.status == TimesheetPeriodStatus.LOCKED,
        )


__all__ = ["TimesheetService"]
