from __future__ import annotations

from src.core.platform.common.pydantic import normalize_optional_text


def resolve_name(*, name: str, display_name: str | None) -> str :
    
    if display_name is not None:   
        return display_name
    return name


__all__ = ["normalize_optional_text", "resolve_name"]
