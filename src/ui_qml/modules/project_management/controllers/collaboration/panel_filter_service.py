from __future__ import annotations


class CollaborationPanelFilterService:
    def __init__(self) -> None:
        self.selected_project_id = "all"
        self.selected_team_id = "all"
        self.selected_period_key = "all"
        self.selected_unread_key = "all"
        self.inbox_search_text = ""
        self.mentions_search_text = ""


__all__ = ["CollaborationPanelFilterService"]
