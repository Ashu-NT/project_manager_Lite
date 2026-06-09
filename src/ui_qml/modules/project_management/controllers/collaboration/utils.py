from __future__ import annotations


def panel_label(panel_id: str) -> str:
    labels = {
        "inbox": "Inbox",
        "mentions": "Mentions",
        "approvals": "Approvals",
        "activity": "Activity",
        "team_updates": "Team Updates",
        "audit": "Audit",
    }
    return labels.get(panel_id, "Collaboration")


def title_case(value: str) -> str:
    raw = str(value or "").replace("_", " ").strip()
    return " ".join(w.capitalize() for w in raw.split()) if raw else ""


__all__ = ["panel_label", "title_case"]
