"""PM-owned actionable-work projections. Counts and windows share SQL predicates."""

from datetime import date

from sqlalchemy import Date, DateTime, String, cast, func, literal, null, select

from src.core.global_overview.application.ordering import sort_action_center_items
from src.core.global_overview.contract.action_center import (
    ActionCenterContribution,
    ActionCenterItemDto,
    ActionCenterSummaryDto,
)
from src.core.global_overview.infrastructure.persistence.reads.action_center import (
    action_window,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.infrastructure.persistence.orm.baseline import (
    ProjectBaselineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus
from src.core.platform.infrastructure.persistence.common.scoped_permission import (
    scoped_permission,
)
from src.core.platform.infrastructure.persistence.orm.time_management.time.time import (
    TimesheetPeriodORM,
)

_MODULE = "Project Management"


class SqlAlchemyProjectManagementActionCenterReader:
    def __init__(self, *, session, resource_identity_reader, timesheet_workspace_reader):
        self._session = session
        self._identities = resource_identity_reader
        self._timesheets = timesheet_workspace_reader

    def _permission(self, context, permission, *, project=None):
        return scoped_permission(user_id=context.user_id, tenant_id=context.tenant_id,
                                 organization_id=context.organization_id, project_id=project,
                                 permissions=(permission,))

    def _datetime(self, value):
        if self._session.get_bind().dialect.name == "postgresql":
            return cast(value, DateTime)
        return func.datetime(value, type_=DateTime)

    def _read(self, base, *, kind, due, recency, identity, limit, after):
        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        rows = self._session.execute(action_window(base, due=due, recency=recency,
            module=_MODULE, kind=kind, identity=identity, after=after, limit=limit)).all() if limit else ()
        return rows, total

    def collect(self, context, preview_limit, *, after=None):
        limit = min(101, max(0, preview_limit))
        project_scope = (ProjectORM.tenant_id == context.tenant_id,
                         ProjectORM.organization_id == context.organization_id)
        identity = self._identities.resolve_resource_for_user(user_id=context.user_id,
            tenant_id=context.tenant_id, organization_id=context.organization_id)
        items = []
        task_count = 0
        if identity is not None:
            assigned = select(TaskAssignmentORM.id).where(
                TaskAssignmentORM.task_id == TaskORM.id,
                TaskAssignmentORM.resource_id == identity.resource_id,
                TaskAssignmentORM.response_status != "declined",
            ).exists()
            recency = self._datetime(TaskORM.start_date)
            base = select(TaskORM.id, TaskORM.name, TaskORM.status, TaskORM.deadline,
                          recency.label("recency"), ProjectORM.name.label("project_name"))\
                .join(ProjectORM, ProjectORM.id == TaskORM.project_id).where(
                    *project_scope, assigned,
                    TaskORM.status.in_((TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED)),
                    self._permission(context, "task.read", project=ProjectORM.id),
                    self._permission(context, "project.read", project=ProjectORM.id),
                )
            rows, task_count = self._read(base, kind="pm_task", due=TaskORM.deadline,
                recency=recency, identity=TaskORM.id, limit=limit, after=after)
            items.extend(ActionCenterItemDto(id=row.id, kind="pm_task", title=row.name,
                module=_MODULE, subject_type="task", subject_id=row.id,
                subject_display=row.project_name, action_state=row.status.value.lower(),
                route_id="project_management.workspace", destination_id="tasks", due_at=row.deadline, sort_at=row.recency) for row in rows)

        baseline = ProjectBaselineORM
        recency = self._datetime(baseline.submitted_at)
        base = select(baseline.id, recency.label("recency"), ProjectORM.name.label("project_name"))\
            .join(ProjectORM, ProjectORM.id == baseline.project_id).where(
                *project_scope, baseline.status == "submitted",
                self._permission(context, "baseline.approve", project=ProjectORM.id),
                self._permission(context, "project.read", project=ProjectORM.id),
            )
        rows, baseline_count = self._read(base, kind="baseline_review", due=cast(null(), Date),
            recency=recency, identity=baseline.id, limit=limit, after=after)
        items.extend(ActionCenterItemDto(id=row.id, kind="baseline_review", title="Review project baseline",
            module=_MODULE, subject_type="baseline", subject_id=row.id, subject_display=row.project_name,
            action_state="awaiting_review", route_id="project_management.workspace", destination_id="scheduling", sort_at=row.recency) for row in rows)

        timesheet_items, timesheet_count = self._submissions(context, limit, after)
        items.extend(timesheet_items)
        return ActionCenterContribution(sort_action_center_items(items, today=date.today())[:limit],
            ActionCenterSummaryDto(task_count + baseline_count + timesheet_count, baseline_count, task_count, timesheet_count))

    def _submissions(self, context, limit, after):
        allowed = self._session.scalar(select(
            self._permission(context, "timesheet.read_own") & self._permission(context, "timesheet.submit")))
        if not allowed:
            return (), 0
        resource = self._timesheets.resolve_mine_resource(user_id=context.user_id,
            tenant_id=context.tenant_id, organization_id=context.organization_id)
        if resource is None:
            return (), 0
        # Reuse the canonical scoped month aggregate rather than rediscovering entry dates.
        months = self._timesheets._open_period_statement(resource=resource,
            tenant_id=context.tenant_id, organization_id=context.organization_id).subquery()
        open_id = literal(f"open:{resource.resource_id}:") + cast(months.c.period_start, String)
        recency = self._datetime(months.c.period_start)
        base = select(open_id.label("id"), months.c.period_start, recency.label("recency"))
        rows, total = self._read(base, kind="timesheet", due=cast(null(), Date), recency=recency,
            identity=open_id, limit=limit, after=after)
        items = [self._period_item(row, "open") for row in rows]
        period = TimesheetPeriodORM
        recency = func.coalesce(period.decided_at, self._datetime(period.period_start))
        base = select(period.id, period.period_start, recency.label("recency")).where(
            period.tenant_id == context.tenant_id, period.organization_id == context.organization_id,
            period.resource_id == resource.resource_id, period.status == TimesheetPeriodStatus.REJECTED,
            self._permission(context, "timesheet.edit_own"),
        )
        rows, rejected = self._read(base, kind="timesheet", due=cast(null(), Date), recency=recency,
            identity=period.id, limit=limit, after=after)
        items.extend(self._period_item(row, "rejected") for row in rows)
        return tuple(items), total + rejected

    @staticmethod
    def _period_item(row, state):
        return ActionCenterItemDto(id=row.id, kind="timesheet", module=_MODULE,
            title="Submit timesheet" if state == "open" else "Correct and resubmit timesheet",
            subject_type="timesheet_period", subject_id=row.id,
            subject_display=row.period_start.strftime("%b %Y"), action_state=state,
            route_id="project_management.workspace", destination_id="timesheets", sort_at=row.recency)
