from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationContextViewModel,
    CollaborationOptionViewModel,
)


def build_context_view_model(
    *,
    projects,
    people,
) -> CollaborationContextViewModel:
    project_options = [CollaborationOptionViewModel("all", "All Projects")]
    project_options.extend(
        CollaborationOptionViewModel(str(project_id), str(project_name or project_id))
        for project_id, project_name in projects
    )
    team_options = [CollaborationOptionViewModel("all", "All People")]
    team_options.extend(
        CollaborationOptionViewModel(str(username), f"@{username}")
        for username in people
        if str(username).strip()
    )
    return CollaborationContextViewModel(
        project_options=tuple(project_options),
        team_options=tuple(team_options),
        period_options=(
            CollaborationOptionViewModel("all", "All Time"),
            CollaborationOptionViewModel("24h", "Last 24 Hours"),
            CollaborationOptionViewModel("7d", "Last 7 Days"),
            CollaborationOptionViewModel("30d", "Last 30 Days"),
        ),
        unread_options=(
            CollaborationOptionViewModel("all", "All Items"),
            CollaborationOptionViewModel("unread", "Unread Only"),
            CollaborationOptionViewModel("attention", "Needs Attention"),
        ),
    )


def build_workspace_empty_state(
    *,
    inbox: CollaborationCollectionViewModel,
    mentions: CollaborationCollectionViewModel,
    approvals: CollaborationCollectionViewModel,
    activity_feed: CollaborationCollectionViewModel,
) -> str:
    if any(
        collection.items
        for collection in (inbox, mentions, approvals, activity_feed)
    ):
        return ""
    return "No collaboration or workflow activity is available for the accessible project scope yet."
