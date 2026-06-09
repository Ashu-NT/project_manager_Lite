from __future__ import annotations


def build_entry_detail(entry_id: str, entries: dict[str, object]) -> dict[str, object]:
    items = entries.get("items") or []
    entry = next((e for e in items if str(e.get("id", "")) == entry_id), None)
    if entry:
        return {
            "id": str(entry.get("id", "")),
            "title": str(entry.get("title", "")),
            "statusLabel": str(entry.get("statusLabel", "")),
            "subtitle": str(entry.get("subtitle", "")),
            "description": str(entry.get("description", "")),
            "emptyState": "",
            "fields": [
                {"label": "Date",   "value": str(entry.get("title", "")),       "supportingText": ""},
                {"label": "Hours",  "value": str(entry.get("statusLabel", "")), "supportingText": ""},
                {"label": "Author", "value": str(entry.get("subtitle", "")),    "supportingText": ""},
            ],
            "state": dict(entry.get("state") or {}),
        }
    return {
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "Entry not found.", "fields": [], "state": {},
    }


__all__ = ["build_entry_detail"]
