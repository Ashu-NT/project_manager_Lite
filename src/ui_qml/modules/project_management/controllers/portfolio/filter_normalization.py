from __future__ import annotations


def normalize_intake_status(raw: str) -> str:
    """Normalise intake status filter input to the canonical stored form.

    Empty/whitespace → "all"; "ALL" (case-insensitive) → "all";
    any other value → uppercased (e.g. "draft" → "DRAFT").
    """
    v = (raw or "").strip().upper() or "ALL"
    return "all" if v == "ALL" else v


__all__ = ["normalize_intake_status"]
