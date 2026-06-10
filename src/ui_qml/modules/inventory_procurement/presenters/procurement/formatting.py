from __future__ import annotations


def format_source_reference(source_type: str, source_id: str) -> str:
    left = (source_type or "").strip()
    right = (source_id or "").strip()
    if not left and not right:
        return "-"
    if not right:
        return left
    if not left:
        return right
    return f"{left}: {right}"
