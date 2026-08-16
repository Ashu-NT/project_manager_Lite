"""ProjectManagementDashboardDesktopApi — thin desktop dashboard facade."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.dashboard.models.overview import (
    ProjectDashboardOverviewDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.snapshot import (
    ProjectDashboardSnapshotDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.tables import (
    ProjectDashboardOperationalTableDescriptor,
    ProjectDashboardTableColumnDescriptor,
    ProjectDashboardTableRowDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.overview_builder import (
    build_empty_overview,
    build_overview_from_dashboard_data,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.date_formatter import fmt_date
from src.core.modules.project_management.api.desktop.dashboard.services.dashboard_snapshot_service import (
    DashboardSnapshotService,
)

_COL = ProjectDashboardTableColumnDescriptor

_DELAYED_TASKS_COLUMNS = (
    _COL("taskName", "Task", 3, 220, True),
    _COL("projectName", "Project", 2, 160, True),
    _COL("finish", "Finish", 1, 108, True),
    _COL("owner", "Owner", 2, 140),
    _COL("statusLabel", "Status", 0, 96, False, True, "status"),
)


class ProjectManagementDashboardDesktopApi:
    """Thin facade — all orchestration delegates to DashboardSnapshotService."""

    def __init__(
        self,
        *,
        project_service=None,
        dashboard_service=None,
        baseline_service=None,
        reporting_service=None,
        collaboration_service=None,
        approval_service=None,
        task_service=None,
    ) -> None:
        self._snapshot_service = DashboardSnapshotService(
            project_service=project_service,
            dashboard_service=dashboard_service,
            baseline_service=baseline_service,
            reporting_service=reporting_service,
            collaboration_service=collaboration_service,
            approval_service=approval_service,
        )
        self._task_service = task_service

    def build_empty_overview(self) -> ProjectDashboardOverviewDescriptor:
        return build_empty_overview()

    def build_overview_from_dashboard_data(
        self, *, project_name: str, dashboard_data
    ) -> ProjectDashboardOverviewDescriptor:
        return build_overview_from_dashboard_data(
            project_name=project_name, dashboard_data=dashboard_data
        )

    def build_snapshot(
        self,
        *,
        project_id: str | None = None,
        baseline_id: str | None = None,
        period_key: str | None = None,
        view_key: str | None = None,
    ) -> ProjectDashboardSnapshotDescriptor:
        return self._snapshot_service.build_snapshot(
            project_id=project_id,
            baseline_id=baseline_id,
            period_key=period_key,
            view_key=view_key,
        )

    def list_delayed_tasks_page(
        self,
        *,
        project_id: str | None = None,
        search_text: str = "",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "endDateLabel",
        sort_direction: str = "asc",
    ) -> ProjectDashboardOperationalTableDescriptor:
        """Overview's "Delays" tab: SCALABLE (overdue tasks scale with task
        volume, not inherently bounded) -- authoritatively server-paginated
        by reusing Tasks' own query_workspace_page(schedule="overdue", ...)
        rather than a duplicate PM-Dashboard-owned reader. project_id=None
        means "all accessible projects" (portfolio scope), matching
        TaskWorkspaceReader's own falsy-check semantics.
        """
        if self._task_service is None:
            return ProjectDashboardOperationalTableDescriptor(
                id="delayed_tasks", title="Delays",
                collection_semantics="complete", supports_search=True, supports_pagination=True,
                columns=_DELAYED_TASKS_COLUMNS,
                page=page, page_size=page_size, sort_key=sort_key, sort_direction=sort_direction, search_text=search_text,
            )
        result = self._task_service.query_workspace_page(
            project_id=project_id,
            search_text=search_text,
            status="all",
            priority="all",
            schedule="overdue",
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return ProjectDashboardOperationalTableDescriptor(
            id="delayed_tasks", title="Delays",
            subtitle="Every currently overdue task across the accessible scope, not a curated preview.",
            empty_state="No tasks are currently overdue.",
            collection_semantics="complete", supports_search=True, supports_pagination=True,
            columns=_DELAYED_TASKS_COLUMNS,
            rows=tuple(
                ProjectDashboardTableRowDescriptor(
                    id=item.id, route_id="project_management.tasks",
                    state={"taskId": item.id, "projectId": item.project_id},
                    values={
                        "taskName": item.name,
                        "projectName": item.project_name,
                        "finish": fmt_date(item.end_date),
                        "owner": "Unassigned",
                        "statusLabel": "Overdue",
                    },
                )
                for item in result.items
            ),
            page=result.page,
            page_size=result.page_size,
            total_count=result.filtered_total,
            sort_key=sort_key,
            sort_direction=sort_direction,
            search_text=search_text,
        )


__all__ = ["ProjectManagementDashboardDesktopApi"]
