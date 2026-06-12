from __future__ import annotations


def normalize_project_id(raw: str) -> str:
    v = (raw or "").strip()
    return v or "all"


def normalize_queue_status(raw: str) -> str:
    v = (raw or "").strip().upper()
    return v or "SUBMITTED"


__all__ = ["normalize_project_id", "normalize_queue_status"]
