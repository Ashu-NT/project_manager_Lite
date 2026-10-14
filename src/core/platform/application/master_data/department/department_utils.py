from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import normalize_optional_text


def require_name(name: str | None) -> str:
    if name is None:
        raise ValidationError("Department name is required.", code="DEPARTMENT_NAME_REQUIRED")
    return name


__all__ = ["normalize_optional_text", "require_name"]
