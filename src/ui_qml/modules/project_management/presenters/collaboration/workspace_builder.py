from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
from src.core.modules.project_management.api.desktop import (
    ProjectManagementCollaborationDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationPanelTabViewModel,
    CollaborationWorkspaceViewModel,
)

from .activity_builder import build_activity_collection
from .approvals_builder import build_approvals_collection
from .context_builder import build_context_view_model, build_workspace_empty_state
from .inbox_builder import build_inbox_collection
from .mentions_builder import build_mentions_collection
from .overview_builder import build_overview
from .presence_builder import build_active_presence_collection
from .team_updates_builder import build_team_updates_collection


def build_workspace_state(
    desktop_api: ProjectManagementCollaborationDesktopApi,
    approval_api: PlatformApprovalDesktopApi | None,
    *,
    limit: int = 200,
    selected_project_id: str = "all",
    selected_team_id: str = "all",
    selected_period_key: str = "all",
    selected_unread_key: str = "all",
    mentions_search_text: str = "",
    mentions_page: int = 1,
    mentions_page_size: int = 25,
) -> CollaborationWorkspaceViewModel:
    # R1.6 TEMPORARY: the snapshot still feeds Inbox, Activity, and Presence.
    # Delete this call when those final purpose-specific projections are wired.
    snapshot = desktop_api.build_snapshot(limit=limit)
    inbox = build_inbox_collection(snapshot.notifications)
    period_deltas = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = period_deltas.get(selected_period_key)
    mentions_page_result = desktop_api.query_mentions_page(
        project_id=(None if selected_project_id == "all" else selected_project_id),
        author_username=(None if selected_team_id == "all" else selected_team_id),
        search_text=mentions_search_text,
        created_since=(datetime.now(timezone.utc) - delta if delta is not None else None),
        unread_only=selected_unread_key in {"unread", "attention"},
        page=mentions_page,
        page_size=mentions_page_size,
    )
    mentions = build_mentions_collection(
        mentions_page_result.items,
        total_count=mentions_page_result.total,
        page=mentions_page_result.page,
        page_size=mentions_page_result.page_size,
    )
    approvals = build_approvals_collection(approval_api, limit=limit)
    activity_feed = build_activity_collection(
        notifications=snapshot.notifications,
        recent_activity=snapshot.recent_activity,
    )
    active_presence = build_active_presence_collection(snapshot.active_presence)
    team_updates = build_team_updates_collection(snapshot.active_presence)
    unread_count = sum(1 for item in snapshot.inbox if item.unread)
    attention_count = sum(1 for item in snapshot.notifications if item.attention)
    active_users_count = len(snapshot.active_presence)
    context = build_context_view_model(
        inbox=inbox,
        mentions=mentions,
        approvals=approvals,
        activity_feed=activity_feed,
        team_updates=team_updates,
    )
    panel_tabs = (
        CollaborationPanelTabViewModel("inbox", "Inbox", len(inbox.items)),
        CollaborationPanelTabViewModel("mentions", "Mentions", mentions.total_count),
        CollaborationPanelTabViewModel("approvals", "Approvals", len(approvals.items)),
        CollaborationPanelTabViewModel("activity", "Activity", len(activity_feed.items)),
        CollaborationPanelTabViewModel("team_updates", "Team Updates", len(team_updates.items)),
    )
    return CollaborationWorkspaceViewModel(
        overview=build_overview(
            inbox=inbox,
            mentions=mentions,
            approvals=approvals,
            unread_count=unread_count,
            attention_count=attention_count,
            active_users_count=active_users_count,
        ),
        notifications=inbox,
        inbox=mentions,
        recent_activity=activity_feed,
        active_presence=active_presence,
        context=context,
        panel_tabs=panel_tabs,
        mentions=mentions,
        approvals=approvals,
        activity_feed=activity_feed,
        team_updates=team_updates,
        empty_state=build_workspace_empty_state(
            inbox=inbox,
            mentions=mentions,
            approvals=approvals,
            activity_feed=activity_feed,
            team_updates=team_updates,
        ),
    )
