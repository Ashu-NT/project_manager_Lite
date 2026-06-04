"""Activity feed builder."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from src.core.modules.project_management.api.desktop.dashboard.models.activity_feed import (
    ProjectDashboardActivityFeedDescriptor,
    ProjectDashboardActivityItemDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.date_formatter import (
    coerce_utc_datetime, fmt_utc_datetime,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.period_formatter import (
    period_cutoff_datetime,
)

_EMPTY = ProjectDashboardActivityFeedDescriptor(
    title="Recent Activity",
    subtitle="Activity feed appears here when the dashboard API is connected.",
    empty_state="No recent dashboard activity is available in preview mode.",
)


def build_preview_activity_feed() -> ProjectDashboardActivityFeedDescriptor:
    return ProjectDashboardActivityFeedDescriptor(
        title="Recent Activity",
        subtitle="Activity stream is not connected for this dashboard preview.",
        empty_state="No collaboration or workflow activity is available yet.",
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
        snapshot = collaboration_service.list_workspace_snapshot(limit=120)
    except Exception:
        return ProjectDashboardActivityFeedDescriptor(
            title="Recent Activity",
            subtitle="Activity feed is unavailable for the current session.",
            empty_state="No collaboration or workflow activity is available yet.",
        )

    items: list[tuple[datetime, ProjectDashboardActivityItemDescriptor]] = []

    for note in getattr(snapshot, "notifications", []) or []:
        if project_id and str(getattr(note, "project_id", "") or "") != project_id:
            continue
        created_at = coerce_utc_datetime(getattr(note, "created_at", None))
        if cutoff is not None and created_at is not None and created_at < cutoff:
            continue
        route_id = "platform.control" if str(getattr(note, "entity_type", "") or "") == "approval_request" else "project_management.collaboration"
        items.append((
            created_at or datetime.now(timezone.utc),
            ProjectDashboardActivityItemDescriptor(
                id=f"note-{getattr(note, 'entity_id', '')}-{len(items)}",
                title=str(getattr(note, "headline", "") or ""),
                status_label=str(getattr(note, "notification_type", "") or "").replace("_", " ").title(),
                meta_text=f"{getattr(note, 'project_name', '') or 'Project'} • {getattr(note, 'actor_username', '') or 'system'} • {fmt_utc_datetime(created_at)}".strip(" •"),
                route_id=route_id,
                state={"entityId": getattr(note, "entity_id", ""), "projectId": getattr(note, "project_id", "") or "", "entityType": getattr(note, "entity_type", "")},
            ),
        ))

    for activity in getattr(snapshot, "recent_activity", []) or []:
        if project_id and str(getattr(activity, "project_id", "") or "") != project_id:
            continue
        created_at = coerce_utc_datetime(getattr(activity, "created_at", None))
        if cutoff is not None and created_at is not None and created_at < cutoff:
            continue
        items.append((
            created_at or datetime.now(timezone.utc),
            ProjectDashboardActivityItemDescriptor(
                id=f"comment-{getattr(activity, 'comment_id', '')}",
                title=f"{getattr(activity, 'task_name', '') or 'Task'} update",
                status_label="Mention" if bool(getattr(activity, "unread", False)) else "Comment",
                meta_text=f"{getattr(activity, 'project_name', '') or 'Project'} • {getattr(activity, 'author_username', '') or 'unknown'} • {fmt_utc_datetime(created_at)}".strip(" •"),
                route_id="project_management.tasks",
                state={"taskId": getattr(activity, "task_id", ""), "projectId": getattr(activity, "project_id", ""), "commentId": getattr(activity, "comment_id", "")},
            ),
        ))

    items.sort(key=lambda item: item[0], reverse=True)
    return ProjectDashboardActivityFeedDescriptor(
        title="Recent Activity",
        subtitle=(
            "Portfolio workflow notifications, approvals, and task updates."
            if portfolio_mode
            else "Latest project workflow notifications, approvals, and task updates."
        ),
        empty_state="No recent dashboard activity is available in the selected period.",
        items=tuple(item for _, item in items[:24]),
    )


__all__ = ["build_activity_feed", "build_preview_activity_feed"]
