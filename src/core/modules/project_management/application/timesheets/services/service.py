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
from src.core.modules.project_management.domain.resources import TimeReportingEligibilityPolicy
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
    TimesheetEntryCriteria,
    TimesheetEntryReadPage,
    TimesheetHistoryCriteria,
    TimesheetHistoryReadPage,
    TimesheetPeriodFact,
    TimesheetResourceFact,
    TimesheetResourceReadPage,
    TimesheetResourceSelectorCriteria,
    TimesheetScope,
    TimesheetWorkspaceAccessFact,
    TimesheetWorkspaceReader,
)
from src.core.modules.project_management.contracts.reads import ReadSort, ReadSortDirection
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.application.security.authorization import get_authorization_engine
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
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
        timesheet_workspace_reader: TimesheetWorkspaceReader | None = None,
        timesheet_review_reader: TimesheetReviewReader | None = None,
        timesheet_review_inspector_reader: TimesheetReviewInspectorReader | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._owner_timesheet_reader = owner_timesheet_reader
        self._timesheet_workspace_reader = timesheet_workspace_reader
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
        ) or engine.has_permission(
            self._user_session, "task.manage"
        ) or engine.has_permission(
            self._user_session, "timesheet.edit_team"
        ) or engine.has_permission(
            self._user_session, "timesheet.edit_all"
        ) or engine.has_permission(
            self._user_session, "timesheet.submit_on_behalf"
        )
        resource = self._resource_repo.get(
            str(getattr(work_allocation, "resource_id", "") or "").strip()
        )
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
            (
                "time.manage",
                "task.manage",
                "timesheet.edit_own",
                "timesheet.edit_team",
                "timesheet.edit_all",
            ),
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

    def get_owner_timesheet_identity(self) -> OwnerTimesheetIdentityFact:
        identity, _, _ = self._owner_context(
            operation_label="resolve own timesheet identity"
        )
        return identity

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
        period_start: date,
        entry_date: date,
        hours: float,
        note: str = "",
    ):
        allocation, _, _ = self._load_work_allocation_context(assignment_id)
        self._require_current_principal_resource(str(allocation.resource_id))
        start, end = self._timesheet_period_bounds(period_start)
        if not start <= entry_date <= end:
            raise ValidationError(
                "The time entry date must be inside the selected reporting period.",
                code="TIME_ENTRY_OUTSIDE_SELECTED_PERIOD",
            )
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
        period_start: date,
        entry_date: date | None = None,
        hours: float | None = None,
        note: str | None = None,
    ):
        entry = self._require_time_entry(entry_id)
        allocation, _, _ = self._load_work_allocation_context(entry.work_allocation_id)
        self._require_current_principal_resource(str(allocation.resource_id))
        start, end = self._timesheet_period_bounds(period_start)
        target_date = entry_date or entry.entry_date
        if not (start <= entry.entry_date <= end and start <= target_date <= end):
            raise ValidationError(
                "The time entry belongs to a different reporting period.",
                code="TIME_ENTRY_OUTSIDE_SELECTED_PERIOD",
            )
        return self.update_time_entry(
            entry_id,
            entry_date=entry_date,
            hours=hours,
            note=note,
        )

    def delete_owner_time_entry(self, entry_id: str, *, period_start: date) -> None:
        entry = self._require_time_entry(entry_id)
        allocation, _, _ = self._load_work_allocation_context(entry.work_allocation_id)
        self._require_current_principal_resource(str(allocation.resource_id))
        start, end = self._timesheet_period_bounds(period_start)
        if not start <= entry.entry_date <= end:
            raise ValidationError(
                "The time entry belongs to a different reporting period.",
                code="TIME_ENTRY_OUTSIDE_SELECTED_PERIOD",
            )
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

    @staticmethod
    def _coerce_timesheet_scope(value: TimesheetScope | str) -> TimesheetScope:
        if isinstance(value, TimesheetScope):
            return value
        try:
            return TimesheetScope(str(value or "").strip().lower())
        except ValueError as exc:
            raise ValidationError(
                "Timesheet scope is invalid.", code="TIMESHEET_SCOPE_INVALID"
            ) from exc

    def _timesheet_workspace_base_context(
        self, *, operation_label: str
    ) -> tuple[str, str, str]:
        if self._timesheet_workspace_reader is None or self._tenant_context_service is None:
            raise RuntimeError("Timesheet workspace reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )
        actor_user_id = str(
            getattr(getattr(self._user_session, "principal", None), "user_id", "") or ""
        ).strip()
        if not actor_user_id:
            raise BusinessRuleError(
                "An authenticated user is required.", code="AUTHENTICATION_REQUIRED"
            )
        return actor_user_id, scope.tenant_id, scope.organization_id

    def _available_timesheet_scopes(self) -> tuple[TimesheetScope, ...]:
        engine = get_authorization_engine()
        available: list[TimesheetScope] = []
        if engine.has_permission(self._user_session, "timesheet.read_own"):
            available.append(TimesheetScope.MINE)
        if engine.has_permission(self._user_session, "timesheet.read_team"):
            available.append(TimesheetScope.TEAM)
        if engine.has_permission(self._user_session, "timesheet.read_all"):
            available.append(TimesheetScope.ALL)
        return tuple(available)

    def _team_project_ids(self) -> tuple[str, ...]:
        session = self._user_session
        if session is None:
            return ()
        return tuple(
            sorted(
                session.project_ids_for("timesheet.read_team")
                | session.project_ids_for("timesheet.edit_team")
                | session.project_ids_for("timesheet.submit_on_behalf")
            )
        )

    def get_timesheet_workspace_access(self) -> TimesheetWorkspaceAccessFact:
        actor_user_id, tenant_id, organization_id = self._timesheet_workspace_base_context(
            operation_label="open Timesheets"
        )
        available = self._available_timesheet_scopes()
        if not available:
            require_any_permission(
                self._user_session,
                ("timesheet.read_own", "timesheet.read_team", "timesheet.read_all"),
                operation_label="open Timesheets",
            )
        mine = None
        if TimesheetScope.MINE in available:
            mine = self._timesheet_workspace_reader.resolve_mine_resource(  # type: ignore[union-attr]
                user_id=actor_user_id,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
        default_scope = (
            TimesheetScope.MINE
            if TimesheetScope.MINE in available
            else available[0]
        )
        return TimesheetWorkspaceAccessFact(
            actor_user_id=actor_user_id,
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
        resolved_scope = self._coerce_timesheet_scope(scope)
        permission = {
            TimesheetScope.MINE: "timesheet.read_own",
            TimesheetScope.TEAM: "timesheet.read_team",
            TimesheetScope.ALL: "timesheet.read_all",
        }[resolved_scope]
        require_any_permission(
            self._user_session, (permission,), operation_label="search Timesheet resources"
        )
        actor_user_id, tenant_id, organization_id = self._timesheet_workspace_base_context(
            operation_label="search Timesheet resources"
        )
        request = PageRequest(page=page, page_size=min(50, max(1, int(page_size))))
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={"resource", "code"},
            default_key="resource",
            default_direction=ReadSortDirection.ASCENDING,
        )
        kwargs = dict(
            scope=resolved_scope,
            actor_user_id=actor_user_id,
            explicit_team_project_ids=self._team_project_ids(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            criteria=TimesheetResourceSelectorCriteria(
                search_text=str(search_text or "").strip(), sort=sort
            ),
            page=request.page,
            page_size=request.page_size,
        )
        result = self._timesheet_workspace_reader.read_resource_page(**kwargs)  # type: ignore[union-attr]
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.total
        )
        if normalized_page != result.page:
            kwargs["page"] = normalized_page
            result = self._timesheet_workspace_reader.read_resource_page(**kwargs)  # type: ignore[union-attr]
        return result

    def _selected_timesheet_resource(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        operation_label: str,
    ) -> tuple[TimesheetScope, TimesheetResourceFact, str, str, str]:
        resolved_scope = self._coerce_timesheet_scope(scope)
        permission = {
            TimesheetScope.MINE: "timesheet.read_own",
            TimesheetScope.TEAM: "timesheet.read_team",
            TimesheetScope.ALL: "timesheet.read_all",
        }[resolved_scope]
        require_any_permission(self._user_session, (permission,), operation_label=operation_label)
        actor_user_id, tenant_id, organization_id = self._timesheet_workspace_base_context(
            operation_label=operation_label
        )
        if resolved_scope == TimesheetScope.MINE:
            resource = self._timesheet_workspace_reader.resolve_mine_resource(  # type: ignore[union-attr]
                user_id=actor_user_id,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
            if resource_id and resource and resource.resource_id != str(resource_id).strip():
                resource = None
        else:
            normalized_resource_id = str(resource_id or "").strip()
            if not normalized_resource_id:
                raise ValidationError(
                    "Select a Resource to view its Timesheet.",
                    code="TIMESHEET_RESOURCE_REQUIRED",
                )
            resource = self._timesheet_workspace_reader.read_resource_in_scope(  # type: ignore[union-attr]
                scope=resolved_scope,
                resource_id=normalized_resource_id,
                actor_user_id=actor_user_id,
                explicit_team_project_ids=self._team_project_ids(),
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
        if resource is None:
            raise NotFoundError(
                "The requested time-reporting Resource is not available in this Timesheet scope.",
                code="TIMESHEET_RESOURCE_NOT_AVAILABLE",
            )
        return resolved_scope, resource, actor_user_id, tenant_id, organization_id

    def _visible_timesheet_project_ids(self) -> tuple[str, ...] | None:
        session = self._user_session
        if session is None or not session.is_project_restricted():
            return None
        return tuple(
            sorted(
                session.project_ids_for("project.read")
                | session.project_ids_for("task.read")
                | session.project_ids_for("time.read")
            )
        )

    def _with_timesheet_capabilities(
        self,
        fact: TimesheetPeriodFact,
        *,
        scope: TimesheetScope,
        actor_user_id: str,
        resource: TimesheetResourceFact,
    ) -> TimesheetPeriodFact:
        engine = get_authorization_engine()
        is_owner = resource.identity_user_id == actor_user_id
        editable_state = fact.status in {
            TimesheetPeriodStatus.OPEN,
            TimesheetPeriodStatus.REJECTED,
        }
        can_edit_permission = (
            is_owner and engine.has_permission(self._user_session, "timesheet.edit_own")
        ) or (
            not is_owner
            and scope == TimesheetScope.TEAM
            and engine.has_permission(self._user_session, "timesheet.edit_team")
        ) or (
            not is_owner
            and scope == TimesheetScope.ALL
            and engine.has_permission(self._user_session, "timesheet.edit_all")
        )
        can_submit_permission = (
            is_owner and engine.has_permission(self._user_session, "timesheet.submit")
        ) or (
            not is_owner
            and engine.has_permission(self._user_session, "timesheet.submit_on_behalf")
        )
        can_submit = editable_state and can_submit_permission and fact.entry_count > 0
        return replace(
            fact,
            can_add_entry=editable_state and can_edit_permission,
            can_edit_entry=editable_state and can_edit_permission,
            can_delete_entry=editable_state and can_edit_permission,
            can_submit=can_submit,
            can_resubmit=can_submit and fact.status == TimesheetPeriodStatus.REJECTED,
            can_view_return_reason=fact.status == TimesheetPeriodStatus.REJECTED and bool(fact.decision_note),
            can_view_history=True,
        )

    def get_timesheet_period(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
    ) -> TimesheetPeriodFact:
        resolved_scope, resource, actor, tenant_id, organization_id = self._selected_timesheet_resource(
            scope=scope, resource_id=resource_id, operation_label="view Timesheet period"
        )
        fact = self._timesheet_workspace_reader.read_period(  # type: ignore[union-attr]
            resource=resource,
            tenant_id=tenant_id,
            organization_id=organization_id,
            period_start=period_start,
        )
        return self._with_timesheet_capabilities(
            fact, scope=resolved_scope, actor_user_id=actor, resource=resource
        )

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
        resolved_scope, resource, actor, tenant_id, organization_id = self._selected_timesheet_resource(
            scope=scope, resource_id=resource_id, operation_label="list Timesheet entries"
        )
        visible_ids = self._visible_timesheet_project_ids()
        normalized_project_id = str(project_id or "").strip() or None
        if normalized_project_id and visible_ids is not None and normalized_project_id not in visible_ids:
            raise BusinessRuleError("Project filter is outside the visible scope.", code="PERMISSION_DENIED")
        request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={"date", "project", "task", "hours"},
            default_key="date",
            default_direction=ReadSortDirection.DESCENDING,
        )
        kwargs = dict(
            resource=resource,
            tenant_id=tenant_id,
            organization_id=organization_id,
            visible_project_ids=visible_ids,
            criteria=TimesheetEntryCriteria(
                period_start=period_start,
                search_text=str(search_text or "").strip(),
                project_id=normalized_project_id,
                task_id=str(task_id or "").strip() or None,
                sort=sort,
            ),
            page=request.page,
            page_size=request.page_size,
        )
        result = self._timesheet_workspace_reader.read_entries(**kwargs)  # type: ignore[union-attr]
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.total
        )
        if normalized_page != result.page:
            kwargs["page"] = normalized_page
            result = self._timesheet_workspace_reader.read_entries(**kwargs)  # type: ignore[union-attr]
        period = self._with_timesheet_capabilities(
            self._timesheet_workspace_reader.read_period(  # type: ignore[union-attr]
                resource=resource,
                tenant_id=tenant_id,
                organization_id=organization_id,
                period_start=period_start,
            ),
            scope=resolved_scope,
            actor_user_id=actor,
            resource=resource,
        )
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
        resolved_scope, resource, actor, tenant_id, organization_id = self._selected_timesheet_resource(
            scope=scope, resource_id=resource_id, operation_label="list Timesheet history"
        )
        request = PageRequest(page=page, page_size=page_size)
        kwargs = dict(
            resource=resource,
            tenant_id=tenant_id,
            organization_id=organization_id,
            criteria=TimesheetHistoryCriteria(),
            page=request.page,
            page_size=request.page_size,
        )
        result = self._timesheet_workspace_reader.read_history(**kwargs)  # type: ignore[union-attr]
        return replace(
            result,
            items=tuple(
                self._with_timesheet_capabilities(
                    item, scope=resolved_scope, actor_user_id=actor, resource=resource
                )
                for item in result.items
            ),
        )

    def _require_timesheet_edit_target(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        operation_label: str,
    ) -> tuple[TimesheetScope, TimesheetResourceFact, str]:
        resolved_scope, resource, actor, _, _ = self._selected_timesheet_resource(
            scope=scope,
            resource_id=resource_id,
            operation_label=operation_label,
        )
        is_owner = resource.identity_user_id == actor
        permission = (
            "timesheet.edit_own"
            if is_owner
            else (
                "timesheet.edit_team"
                if resolved_scope == TimesheetScope.TEAM
                else "timesheet.edit_all"
            )
        )
        require_any_permission(self._user_session, (permission,), operation_label=operation_label)
        return resolved_scope, resource, actor

    def add_timesheet_entry(
        self,
        assignment_id: str,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
        entry_date: date,
        hours: float,
        note: str = "",
    ):
        _, resource, _ = self._require_timesheet_edit_target(
            scope=scope, resource_id=resource_id, operation_label="add Timesheet entry"
        )
        allocation, _, _ = self._load_work_allocation_context(assignment_id)
        if str(allocation.resource_id) != resource.resource_id:
            raise BusinessRuleError(
                "The assignment does not belong to the selected Resource.",
                code="TIMESHEET_RESOURCE_ASSIGNMENT_MISMATCH",
            )
        period = self.get_timesheet_period(
            scope=scope, resource_id=resource.resource_id, period_start=period_start
        )
        if not period.can_add_entry:
            raise BusinessRuleError(
                "This Timesheet period is not open for entry changes.",
                code="TIMESHEET_ENTRY_CHANGE_DENIED",
            )
        start, end = self._timesheet_period_bounds(period_start)
        if not start <= entry_date <= end:
            raise ValidationError(
                "The time entry date must be inside the selected reporting period.",
                code="TIME_ENTRY_OUTSIDE_SELECTED_PERIOD",
            )
        return self.add_time_entry(
            assignment_id, entry_date=entry_date, hours=hours, note=note
        )

    def update_timesheet_entry(
        self,
        entry_id: str,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
        entry_date: date | None = None,
        hours: float | None = None,
        note: str | None = None,
    ):
        _, resource, _ = self._require_timesheet_edit_target(
            scope=scope, resource_id=resource_id, operation_label="update Timesheet entry"
        )
        entry = self._require_time_entry(entry_id)
        allocation, _, _ = self._load_work_allocation_context(entry.work_allocation_id)
        if str(allocation.resource_id) != resource.resource_id:
            raise BusinessRuleError(
                "The time entry does not belong to the selected Resource.",
                code="TIMESHEET_RESOURCE_ENTRY_MISMATCH",
            )
        period = self.get_timesheet_period(
            scope=scope, resource_id=resource.resource_id, period_start=period_start
        )
        if not period.can_edit_entry:
            raise BusinessRuleError(
                "This Timesheet period is not open for entry changes.",
                code="TIMESHEET_ENTRY_CHANGE_DENIED",
            )
        start, end = self._timesheet_period_bounds(period_start)
        target_date = entry_date or entry.entry_date
        if not (start <= entry.entry_date <= end and start <= target_date <= end):
            raise ValidationError(
                "The time entry belongs to a different reporting period.",
                code="TIME_ENTRY_OUTSIDE_SELECTED_PERIOD",
            )
        return self.update_time_entry(
            entry_id, entry_date=entry_date, hours=hours, note=note
        )

    def delete_timesheet_entry(
        self,
        entry_id: str,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
    ) -> None:
        _, resource, _ = self._require_timesheet_edit_target(
            scope=scope, resource_id=resource_id, operation_label="delete Timesheet entry"
        )
        entry = self._require_time_entry(entry_id)
        allocation, _, _ = self._load_work_allocation_context(entry.work_allocation_id)
        if str(allocation.resource_id) != resource.resource_id:
            raise BusinessRuleError(
                "The time entry does not belong to the selected Resource.",
                code="TIMESHEET_RESOURCE_ENTRY_MISMATCH",
            )
        period = self.get_timesheet_period(
            scope=scope, resource_id=resource.resource_id, period_start=period_start
        )
        if not period.can_delete_entry:
            raise BusinessRuleError(
                "This Timesheet period is not open for entry changes.",
                code="TIMESHEET_ENTRY_CHANGE_DENIED",
            )
        start, end = self._timesheet_period_bounds(period_start)
        if not start <= entry.entry_date <= end:
            raise ValidationError(
                "The time entry belongs to a different reporting period.",
                code="TIME_ENTRY_OUTSIDE_SELECTED_PERIOD",
            )
        self.delete_time_entry(entry_id)

    def submit_resource_timesheet_period(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
        expected_version: int,
        note: str = "",
    ):
        resolved_scope, resource, actor, _, _ = self._selected_timesheet_resource(
            scope=scope,
            resource_id=resource_id,
            operation_label="submit Timesheet period",
        )
        is_owner = resource.identity_user_id == actor
        permission = "timesheet.submit" if is_owner else "timesheet.submit_on_behalf"
        require_any_permission(self._user_session, (permission,), operation_label="submit Timesheet period")
        period = self.get_timesheet_period(
            scope=resolved_scope,
            resource_id=resource.resource_id,
            period_start=period_start,
        )
        if not period.can_submit:
            raise BusinessRuleError(
                "This Timesheet period cannot be submitted in its current state.",
                code="TIMESHEET_SUBMIT_DENIED",
            )
        entries = self.list_time_entries_for_resource_period(
            resource.resource_id, period_start=period_start
        )
        for entry in entries:
            allocation, owner, _ = self._load_work_allocation_context(entry.work_allocation_id)
            self._require_time_project_scope(
                work_allocation=allocation,
                work_owner=owner,
                operation_label="submit Timesheet period",
            )
        return self.submit_timesheet_period(
            resource.resource_id,
            period_start=period_start,
            expected_version=expected_version,
            note=note,
            _required_permission=permission,
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
