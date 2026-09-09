from __future__ import annotations

from datetime import date, datetime, time

from src.core.application.global_overview.contracts.action_center import (
    ActionCenterContext,
    ActionCenterContribution,
    ActionCenterItemDto,
    ActionCenterSummaryDto,
)
from src.core.application.global_overview.services.ordering import sort_action_center_items
from src.core.modules.project_management.application.projects.service import ProjectService
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.tasks.service import TaskService
from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetHistoryCriteria,
    TimesheetWorkspaceReader,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.scheduling.baseline import BaselineStatus
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus
from src.core.shared.resource_identity.contracts import ResourceIdentityReader

_MODULE = "Project Management"
_OPEN_TASK_STATUSES = (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED)


def _to_datetime(value: date | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min)


class ProjectManagementActionCenterContributor:
    """Project Management's Action Center contribution: assigned tasks,
    submitted baselines awaiting review, and the user's own open/rejected
    timesheet periods.

    Each of the three sources keeps its own actionable criteria and never
    invents an assignee, reviewer, or due date the domain doesn't have --
    see `action-center-guidelines.md` for the verified per-source semantics
    this mirrors exactly.
    """

    def __init__(
        self,
        *,
        task_service: TaskService,
        baseline_service: BaselineService,
        project_service: ProjectService,
        resource_identity_reader: ResourceIdentityReader,
        timesheet_workspace_reader: TimesheetWorkspaceReader,
    ) -> None:
        self._task_service = task_service
        self._baseline_service = baseline_service
        self._project_service = project_service
        self._resource_identity_reader = resource_identity_reader
        self._timesheet_workspace_reader = timesheet_workspace_reader

    def collect(
        self,
        context: ActionCenterContext,
        preview_limit: int,
    ) -> ActionCenterContribution:
        # One accessible-projects fetch, shared by task project-name lookup
        # and baseline discovery -- avoids fetching the same list twice.
        accessible_projects = self._project_service.list_projects()
        projects_by_id = {project.id: project for project in accessible_projects}

        task_items = self._collect_tasks(context, projects_by_id)
        baseline_items = self._collect_baselines(context, accessible_projects)
        timesheet_items, timesheet_total = self._collect_timesheets(context, preview_limit)

        assigned_work = len(task_items)
        reviews_and_approvals = len(baseline_items)
        submissions = timesheet_total

        merged = [*task_items, *baseline_items, *timesheet_items]
        ordered = sort_action_center_items(merged, today=date.today())[:preview_limit]
        summary = ActionCenterSummaryDto(
            all_action_items=assigned_work + reviews_and_approvals + submissions,
            reviews_and_approvals=reviews_and_approvals,
            assigned_work=assigned_work,
            submissions=submissions,
        )
        return ActionCenterContribution(items=ordered, summary=summary)

    # -- A. Tasks -----------------------------------------------------------

    def _collect_tasks(
        self,
        context: ActionCenterContext,
        projects_by_id: dict,
    ) -> tuple[ActionCenterItemDto, ...]:
        identity = self._resource_identity_reader.resolve_resource_for_user(
            user_id=context.user_id,
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
        )
        if identity is None:
            return ()
        tasks = self._task_service.list_tasks_for_resource(identity.resource_id)
        open_tasks = [task for task in tasks if task.status in _OPEN_TASK_STATUSES]
        items = tuple(self._task_to_item(task, projects_by_id) for task in open_tasks)
        return items

    @staticmethod
    def _task_to_item(task, projects_by_id: dict) -> ActionCenterItemDto:
        project = projects_by_id.get(task.project_id)
        project_name = project.name if project is not None else task.project_id
        return ActionCenterItemDto(
            id=task.id,
            kind="pm_task",
            title=task.name,
            module=_MODULE,
            subject_type="task",
            subject_id=task.id,
            subject_display=project_name,
            action_state=task.status.value.lower(),
            route_id="project_management.tasks",
            due_at=task.deadline,
            source_timestamp=_to_datetime(task.start_date),
        )

    # -- B. Baseline reviews --------------------------------------------------

    def _collect_baselines(
        self,
        context: ActionCenterContext,
        accessible_projects,
    ) -> tuple[ActionCenterItemDto, ...]:
        items: list[ActionCenterItemDto] = []
        for project in accessible_projects:
            baselines = self._baseline_service.list_baselines(project.id)
            for baseline in baselines:
                if baseline.status != BaselineStatus.SUBMITTED:
                    continue
                items.append(self._baseline_to_item(baseline, project))
        return tuple(items)

    @staticmethod
    def _baseline_to_item(baseline, project) -> ActionCenterItemDto:
        return ActionCenterItemDto(
            id=baseline.id,
            kind="baseline_review",
            title="Review project baseline",
            module=_MODULE,
            subject_type="baseline",
            subject_id=baseline.id,
            subject_display=project.name,
            action_state="awaiting_review",
            route_id="project_management.scheduling",
            source_timestamp=_to_datetime(baseline.submitted_at),
        )

    # -- C. Timesheets --------------------------------------------------------

    def _collect_timesheets(
        self,
        context: ActionCenterContext,
        preview_limit: int,
    ) -> tuple[tuple[ActionCenterItemDto, ...], int]:
        resource = self._timesheet_workspace_reader.resolve_mine_resource(
            user_id=context.user_id,
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
        )
        if resource is None:
            return (), 0

        # OPEN periods never got a TimesheetPeriodORM row (one is only
        # created on first submit), so read_history's own
        # TimesheetPeriodORM-anchored query cannot see them -- a dedicated
        # read path covers that case; REJECTED periods do have a row and
        # are covered by read_history as usual.
        open_count = self._timesheet_workspace_reader.count_open_periods(
            resource=resource,
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
        )
        open_periods = self._timesheet_workspace_reader.list_open_periods(
            resource=resource,
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            limit=max(preview_limit, 1),
        )
        rejected_page = self._timesheet_workspace_reader.read_history(
            resource=resource,
            tenant_id=context.tenant_id,
            organization_id=context.organization_id,
            criteria=TimesheetHistoryCriteria(status=TimesheetPeriodStatus.REJECTED),
            page=1,
            page_size=max(preview_limit, 1),
        )
        items = tuple(
            self._period_to_item(period, action_title="Submit timesheet", action_state="open")
            for period in open_periods
        ) + tuple(
            self._period_to_item(
                period,
                action_title="Correct and resubmit timesheet",
                action_state="rejected",
            )
            for period in rejected_page.items
        )
        total = open_count + rejected_page.total
        return items, total

    @staticmethod
    def _period_to_item(period, *, action_title: str, action_state: str) -> ActionCenterItemDto:
        # period_end is the boundary of the period being timesheeted, not a
        # submission deadline -- never mapped to due_at.
        subject_display = f"{period.period_start:%b %d} - {period.period_end:%b %d}"
        return ActionCenterItemDto(
            id=period.period_id,
            kind="timesheet",
            title=action_title,
            module=_MODULE,
            subject_type="timesheet_period",
            subject_id=period.period_id,
            subject_display=subject_display,
            action_state=action_state,
            route_id="project_management.timesheets",
            source_timestamp=_to_datetime(period.decided_at or period.period_start),
        )


__all__ = ["ProjectManagementActionCenterContributor"]
