from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardActivityFeedViewModel,
    ProjectDashboardActivityItemViewModel,
)


def to_activity_feed(
    feed,
) -> ProjectDashboardActivityFeedViewModel | None:
    if feed is None:
        return None
    return ProjectDashboardActivityFeedViewModel(
        title=feed.title,
        subtitle=feed.subtitle,
        empty_state=feed.empty_state,
        items=tuple(
            ProjectDashboardActivityItemViewModel(
                id=item.id,
                title=item.title,
                status_label=item.status_label,
                meta_text=item.meta_text,
                route_id=item.route_id,
                state=dict(item.state),
            )
            for item in feed.items
        ),
    )
