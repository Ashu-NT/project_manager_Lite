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
from src.core.modules.project_management.api.desktop.timesheets.commands.entry_commands import (
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
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
from src.core.modules.project_management.api.desktop.timesheets.models.owner import (
    OwnerTimesheetEntryPageDesktopDto,
    OwnerTimesheetHistoryPageDesktopDto,
    OwnerTimesheetPeriodDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.models.review import (
    TimesheetReviewDetailDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.models.snapshots import (
    TimesheetAssignmentSnapshotDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.serializers.entry_serializer import (
    serialize_entry,
)
from src.core.modules.project_management.api.desktop.timesheets.serializers.period_serializer import (
    serialize_period_aggregate,
)
from src.core.modules.project_management.api.desktop.timesheets.serializers.owner_serializer import (
    serialize_owner_entry,
    serialize_owner_period,
)
from src.core.modules.project_management.api.desktop.timesheets.serializers.review_serializer import (
    serialize_review_detail,
    serialize_review_summary,
)
from src.core.modules.project_management.api.desktop.timesheets.utils.status_utils import (
    coerce_queue_status,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ResourceService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


class ProjectManagementTimesheetsDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        resource_service: ResourceService | None = None,
        timesheet_service: TimesheetService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._resource_service = resource_service
        self._timesheet_service = timesheet_service

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
        return build_assignment_options(
            project_id=project_id,
            task_service=self._task_service,
        )

    def list_owner_assignments(
        self,
        *,
        project_id: str | None = None,
    ) -> tuple[TimesheetAssignmentOptionDescriptor, ...]:
        owner = self._require_timesheet_service().get_owner_timesheet_identity()
        return tuple(
            option
            for option in self.list_assignments(project_id=project_id)
            if option.resource_id == owner.resource_id
        )

    def get_owner_period(self, *, period_start: date) -> OwnerTimesheetPeriodDesktopDto:
        return serialize_owner_period(
            self._require_timesheet_service().get_owner_timesheet_period(
                period_start=period_start
            )
        )

    def list_owner_entries_page(
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
    ) -> OwnerTimesheetEntryPageDesktopDto:
        result = self._require_timesheet_service().query_owner_time_entries(
            period_start=period_start,
            search_text=search_text,
            project_id=project_id,
            task_id=task_id,
            work_date_from=work_date_from,
            work_date_to=work_date_to,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return OwnerTimesheetEntryPageDesktopDto(
            items=tuple(serialize_owner_entry(item) for item in result.items),
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
        )

    def list_owner_history_page(
        self,
        *,
        status: TimesheetPeriodStatus | None = None,
        page: int = 1,
        page_size: int = 12,
        sort_key: str = "period",
        sort_direction: str = "desc",
    ) -> OwnerTimesheetHistoryPageDesktopDto:
        result = self._require_timesheet_service().query_owner_timesheet_history(
            status=status,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return OwnerTimesheetHistoryPageDesktopDto(
            items=tuple(serialize_owner_period(item) for item in result.items),
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
        )

    def add_owner_time_entry(
        self,
        command: TimesheetEntryCreateCommand,
        *,
        period_start: date,
    ) -> TimesheetEntryDesktopDto:
        entry = self._require_timesheet_service().add_owner_time_entry(
            str(command.assignment_id or "").strip(),
            period_start=period_start,
            entry_date=command.entry_date,
            hours=float(command.hours),
            note=command.note,
        )
        return serialize_entry(entry, str(command.assignment_id or "").strip())

    def update_owner_time_entry(
        self,
        command: TimesheetEntryUpdateCommand,
        *,
        period_start: date,
    ) -> TimesheetEntryDesktopDto:
        entry = self._require_timesheet_service().update_owner_time_entry(
            str(command.entry_id or "").strip(),
            period_start=period_start,
            entry_date=command.entry_date,
            hours=command.hours,
            note=command.note,
        )
        return serialize_entry(
            entry,
            str(getattr(entry, "assignment_id", "") or entry.work_allocation_id),
        )

    def delete_owner_time_entry(self, entry_id: str, *, period_start: date) -> None:
        self._require_timesheet_service().delete_owner_time_entry(
            str(entry_id or "").strip(),
            period_start=period_start,
        )

    def submit_owner_period(
        self,
        *,
        period_start: date,
        expected_version: int,
        note: str = "",
    ) -> OwnerTimesheetPeriodDesktopDto:
        self._require_timesheet_service().submit_owner_timesheet_period(
            period_start=period_start,
            expected_version=expected_version,
            note=note,
        )
        return self.get_owner_period(period_start=period_start)

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
        return build_assignment_snapshot(
            assignment_id,
            period_start=period_start,
            task_service=self._require_task_service(),
            timesheet_service=self._require_timesheet_service(),
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
        service = self._require_timesheet_service()
        normalized_status = coerce_queue_status(status)
        result = service.query_review_queue_page(
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
        detail = self._require_timesheet_service().get_review_queue_inspector(
            str(period_id or "").strip()
        )
        return serialize_review_detail(detail, project_service=self._project_service)

    def add_time_entry(
        self,
        command: TimesheetEntryCreateCommand,
    ) -> TimesheetEntryDesktopDto:
        entry = self._require_timesheet_service().add_time_entry(
            str(command.assignment_id or "").strip(),
            entry_date=command.entry_date,
            hours=float(command.hours),
            note=command.note,
        )
        return serialize_entry(entry, str(command.assignment_id or "").strip())

    def update_time_entry(
        self,
        command: TimesheetEntryUpdateCommand,
    ) -> TimesheetEntryDesktopDto:
        entry = self._require_timesheet_service().update_time_entry(
            str(command.entry_id or "").strip(),
            entry_date=command.entry_date,
            hours=command.hours,
            note=command.note,
        )
        return serialize_entry(
            entry,
            str(
                getattr(entry, "assignment_id", "")
                or getattr(entry, "work_allocation_id", "")
            ),
        )

    def delete_time_entry(self, entry_id: str) -> None:
        self._require_timesheet_service().delete_time_entry(str(entry_id or "").strip())

    def submit_period(
        self,
        *,
        resource_id: str,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        aggregate = self._require_timesheet_service().submit_timesheet_period(
            str(resource_id or "").strip(),
            period_start=period_start,
            note=note,
        )
        return serialize_period_aggregate(
            aggregate,
            resource_service=self._resource_service,
            project_service=self._project_service,
        )

    def approve_period(
        self,
        period_id: str,
        *,
        expected_version: int,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        aggregate = self._require_timesheet_service().approve_timesheet_period(
            str(period_id or "").strip(),
            expected_version=int(expected_version),
            note=note,
        )
        return serialize_period_aggregate(
            aggregate,
            resource_service=self._resource_service,
            project_service=self._project_service,
        )

    def reject_period(
        self,
        period_id: str,
        *,
        expected_version: int,
        note: str,
    ) -> TimesheetPeriodSummaryDesktopDto:
        aggregate = self._require_timesheet_service().reject_timesheet_period(
            str(period_id or "").strip(),
            expected_version=int(expected_version),
            note=note,
        )
        return serialize_period_aggregate(
            aggregate,
            resource_service=self._resource_service,
            project_service=self._project_service,
        )

    def lock_period(
        self,
        period_id: str,
        *,
        expected_version: int,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        aggregate = self._require_timesheet_service().lock_timesheet_period(
            str(period_id or "").strip(),
            expected_version=int(expected_version),
            note=note,
        )
        return serialize_period_aggregate(
            aggregate,
            resource_service=self._resource_service,
            project_service=self._project_service,
        )

    def unlock_period(
        self,
        period_id: str,
        *,
        expected_version: int,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        aggregate = self._require_timesheet_service().unlock_timesheet_period(
            str(period_id or "").strip(),
            expected_version=int(expected_version),
            note=note,
        )
        return serialize_period_aggregate(
            aggregate,
            resource_service=self._resource_service,
            project_service=self._project_service,
        )

    def reopen_period_for_correction(
        self,
        period_id: str,
        *,
        expected_version: int,
        reason: str,
    ) -> TimesheetPeriodSummaryDesktopDto:
        aggregate = self._require_timesheet_service().reopen_approved_timesheet_period_for_correction(
            str(period_id or "").strip(),
            expected_version=int(expected_version),
            note=str(reason or "").strip(),
        )
        return serialize_period_aggregate(
            aggregate,
            resource_service=self._resource_service,
            project_service=self._project_service,
        )

    def _require_task_service(self) -> TaskService:
        if self._task_service is None:
            raise RuntimeError(
                "Project management timesheets desktop API is not connected."
            )
        return self._task_service

    def _require_timesheet_service(self) -> TimesheetService:
        if self._timesheet_service is None:
            raise RuntimeError(
                "Project management timesheets desktop API is not connected."
            )
        return self._timesheet_service


__all__ = ["ProjectManagementTimesheetsDesktopApi"]
