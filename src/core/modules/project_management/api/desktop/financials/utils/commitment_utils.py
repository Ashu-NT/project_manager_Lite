"""Commitment status value helpers."""

from __future__ import annotations


def commitment_status_value(item) -> str:
    raw = getattr(item, "commitment_status", None)
    if raw is None:
        return "UNCOMMITTED"
    if hasattr(raw, "value"):
        return str(raw.value).upper()
    return str(raw).upper()


__all__ = ["commitment_status_value"]
