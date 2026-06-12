from __future__ import annotations


def resolve_selected_id(selected_id: str | None, rows) -> str:
    normalized_id = (selected_id or "").strip()
    if normalized_id and any(row.id == normalized_id for row in rows):
        return normalized_id
    if rows:
        return rows[0].id
    return ""
