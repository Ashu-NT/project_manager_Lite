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
    serialize_period_from_service,
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
from src.core.platform.time.domain import TimesheetPeriodStatus


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
            project_service=self._project_service,
            task_service=self._task_service,
            resource_service=self._resource_service,
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
            project_service=self._project_service,
            task_service=self._require_task_service(),
            resource_service=self._resource_service,
            timesheet_service=self._require_timesheet_service(),
        )

    def list_review_queue(
        self,
        *,
        status: str = TimesheetPeriodStatus.SUBMITTED.value,
    ) -> tuple[TimesheetPeriodSummaryDesktopDto, ...]:
        service = self._timesheet_service
        if service is None:
            return ()
        normalized_status = coerce_queue_status(status)
        rows = service.list_timesheet_review_queue(status=normalized_status, limit=200)
        return tuple(
            serialize_review_summary(row, project_service=self._project_service)
            for row in rows
        )

    def get_review_detail(self, period_id: str) -> TimesheetReviewDetailDesktopDto:
        detail = self._require_timesheet_service().get_timesheet_review_detail(
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
        period = self._require_timesheet_service().submit_timesheet_period(
            str(resource_id or "").strip(),
            period_start=period_start,
            note=note,
        )
        return serialize_period_from_service(
            period,
            timesheet_service=self._require_timesheet_service(),
            resource_service=self._resource_service,
            project_service=self._project_service,
        )

    def approve_period(
        self,
        period_id: str,
        *,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        period = self._require_timesheet_service().approve_timesheet_period(
            str(period_id or "").strip(),
            note=note,
        )
        return serialize_period_from_service(
            period,
            timesheet_service=self._require_timesheet_service(),
            resource_service=self._resource_service,
            project_service=self._project_service,
        )

    def reject_period(
        self,
        period_id: str,
        *,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        period = self._require_timesheet_service().reject_timesheet_period(
            str(period_id or "").strip(),
            note=note,
        )
        return serialize_period_from_service(
            period,
            timesheet_service=self._require_timesheet_service(),
            resource_service=self._resource_service,
            project_service=self._project_service,
        )

    def lock_period(
        self,
        *,
        resource_id: str,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        period = self._require_timesheet_service().lock_timesheet_period(
            str(resource_id or "").strip(),
            period_start=period_start,
            note=note,
        )
        return serialize_period_from_service(
            period,
            timesheet_service=self._require_timesheet_service(),
            resource_service=self._resource_service,
            project_service=self._project_service,
        )

    def unlock_period(
        self,
        period_id: str,
        *,
        note: str = "",
    ) -> TimesheetPeriodSummaryDesktopDto:
        period = self._require_timesheet_service().unlock_timesheet_period(
            str(period_id or "").strip(),
            note=note,
        )
        return serialize_period_from_service(
            period,
            timesheet_service=self._require_timesheet_service(),
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
