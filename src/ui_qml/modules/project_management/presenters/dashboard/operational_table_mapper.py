from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardOperationalTableViewModel,
    ProjectDashboardTableColumnViewModel,
    ProjectDashboardTableRowViewModel,
)


def to_operational_tables(
    tables,
) -> tuple[ProjectDashboardOperationalTableViewModel, ...]:
    return tuple(
        ProjectDashboardOperationalTableViewModel(
            id=table.id,
            title=table.title,
            subtitle=table.subtitle,
            empty_state=table.empty_state,
            collection_semantics=table.collection_semantics,
            supports_search=table.supports_search,
            supports_pagination=table.supports_pagination,
            columns=tuple(
                ProjectDashboardTableColumnViewModel(
                    key=column.key,
                    label=column.label,
                    flex=column.flex,
                    min_width=column.min_width,
                    sortable=column.sortable,
                    visible=column.visible,
                    column_type=column.column_type,
                )
                for column in table.columns
            ),
            rows=tuple(
                ProjectDashboardTableRowViewModel(
                    id=row.id,
                    values=dict(row.values),
                    route_id=row.route_id,
                    state=dict(row.state),
                )
                for row in table.rows
            ),
            page=getattr(table, "page", 1),
            page_size=getattr(table, "page_size", 25),
            total_count=getattr(table, "total_count", 0),
            sort_key=getattr(table, "sort_key", ""),
            sort_direction=getattr(table, "sort_direction", "asc"),
            search_text=getattr(table, "search_text", ""),
        )
        for table in tables
    )
