from __future__ import annotations


def preview_text(*values: str | None) -> str:
    for value in values:
        normalized = " ".join((value or "").strip().split())
        if normalized:
            return normalized
    return "No additional notes recorded."
