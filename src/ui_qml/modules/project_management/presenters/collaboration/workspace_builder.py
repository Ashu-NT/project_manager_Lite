from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.modules.project_management.api.desktop import (
    ProjectManagementCollaborationDesktopApi,
)
from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
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


def build_workspace_state(
    desktop_api: ProjectManagementCollaborationDesktopApi,
    approval_api: PlatformApprovalDesktopApi | None,
    *,
    limit: int = 200,
    selected_project_id: str = "all",
    selected_team_id: str = "all",
    selected_period_key: str = "all",
    selected_unread_key: str = "all",
    inbox_search_text: str = "",
    inbox_page: int = 1,
    inbox_page_size: int = 25,
    mentions_search_text: str = "",
    mentions_page: int = 1,
    mentions_page_size: int = 25,
) -> CollaborationWorkspaceViewModel:
    period_deltas = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = period_deltas.get(selected_period_key)
    created_since = datetime.now(timezone.utc) - delta if delta is not None else None
    project_id = None if selected_project_id == "all" else selected_project_id
    author_username = None if selected_team_id == "all" else selected_team_id
    unread_only = selected_unread_key in {"unread", "attention"}

    inbox_result = desktop_api.query_inbox_page(
        project_id=project_id,
        author_username=author_username,
        search_text=inbox_search_text,
        created_since=created_since,
        unread_only=unread_only,
        page=inbox_page,
        page_size=inbox_page_size,
    )
    inbox = build_inbox_collection(
        inbox_result.items,
        total_count=inbox_result.total,
        page=inbox_result.page,
        page_size=inbox_result.page_size,
    )
    mentions_result = desktop_api.query_mentions_page(
        project_id=project_id,
        author_username=author_username,
        search_text=mentions_search_text,
        created_since=created_since,
        unread_only=unread_only,
        page=mentions_page,
        page_size=mentions_page_size,
    )
    mentions = build_mentions_collection(
        mentions_result.items,
        total_count=mentions_result.total,
        page=mentions_result.page,
        page_size=mentions_result.page_size,
    )
    activity_feed = build_activity_collection(
        desktop_api.list_recent_activity(
            project_id=project_id,
            author_username=author_username,
            created_since=created_since,
            limit=min(max(1, int(limit)), 100),
        )
    )
    active_presence = desktop_api.list_active_presence()
    context_options = desktop_api.list_context_options()
    context = build_context_view_model(
        projects=context_options.projects,
        people=tuple(
            dict.fromkeys(
                (*context_options.people, *(item.username for item in active_presence))
            )
        ),
    )
    approvals = build_approvals_collection(
        approval_api,
        limit=limit,
        project_id=project_id,
    )
    panel_tabs = (
        CollaborationPanelTabViewModel("inbox", "Inbox", inbox.total_count),
        CollaborationPanelTabViewModel("mentions", "Mentions", mentions.total_count),
        CollaborationPanelTabViewModel("approvals", "Approvals", len(approvals.items)),
        CollaborationPanelTabViewModel("activity", "Activity", len(activity_feed.items)),
    )
    return CollaborationWorkspaceViewModel(
        overview=build_overview(
            inbox=inbox,
            mentions=mentions,
            approvals=approvals,
            active_users_count=len(active_presence),
        ),
        context=context,
        panel_tabs=panel_tabs,
        inbox=inbox,
        mentions=mentions,
        approvals=approvals,
        activity_feed=activity_feed,
        empty_state=build_workspace_empty_state(
            inbox=inbox,
            mentions=mentions,
            approvals=approvals,
            activity_feed=activity_feed,
        ),
    )
