from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetPeriodFact,
    TimesheetResourceFact,
    TimesheetScope,
    TimesheetWorkspaceReader,
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
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus

_READ_PERMISSION_BY_SCOPE = {
    TimesheetScope.MINE: "timesheet.read_own",
    TimesheetScope.TEAM: "timesheet.read_team",
    TimesheetScope.ALL: "timesheet.read_all",
}


@dataclass(frozen=True)
class TimesheetWorkspaceContext:
    actor_user_id: str
    tenant_id: str
    organization_id: str


@dataclass(frozen=True)
class SelectedTimesheetResource:
    scope: TimesheetScope
    resource: TimesheetResourceFact
    context: TimesheetWorkspaceContext


class TimesheetWorkspaceScope:
    """Resource-scoped Timesheet authorization shared by the workspace query
    and command handlers: scope resolution, the selected Resource, and the
    per-period capability flags both sides must agree on."""

    def __init__(
        self,
        *,
        workspace_reader: TimesheetWorkspaceReader,
        tenant_context_service: TenantContextService,
        user_session: UserSessionContext | None,
    ) -> None:
        self._reader = workspace_reader
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session

    @property
    def reader(self) -> TimesheetWorkspaceReader:
        return self._reader

    @staticmethod
    def coerce_scope(value: TimesheetScope | str) -> TimesheetScope:
        if isinstance(value, TimesheetScope):
            return value
        try:
            return TimesheetScope(str(value or "").strip().lower())
        except ValueError as exc:
            raise ValidationError(
                "Timesheet scope is invalid.", code="TIMESHEET_SCOPE_INVALID"
            ) from exc

    def require_read_scope(
        self, scope: TimesheetScope | str, *, operation_label: str
    ) -> TimesheetScope:
        resolved = self.coerce_scope(scope)
        require_any_permission(
            self._user_session,
            (_READ_PERMISSION_BY_SCOPE[resolved],),
            operation_label=operation_label,
        )
        return resolved

    def base_context(self, *, operation_label: str) -> TimesheetWorkspaceContext:
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
        return TimesheetWorkspaceContext(
            actor_user_id=actor_user_id,
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
        )

    def available_scopes(self) -> tuple[TimesheetScope, ...]:
        engine = get_authorization_engine()
        return tuple(
            scope
            for scope, permission in _READ_PERMISSION_BY_SCOPE.items()
            if engine.has_permission(self._user_session, permission)
        )

    def team_project_ids(self) -> tuple[str, ...]:
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

    def visible_project_ids(self) -> tuple[str, ...] | None:
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

    def select_resource(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        operation_label: str,
    ) -> SelectedTimesheetResource:
        resolved_scope = self.require_read_scope(scope, operation_label=operation_label)
        context = self.base_context(operation_label=operation_label)
        resource: TimesheetResourceFact | None
        if resolved_scope == TimesheetScope.MINE:
            resource = self._reader.resolve_mine_resource(
                user_id=context.actor_user_id,
                tenant_id=context.tenant_id,
                organization_id=context.organization_id,
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
            resource = self._reader.read_resource_in_scope(
                scope=resolved_scope,
                resource_id=normalized_resource_id,
                actor_user_id=context.actor_user_id,
                explicit_team_project_ids=self.team_project_ids(),
                tenant_id=context.tenant_id,
                organization_id=context.organization_id,
            )
        if resource is None:
            raise NotFoundError(
                "The requested time-reporting Resource is not available in this Timesheet scope.",
                code="TIMESHEET_RESOURCE_NOT_AVAILABLE",
            )
        return SelectedTimesheetResource(scope=resolved_scope, resource=resource, context=context)

    def require_edit_target(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        operation_label: str,
    ) -> SelectedTimesheetResource:
        selected = self.select_resource(
            scope=scope, resource_id=resource_id, operation_label=operation_label
        )
        if selected.resource.identity_user_id == selected.context.actor_user_id:
            permission = "timesheet.edit_own"
        elif selected.scope == TimesheetScope.TEAM:
            permission = "timesheet.edit_team"
        else:
            permission = "timesheet.edit_all"
        require_any_permission(self._user_session, (permission,), operation_label=operation_label)
        return selected

    def read_period(
        self, selected: SelectedTimesheetResource, *, period_start: date
    ) -> TimesheetPeriodFact:
        fact = self._reader.read_period(
            resource=selected.resource,
            tenant_id=selected.context.tenant_id,
            organization_id=selected.context.organization_id,
            period_start=period_start,
        )
        return self.with_capabilities(fact, selected)

    def with_capabilities(
        self, fact: TimesheetPeriodFact, selected: SelectedTimesheetResource
    ) -> TimesheetPeriodFact:
        engine = get_authorization_engine()
        session = self._user_session
        is_owner = selected.resource.identity_user_id == selected.context.actor_user_id
        editable_state = fact.status in {
            TimesheetPeriodStatus.OPEN,
            TimesheetPeriodStatus.REJECTED,
        }
        can_edit_permission = (
            (is_owner and engine.has_permission(session, "timesheet.edit_own"))
            or (
                not is_owner
                and selected.scope == TimesheetScope.TEAM
                and engine.has_permission(session, "timesheet.edit_team")
            )
            or (
                not is_owner
                and selected.scope == TimesheetScope.ALL
                and engine.has_permission(session, "timesheet.edit_all")
            )
        )
        can_submit_permission = (
            is_owner and engine.has_permission(session, "timesheet.submit")
        ) or (not is_owner and engine.has_permission(session, "timesheet.submit_on_behalf"))
        can_submit = editable_state and can_submit_permission and fact.entry_count > 0
        return replace(
            fact,
            can_add_entry=editable_state and can_edit_permission,
            can_edit_entry=editable_state and can_edit_permission,
            can_delete_entry=editable_state and can_edit_permission,
            can_submit=can_submit,
            can_resubmit=can_submit and fact.status == TimesheetPeriodStatus.REJECTED,
            can_view_return_reason=fact.status == TimesheetPeriodStatus.REJECTED
            and bool(fact.decision_note),
            can_view_history=True,
        )


__all__ = [
    "SelectedTimesheetResource",
    "TimesheetWorkspaceContext",
    "TimesheetWorkspaceScope",
]
