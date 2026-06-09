from __future__ import annotations


class CollaborationPanelFilterService:
    def __init__(self) -> None:
        self.selected_project_id = "all"
        self.selected_team_id = "all"
        self.selected_period_key = "all"
        self.selected_unread_key = "all"
        self.inbox_search_text = ""
        self.mentions_search_text = ""
        self.approvals_search_text = ""
        self.team_updates_search_text = ""

    def matches_global_filters(self, item: dict) -> bool:
        state = item.get("state") or {}
        if self.selected_project_id != "all":
            if str(state.get("projectId") or "") != self.selected_project_id:
                return False
        if self.selected_team_id != "all":
            key = str(
                state.get("actorUsername")
                or state.get("requestor")
                or state.get("username")
                or ""
            )
            if key != self.selected_team_id:
                return False
        if self.selected_unread_key == "unread" and not bool(state.get("unread")):
            return False
        if self.selected_unread_key == "attention" and not bool(state.get("attention")):
            return False
        return True

    def matches_search(self, item: dict, search: str) -> bool:
        if not search:
            return True
        term = search.lower()
        for key in ("title", "subtitle", "supportingText", "metaText", "statusLabel"):
            if term in str(item.get(key) or "").lower():
                return True
        return False


__all__ = ["CollaborationPanelFilterService"]
