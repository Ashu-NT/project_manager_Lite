from __future__ import annotations


def resolve_selected_id(
    selected_id: str | None,
    rows,
    *,
    preferred_fallback_index: int = 0,
) -> str:
    normalized_id = (selected_id or "").strip()
    available_ids = [str(getattr(row, "id", "") or "") for row in rows]
    if normalized_id and normalized_id in available_ids:
        return normalized_id
    if not rows:
        return ""
    fallback_index = min(max(preferred_fallback_index, 0), len(rows) - 1)
    return str(getattr(rows[fallback_index], "id", "") or "")


def resolve_compare_id(compare_id: str | None, rows, *, disallowed_id: str) -> str:
    normalized_id = (compare_id or "").strip()
    available_ids = [
        str(getattr(row, "id", "") or "")
        for row in rows
        if str(getattr(row, "id", "") or "") != disallowed_id
    ]
    if normalized_id and normalized_id in available_ids:
        return normalized_id
    return available_ids[0] if available_ids else ""
