from __future__ import annotations


def resolve_selected_id(selected_id: str | None, rows, *, id_attr: str = "id") -> str:
    normalized_id = (selected_id or "").strip()
    if normalized_id and any(getattr(row, id_attr) == normalized_id for row in rows):
        return normalized_id
    if rows:
        first_row = rows[0]
        return str(getattr(first_row, id_attr))
    return ""
