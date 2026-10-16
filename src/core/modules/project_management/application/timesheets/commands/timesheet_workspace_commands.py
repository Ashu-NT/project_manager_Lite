from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.timesheets.dto.commands.time_entries import (
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
)
from src.core.modules.project_management.application.timesheets.timesheet_workspace_scope import (
    SelectedTimesheetResource,
    TimesheetWorkspaceScope,
)
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetPeriodFact,
    TimesheetScope,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.application.time_management.time import (
    TimeAccessPolicy,
    TimeEntryCommandHandler,
    TimeEntryQueryHandler,
    TimesheetPeriodAggregate,
    TimesheetPeriodTransitionHandler,
    TimesheetSupport,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    ValidationError,
)
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.time_management.time import TimeEntry


class TimesheetWorkspaceCommandHandler(ProjectManagementModuleGuardMixin):
    """Resource-scoped Timesheet writes: entry add/update/delete and period
    submission. Each operation checks the workspace scope and period state,
    then delegates to the Platform Time handler that owns the transaction."""

    def __init__(
        self,
        *,
        scope: TimesheetWorkspaceScope,
        time_entries: TimeEntryCommandHandler,
        period_transitions: TimesheetPeriodTransitionHandler,
        entry_queries: TimeEntryQueryHandler,
        support: TimesheetSupport,
        access_policy: TimeAccessPolicy,
        user_session: UserSessionContext | None,
        module_catalog_service: SupportsModuleEntitlements | None,
    ) -> None:
        self._scope = scope
        self._time_entries = time_entries
        self._period_transitions = period_transitions
        self._entry_queries = entry_queries
        self._support = support
        self._access = access_policy
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def add_timesheet_entry(self, command: TimesheetEntryCreateCommand, *, scope: TimesheetScope | str | None = None, resource_id: str | None = None, period_start: date | None = None) -> TimeEntry:
        assignment_id = command.assignment_id.strip()
        hours = float(command.hours)
        if scope is not None:
            if period_start is None:
                raise ValidationError("Reporting period is required.", code="TIMESHEET_PERIOD_REQUIRED")
            selected = self._scope.require_edit_target(
                scope=scope, resource_id=resource_id, operation_label="add Timesheet entry"
            )
            allocation, _, _ = self._support.load_work_allocation_context(assignment_id)
            if str(allocation.resource_id) != selected.resource.resource_id:
                raise BusinessRuleError(
                    "The assignment does not belong to the selected Resource.",
                    code="TIMESHEET_RESOURCE_ASSIGNMENT_MISMATCH",
                )
            if not self._period(selected, period_start).can_add_entry:
                raise _entry_change_denied()
            start, end = self._support.timesheet_period_bounds(period_start)
            if not start <= command.entry_date <= end:
                raise ValidationError(
                    "The time entry date must be inside the selected reporting period.",
                    code="TIME_ENTRY_OUTSIDE_SELECTED_PERIOD",
                )
        return self._time_entries.add_time_entry(
            assignment_id, entry_date=command.entry_date, hours=hours, note=command.note
        )

    def update_timesheet_entry(self, command: TimesheetEntryUpdateCommand, *, scope: TimesheetScope | str | None = None, resource_id: str | None = None, period_start: date | None = None) -> TimeEntry:
        entry_id = command.entry_id.strip()
        if scope is not None:
            if period_start is None:
                raise ValidationError("Reporting period is required.", code="TIMESHEET_PERIOD_REQUIRED")
            selected = self._scope.require_edit_target(
                scope=scope, resource_id=resource_id, operation_label="update Timesheet entry"
            )
            entry = self._require_resource_entry(entry_id, selected)
            if not self._period(selected, period_start).can_edit_entry:
                raise _entry_change_denied()
            start, end = self._support.timesheet_period_bounds(period_start)
            target_date = command.entry_date or entry.entry_date
            if not (start <= entry.entry_date <= end and start <= target_date <= end):
                raise _entry_outside_period()
        return self._time_entries.update_time_entry(
            entry_id,
            expected_version=command.expected_version,
            entry_date=command.entry_date,
            hours=command.hours,
            note=command.note,
        )

    def delete_timesheet_entry(
        self,
        entry_id: str,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
        expected_version: int,
    ) -> None:
        selected = self._scope.require_edit_target(
            scope=scope, resource_id=resource_id, operation_label="delete Timesheet entry"
        )
        entry = self._require_resource_entry(entry_id, selected)
        if not self._period(selected, period_start).can_delete_entry:
            raise _entry_change_denied()
        start, end = self._support.timesheet_period_bounds(period_start)
        if not start <= entry.entry_date <= end:
            raise _entry_outside_period()
        self._time_entries.delete_time_entry(entry_id, expected_version=expected_version)

    def submit_resource_timesheet_period(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
        expected_version: int,
        note: str = "",
    ) -> TimesheetPeriodAggregate:
        operation_label = "submit Timesheet period"
        selected = self._scope.select_resource(
            scope=scope, resource_id=resource_id, operation_label=operation_label
        )
        is_owner = selected.resource.identity_user_id == selected.context.actor_user_id
        permission = "timesheet.submit" if is_owner else "timesheet.submit_on_behalf"
        require_any_permission(self._user_session, (permission,), operation_label=operation_label)
        period = self._period(selected, period_start)
        if int(expected_version) != period.version:
            raise ConcurrencyError(
                "Timesheet period changed since it was loaded.",
                code="TIMESHEET_PERIOD_VERSION_CONFLICT",
            )
        if not period.can_submit:
            raise BusinessRuleError(
                "This Timesheet period cannot be submitted in its current state.",
                code="TIMESHEET_SUBMIT_DENIED",
            )
        resource_id_value = selected.resource.resource_id
        for entry in self._entry_queries.list_time_entries_for_resource_period(
            resource_id_value, period_start=period_start
        ):
            allocation, owner, _ = self._support.load_work_allocation_context(entry.work_allocation_id)
            self._access.require_project_scope(
                work_allocation=allocation,
                work_owner=owner,
                operation_label=operation_label,
            )
        return self._period_transitions.submit_timesheet_period(
            resource_id_value,
            period_start=period_start,
            expected_version=expected_version,
            note=note,
            required_permission=permission,
        )

    def _period(self, selected: SelectedTimesheetResource, period_start: date) -> TimesheetPeriodFact:
        return self._scope.read_period(selected, period_start=period_start)

    def _require_resource_entry(
        self, entry_id: str, selected: SelectedTimesheetResource
    ) -> TimeEntry:
        entry = self._support.require_time_entry(entry_id)
        allocation, _, _ = self._support.load_work_allocation_context(entry.work_allocation_id)
        if str(allocation.resource_id) != selected.resource.resource_id:
            raise BusinessRuleError(
                "The time entry does not belong to the selected Resource.",
                code="TIMESHEET_RESOURCE_ENTRY_MISMATCH",
            )
        return entry


def _entry_change_denied() -> BusinessRuleError:
    return BusinessRuleError(
        "This Timesheet period is not open for entry changes.",
        code="TIMESHEET_ENTRY_CHANGE_DENIED",
    )


def _entry_outside_period() -> ValidationError:
    return ValidationError(
        "The time entry belongs to a different reporting period.",
        code="TIME_ENTRY_OUTSIDE_SELECTED_PERIOD",
    )


__all__ = ["TimesheetWorkspaceCommandHandler"]
