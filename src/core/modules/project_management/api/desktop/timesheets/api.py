from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.timesheets.builders.assignment_options_builder import (
    build_assignment_options,
)
from src.core.modules.project_management.api.desktop.timesheets.builders.assignment_snapshot_builder import (
    build_assignment_snapshot,
)
from src.core.modules.project_management.api.desktop.timesheets.builders.project_options_builder import (
    build_project_options,
)
from src.core.modules.project_management.api.desktop.timesheets.models.entries import (
    TimesheetEntryDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.models.options import (
    TimesheetAssignmentOptionDescriptor,
    TimesheetOptionDescriptor,
    TimesheetProjectOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.timesheets.models.periods import (
    TimesheetPeriodSummaryDesktopDto,
    TimesheetReviewPageDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.models.review import (
    TimesheetReviewDetailDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.models.snapshots import (
    TimesheetAssignmentSnapshotDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.models.workspace import (
    ResourceTimesheetEntryPageDesktopDto,
    ResourceTimesheetHistoryPageDesktopDto,
    ResourceTimesheetPeriodDesktopDto,
    TimesheetResourcePageDesktopDto,
    TimesheetWorkspaceAccessDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.serializers.entry_serializer import (
    serialize_entry,
)
from src.core.modules.project_management.api.desktop.timesheets.serializers.period_serializer import (
    serialize_period_aggregate,
)
from src.core.modules.project_management.api.desktop.timesheets.serializers.review_serializer import (
    serialize_review_detail,
    serialize_review_summary,
)
from src.core.modules.project_management.api.desktop.timesheets.serializers.workspace_serializer import (
    serialize_resource_entry,
    serialize_resource_period,
    serialize_timesheet_resource,
    serialize_workspace_access,
)
from src.core.modules.project_management.api.desktop.timesheets.utils.status_utils import (
    coerce_queue_status,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.application.resources import (
    ResourceQueryHandler,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)
from src.core.modules.project_management.application.timesheets import (
    TimesheetReviewQueryHandler,
    TimesheetWorkspaceCommandHandler,
    TimesheetWorkspaceQueryHandler,
)
from src.core.modules.project_management.application.timesheets.dto.commands.time_entries import (
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
)
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetScope,
)
from src.core.platform.application.tenant.modules.authorization import (
    require_module_enabled,
)
from src.core.platform.application.time_management.time import (
    TimeEntryCommandHandler,
    TimeEntryQueryHandler,
    TimesheetPeriodQueryHandler,
    TimesheetPeriodTransitionHandler,
)
from src.core.platform.common.exceptions import ConfigurationError
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


class ProjectManagementTimesheetsDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectQueryHandler | None = None,
        task_lookup_query: TaskLookupQueryHandler | None = None,
        task_assignment_commands: TaskAssignmentCommandHandler | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
        resource_query: ResourceQueryHandler | None = None,
        timesheet_workspace_query: TimesheetWorkspaceQueryHandler | None = None,
        timesheet_workspace_commands: TimesheetWorkspaceCommandHandler | None = None,
        timesheet_review_query: TimesheetReviewQueryHandler | None = None,
        time_entry_commands: TimeEntryCommandHandler | None = None,
        time_entry_queries: TimeEntryQueryHandler | None = None,
        timesheet_period_query: TimesheetPeriodQueryHandler | None = None,
        timesheet_period_transitions: TimesheetPeriodTransitionHandler | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_lookup_query = task_lookup_query
        self._task_assignment_commands = task_assignment_commands
        self._module_catalog_service = module_catalog_service
        self._resource_service = resource_query
        self._workspace_query = timesheet_workspace_query
        self._workspace_commands = timesheet_workspace_commands
        self._review_query = timesheet_review_query
        self._time_entry_commands = time_entry_commands
        self._time_entry_queries = time_entry_queries
        self._period_query = timesheet_period_query
        self._period_transitions = timesheet_period_transitions

    def list_projects(self) -> tuple[TimesheetProjectOptionDescriptor, ...]:
        return build_project_options(self._project_service)

    def list_queue_statuses(self) -> tuple[TimesheetOptionDescriptor, ...]:
        return (
            TimesheetOptionDescriptor(value="all", label="All statuses"),
            *(
                TimesheetOptionDescriptor(
                    value=status.value,
                    label=status.value.replace("_", " ").title(),
                )
                for status in TimesheetPeriodStatus
            ),
        )

    def list_assignments(
        self,
        *,
        project_id: str | None = None,
    ) -> tuple[TimesheetAssignmentOptionDescriptor, ...]:
        if self._task_lookup_query is not None:
            self._require_pm_module("list timesheet assignments")
        return build_assignment_options(
            project_id=project_id,
            task_lookup_query=self._task_lookup_query,
        )

    def get_timesheet_workspace_access(self) -> TimesheetWorkspaceAccessDesktopDto:
        return serialize_workspace_access(
            _connected(self._workspace_query).get_timesheet_workspace_access()
        )

    def list_timesheet_resources_page(
        self,
        *,
        scope: TimesheetScope | str,
        search_text: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> TimesheetResourcePageDesktopDto:
        result = _connected(self._workspace_query).query_timesheet_resources(
            scope=scope,
            search_text=search_text,
            page=page,
            page_size=page_size,
        )
        return TimesheetResourcePageDesktopDto(
            items=tuple(serialize_timesheet_resource(item) for item in result.items),
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

    def list_resource_assignments(
        self,
        *,
        resource_id: str,
        project_id: str | None = None,
    ) -> tuple[TimesheetAssignmentOptionDescriptor, ...]:
        target = str(resource_id or "").strip()
        if self._task_lookup_query is not None:
            self._require_pm_module("list timesheet assignments")
        return tuple(
            build_assignment_options(
                project_id=project_id,
                resource_id=target,
                task_lookup_query=self._task_lookup_query,
            )
        )

    def get_resource_timesheet_period(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
    ) -> ResourceTimesheetPeriodDesktopDto:
        return serialize_resource_period(
            _connected(self._workspace_query).get_timesheet_period(
                scope=scope,
                resource_id=resource_id,
                period_start=period_start,
            )
        )

    def list_resource_timesheet_entries_page(
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
    ) -> ResourceTimesheetEntryPageDesktopDto:
        result = _connected(self._workspace_query).query_timesheet_entries(
            scope=scope,
            resource_id=resource_id,
            period_start=period_start,
            search_text=search_text,
            project_id=project_id,
            task_id=task_id,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return ResourceTimesheetEntryPageDesktopDto(
            items=tuple(serialize_resource_entry(item) for item in result.items),
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
        )

    def list_resource_timesheet_history_page(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        page: int = 1,
        page_size: int = 12,
    ) -> ResourceTimesheetHistoryPageDesktopDto:
        result = _connected(self._workspace_query).query_timesheet_history(
            scope=scope,
            resource_id=resource_id,
            page=page,
            page_size=page_size,
        )
        return ResourceTimesheetHistoryPageDesktopDto(
            items=tuple(serialize_resource_period(item) for item in result.items),
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

    def add_resource_time_entry(
        self,
        command: TimesheetEntryCreateCommand,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
    ) -> TimesheetEntryDesktopDto:
        entry = _connected(self._workspace_commands).add_timesheet_entry(command, scope=scope, resource_id=resource_id, period_start=period_start)
        return serialize_entry(entry, str(command.assignment_id or "").strip())

    def update_resource_time_entry(
        self,
        command: TimesheetEntryUpdateCommand,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
    ) -> TimesheetEntryDesktopDto:
        entry = _connected(self._workspace_commands).update_timesheet_entry(command, scope=scope, resource_id=resource_id, period_start=period_start)
        return serialize_entry(
            entry, str(getattr(entry, "assignment_id", "") or entry.work_allocation_id)
        )

    def delete_resource_time_entry(
        self,
        entry_id: str,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
        expected_version: int,
    ) -> None:
        _connected(self._workspace_commands).delete_timesheet_entry(
            str(entry_id or "").strip(),
            scope=scope,
            resource_id=resource_id,
            period_start=period_start,
            expected_version=expected_version,
        )

    def submit_resource_timesheet_period(
        self,
        *,
        scope: TimesheetScope | str,
        resource_id: str | None,
        period_start: date,
        expected_version: int,
        note: str = "",
    ) -> ResourceTimesheetPeriodDesktopDto:
        _connected(self._workspace_commands).submit_resource_timesheet_period(
            scope=scope,
            resource_id=resource_id,
            period_start=period_start,
            expected_version=expected_version,
            note=note,
        )
        return self.get_resource_timesheet_period(
            scope=scope, resource_id=resource_id, period_start=period_start
        )
    def list_review_resources(
        self,
        *,
        project_id: str | None = None,
    ) -> tuple[TimesheetOptionDescriptor, ...]:
        labels_by_id = {
            option.resource_id: option.resource_name
            for option in self.list_assignments(project_id=project_id)
        }
        return tuple(
            TimesheetOptionDescriptor(value=resource_id, label=label)
            for resource_id, label in sorted(
                labels_by_id.items(), key=lambda item: item[1].casefold()
            )
        )

    def build_assignment_snapshot(
        self,
        assignment_id: str,
        *,
        period_start: date | None = None,
    ) -> TimesheetAssignmentSnapshotDesktopDto:
        self._require_pm_module("view timesheet assignment")
        return build_assignment_snapshot(
            assignment_id,
            period_start=period_start,
            task_lookup_query=self._require_task_lookup_query(),
            task_assignment_commands=self._require_task_assignment_commands(),
            time_entry_queries=_connected(self._time_entry_queries),
            period_queries=_connected(self._period_query),
        )

    def list_review_queue_page(
        self,
        *,
        status: str = TimesheetPeriodStatus.SUBMITTED.value,
        search_text: str = "",
        project_id: str | None = None,
        resource_id: str | None = None,
        period_start_from: date | None = None,
        period_start_to: date | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "submittedAt",
        sort_direction: str = "desc",
    ) -> TimesheetReviewPageDesktopDto:
        normalized_status = coerce_queue_status(status)
        result = _connected(self._review_query).query_review_queue_page(
            status=normalized_status,
            search_text=search_text,
            project_id=project_id,
            resource_id=resource_id,
            period_start_from=period_start_from,
            period_start_to=period_start_to,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return TimesheetReviewPageDesktopDto(
            items=tuple(
                serialize_review_summary(row, project_service=self._project_service)
                for row in result.items
            ),
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
        )

    def get_review_detail(self, period_id: str) -> TimesheetReviewDetailDesktopDto:
        detail = _connected(self._review_query).get_review_queue_inspector(
            str(period_id or "").strip()
        )
        return serialize_review_detail(detail, project_service=self._project_service)

    def add_time_entry(
        self,
        command: TimesheetEntryCreateCommand,
    ) -> TimesheetEntryDesktopDto:
        self._require_pm_module("add time entry")
        entry = _connected(self._workspace_commands).add_timesheet_entry(command)
        return serialize_entry(entry, str(command.assignment_id or "").strip())

    def update_time_entry(
        self,
        command: TimesheetEntryUpdateCommand,
    ) -> TimesheetEntryDesktopDto:
        self._require_pm_module("update time entry")
        entry = _connected(self._workspace_commands).update_timesheet_entry(command)
        return serialize_entry(
            entry,
            str(
                getattr(entry, "assignment_id", "")
                or getattr(entry, "work_allocation_id", "")
            ),
        )

    def delete_time_entry(self, entry_id: str, *, expected_version: int) -> None:
        self._require_pm_module("delete time entry")
        _connected(self._time_entry_commands).delete_time_entry(
            str(entry_id or "").strip(),
            expected_version=expected_version,
        )

    def submit_period(
        self,
        *,
        resource_id: str,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        self._require_pm_module("submit timesheet period")
        aggregate = _connected(self._period_transitions).submit_timesheet_period(
            str(resource_id or "").strip(),
            period_start=period_start,
            note=note,
        )
        return serialize_period_aggregate(
            aggregate,
            resource_query=self._resource_service,
            project_service=self._project_service,
        )

    def approve_period(
        self,
        period_id: str,
        *,
        expected_version: int,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        self._require_pm_module("approve timesheet period")
        aggregate = _connected(self._period_transitions).approve_timesheet_period(
            str(period_id or "").strip(),
            expected_version=int(expected_version),
            note=note,
        )
        return serialize_period_aggregate(
            aggregate,
            resource_query=self._resource_service,
            project_service=self._project_service,
        )

    def reject_period(
        self,
        period_id: str,
        *,
        expected_version: int,
        note: str,
    ) -> TimesheetPeriodSummaryDesktopDto:
        self._require_pm_module("reject timesheet period")
        aggregate = _connected(self._period_transitions).reject_timesheet_period(
            str(period_id or "").strip(),
            expected_version=int(expected_version),
            note=note,
        )
        return serialize_period_aggregate(
            aggregate,
            resource_query=self._resource_service,
            project_service=self._project_service,
        )

    def lock_period(
        self,
        period_id: str,
        *,
        expected_version: int,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        self._require_pm_module("lock timesheet period")
        aggregate = _connected(self._period_transitions).lock_timesheet_period(
            str(period_id or "").strip(),
            expected_version=int(expected_version),
            note=note,
        )
        return serialize_period_aggregate(
            aggregate,
            resource_query=self._resource_service,
            project_service=self._project_service,
        )

    def unlock_period(
        self,
        period_id: str,
        *,
        expected_version: int,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        self._require_pm_module("unlock timesheet period")
        aggregate = _connected(self._period_transitions).unlock_timesheet_period(
            str(period_id or "").strip(),
            expected_version=int(expected_version),
            note=note,
        )
        return serialize_period_aggregate(
            aggregate,
            resource_query=self._resource_service,
            project_service=self._project_service,
        )

    def reopen_period_for_correction(
        self,
        period_id: str,
        *,
        expected_version: int,
        reason: str,
    ) -> TimesheetPeriodSummaryDesktopDto:
        self._require_pm_module("reopen timesheet period")
        aggregate = _connected(self._period_transitions).reopen_approved_timesheet_period_for_correction(
            str(period_id or "").strip(),
            expected_version=int(expected_version),
            note=str(reason or "").strip(),
        )
        return serialize_period_aggregate(
            aggregate,
            resource_query=self._resource_service,
            project_service=self._project_service,
        )

    def _require_pm_module(self, operation_label: str) -> None:
        require_module_enabled(
            self._module_catalog_service,
            "project_management",
            operation_label=operation_label,
        )

    def _require_task_lookup_query(self) -> TaskLookupQueryHandler:
        if self._task_lookup_query is None:
            raise ConfigurationError(
                "Project management timesheets desktop API is not connected."
            )
        return self._task_lookup_query

    def _require_task_assignment_commands(self) -> TaskAssignmentCommandHandler:
        if self._task_assignment_commands is None:
            raise ConfigurationError(
                "Project management timesheets desktop API is not connected."
            )
        return self._task_assignment_commands



def _connected[T](capability: T | None) -> T:
    if capability is None:
        raise ConfigurationError("Project management timesheets desktop API is not connected.")
    return capability


__all__ = ["ProjectManagementTimesheetsDesktopApi"]
