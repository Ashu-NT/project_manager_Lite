from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationContextViewModel,
    CollaborationOptionViewModel,
)


def build_context_view_model(
    *,
    inbox: CollaborationCollectionViewModel,
    mentions: CollaborationCollectionViewModel,
    approvals: CollaborationCollectionViewModel,
    activity_feed: CollaborationCollectionViewModel,
    team_updates: CollaborationCollectionViewModel,
) -> CollaborationContextViewModel:
    project_options = [CollaborationOptionViewModel("all", "All Projects")]
    seen_projects: set[tuple[str, str]] = set()
    team_options = [CollaborationOptionViewModel("all", "All Teams")]
    seen_teams: set[str] = set()
    for collection in (inbox, mentions, approvals, activity_feed, team_updates):
        for item in collection.items:
            state = dict(item.state)
            project_id = str(state.get("projectId") or "").strip()
            project_name = str(state.get("projectName") or "").strip()
            if project_id and (project_id, project_name) not in seen_projects:
                project_options.append(
                    CollaborationOptionViewModel(project_id, project_name or project_id)
                )
                seen_projects.add((project_id, project_name))
            team_key = str(
                state.get("actorUsername")
                or state.get("requestor")
                or state.get("username")
                or ""
            ).strip()
            if team_key and team_key not in seen_teams:
                team_options.append(CollaborationOptionViewModel(team_key, f"@{team_key}"))
                seen_teams.add(team_key)
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
    team_updates: CollaborationCollectionViewModel,
) -> str:
    if any(
        collection.items
        for collection in (inbox, mentions, approvals, activity_feed, team_updates)
    ):
        return ""
    return "No collaboration or workflow activity is available for the accessible project scope yet."
