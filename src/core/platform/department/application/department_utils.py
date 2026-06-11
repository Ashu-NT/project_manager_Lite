from __future__ import annotations

from src.core.platform.org.support import normalize_name


def normalize_optional_text(value: str | None) -> str:
    return (value or "").strip()


def resolve_name(*, name: str | None, display_name: str | None, label: str) -> str:
    return normalize_name(display_name if display_name is not None else name, label=label)


__all__ = ["normalize_optional_text", "resolve_name"]
