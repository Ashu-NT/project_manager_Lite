"""Build the intentionally bounded dashboard collaboration feed."""

from __future__ import annotations

from datetime import datetime, timezone

from src.core.modules.project_management.api.desktop.dashboard.formatters.date_formatter import (
    coerce_utc_datetime,
    fmt_utc_datetime,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.period_formatter import (
    period_cutoff_datetime,
)
from src.core.modules.project_management.api.desktop.dashboard.models.activity_feed import (
    ProjectDashboardActivityFeedDescriptor,
    ProjectDashboardActivityItemDescriptor,
)


def build_preview_activity_feed() -> ProjectDashboardActivityFeedDescriptor:
    return ProjectDashboardActivityFeedDescriptor(
        title="Recent Activity",
        subtitle="Activity stream is not connected for this dashboard preview.",
        empty_state="No collaboration activity is available yet.",
    )


def build_activity_feed(
    *,
    project_id: str | None,
    selected_period_key: str,
    portfolio_mode: bool,
    collaboration_service=None,
) -> ProjectDashboardActivityFeedDescriptor:
    if collaboration_service is None:
        return build_preview_activity_feed()
    cutoff = period_cutoff_datetime(selected_period_key)
    try:
        recent_activity = collaboration_service.list_recent_activity(
            project_id=project_id,
            created_since=cutoff,
            limit=120,
        )
    except Exception:
        return ProjectDashboardActivityFeedDescriptor(
            title="Recent Activity",
            subtitle="Activity feed is unavailable for the current session.",
            empty_state="No collaboration activity is available yet.",
        )

    items: list[tuple[datetime, ProjectDashboardActivityItemDescriptor]] = []
    for activity in recent_activity:
        created_at = coerce_utc_datetime(getattr(activity, "created_at", None))
        items.append(
            (
                created_at or datetime.now(timezone.utc),
                ProjectDashboardActivityItemDescriptor(
                    id=f"comment-{getattr(activity, 'comment_id', '')}",
                    title=f"{getattr(activity, 'task_name', '') or 'Task'} update",
                    status_label="Mention" if bool(getattr(activity, "mentions", ())) else "Comment",
                    meta_text=" | ".join(
                        (
                            getattr(activity, "project_name", "") or "Project",
                            getattr(activity, "author_username", "") or "unknown",
                            fmt_utc_datetime(created_at),
                        )
                    ),
                    route_id="project_management.tasks",
                    state={
                        "taskId": getattr(activity, "task_id", ""),
                        "projectId": getattr(activity, "project_id", ""),
                        "commentId": getattr(activity, "comment_id", ""),
                    },
                ),
            )
        )

    items.sort(key=lambda item: item[0], reverse=True)
    return ProjectDashboardActivityFeedDescriptor(
        title="Recent Activity",
        subtitle=(
            "Latest 24 task-collaboration events across the accessible portfolio."
            if portfolio_mode
            else "Latest 24 task-collaboration events for the selected project."
        ),
        empty_state="No recent dashboard activity is available in the selected period.",
        items=tuple(item for _, item in items[:24]),
    )


__all__ = ["build_activity_feed", "build_preview_activity_feed"]
