from __future__ import annotations


def resolve_selected_entry_id(selected_entry_id: str | None, filtered_entries) -> str:
    normalized_id = (selected_entry_id or "").strip()
    if normalized_id and any(entry.id == normalized_id for entry in filtered_entries):
        return normalized_id
    if filtered_entries:
        return filtered_entries[0].id
    return ""
