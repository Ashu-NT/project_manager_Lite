from __future__ import annotations

from .panel_filter_service import CollaborationPanelFilterService
from .utils import title_case


def build_inbox_rows(
    notifications: dict[str, object],
    filter_service: CollaborationPanelFilterService,
) -> list[dict]:
    result = []
    for item in notifications.get("items", []):
        if not filter_service.matches_global_filters(item):
            continue
        if not filter_service.matches_search(item, filter_service.inbox_search_text):
            continue
        state = item.get("state") or {}
        result.append({
            "id":             item.get("id"),
            "title":          str(item.get("title") or ""),
            "workflowType":   title_case(state.get("notificationType") or "workflow"),
            "projectName":    str(state.get("projectName") or "Cross-project"),
            "supportingText": str(item.get("supportingText") or ""),
            "statusLabel":    str(item.get("statusLabel") or ""),
            "subtitle":       str(item.get("subtitle") or ""),
            "metaText":       str(item.get("metaText") or ""),
            "state":          dict(state),
        })
    return result


def build_mentions_rows(
    mentions: dict[str, object],
    filter_service: CollaborationPanelFilterService,
) -> list[dict]:
    result = []
    for item in mentions.get("items", []):
        if not filter_service.matches_global_filters(item):
            continue
        if not filter_service.matches_search(item, filter_service.mentions_search_text):
            continue
        state = item.get("state") or {}
        actor = state.get("actorUsername") or ""
        result.append({
            "id":             item.get("id"),
            "title":          str(item.get("title") or ""),
            "sourceName":     str(state.get("taskId") or item.get("subtitle") or ""),
            "actorLabel":     ("@" + actor) if actor else "",
            "metaText":       str(item.get("metaText") or ""),
            "statusLabel":    str(item.get("statusLabel") or ""),
            "subtitle":       str(item.get("subtitle") or ""),
            "supportingText": str(item.get("supportingText") or ""),
            "state":          dict(state),
        })
    return result


def build_approvals_rows(
    approvals: dict[str, object],
    filter_service: CollaborationPanelFilterService,
) -> list[dict]:
    result = []
    for item in approvals.get("items", []):
        if not filter_service.matches_global_filters(item):
            continue
        if not filter_service.matches_search(item, filter_service.approvals_search_text):
            continue
        state = item.get("state") or {}
        req = state.get("requestor") or ""
        result.append({
            "id":             item.get("id"),
            "title":          str(item.get("title") or ""),
            "approvalType":   title_case(
                state.get("requestType") or state.get("entityType") or "approval"
            ),
            "requestor":      ("@" + req) if req else "",
            "moduleLabel":    str(state.get("moduleLabel") or ""),
            "statusLabel":    str(item.get("statusLabel") or ""),
            "subtitle":       str(item.get("subtitle") or ""),
            "supportingText": str(item.get("supportingText") or ""),
            "metaText":       str(item.get("metaText") or ""),
            "state":          dict(state),
        })
    return result


def build_team_updates_rows(
    team_updates: dict[str, object],
    filter_service: CollaborationPanelFilterService,
) -> list[dict]:
    result = []
    for item in team_updates.get("items", []):
        if not filter_service.matches_global_filters(item):
            continue
        if not filter_service.matches_search(item, filter_service.team_updates_search_text):
            continue
        state = item.get("state") or {}
        result.append({
            "id":           item.get("id"),
            "title":        str(item.get("title") or ""),
            "activityType": title_case(state.get("activityType") or ""),
            "sourceName":   str(state.get("taskName") or item.get("subtitle") or ""),
            "projectName":  str(state.get("projectName") or ""),
            "metaText":     str(item.get("metaText") or ""),
            "statusLabel":  str(item.get("statusLabel") or ""),
            "state":        dict(state),
        })
    return result


__all__ = [
    "build_inbox_rows",
    "build_mentions_rows",
    "build_approvals_rows",
    "build_team_updates_rows",
]
