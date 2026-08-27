from __future__ import annotations

from src.core.platform.common.pydantic import normalize_optional_text


def resolve_name(*, name: str | None, display_name: str | None) -> str | None:
    return display_name if display_name is not None else name


__all__ = ["normalize_optional_text", "resolve_name"]
