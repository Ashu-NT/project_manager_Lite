from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardOperationalTableViewModel,
    ProjectDashboardTableColumnViewModel,
    ProjectDashboardTableRowViewModel,
)

from .formatters.date_formatter import fmt_date

_COL = ProjectDashboardTableColumnViewModel

_DELAYED_TASKS_COLUMNS = (
    _COL("taskName", "Task", 3, 220, True),
    _COL("projectName", "Project", 2, 160, True),
    _COL("finish", "Finish", 1, 108, True),
    _COL("owner", "Owner", 2, 140),
    _COL("statusLabel", "Status", 0, 96, False, True, "status"),
)


def build_delayed_tasks_table(result, *, page=1, page_size=25, sort_key="endDateLabel", sort_direction="asc", search_text=""):
    if result is None:
        return ProjectDashboardOperationalTableViewModel(
            id="delayed_tasks", title="Delays", collection_semantics="complete",
            supports_search=True, supports_pagination=True, columns=_DELAYED_TASKS_COLUMNS,
            page=page, page_size=page_size, sort_key=sort_key, sort_direction=sort_direction, search_text=search_text,
        )
    return ProjectDashboardOperationalTableViewModel(
        id="delayed_tasks", title="Delays",
        subtitle="Every currently overdue task across the accessible scope, not a curated preview.",
        empty_state="No tasks are currently overdue.",
        collection_semantics="complete", supports_search=True, supports_pagination=True,
        columns=_DELAYED_TASKS_COLUMNS,
        rows=tuple(
            ProjectDashboardTableRowViewModel(
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
