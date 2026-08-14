from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Collection


class ReadSortDirection(str, Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"

    @classmethod
    def coerce(cls, value: object) -> "ReadSortDirection":
        normalized = str(getattr(value, "value", value) or "").strip().lower()
        if normalized in {"desc", "descending", "1"}:
            return cls.DESCENDING
        return cls.ASCENDING


@dataclass(frozen=True, slots=True)
class ReadSort:
    key: str
    direction: ReadSortDirection = ReadSortDirection.ASCENDING

    @classmethod
    def normalize(
        cls,
        *,
        key: object,
        direction: object,
        allowed_keys: Collection[str],
        default_key: str,
        default_direction: ReadSortDirection = ReadSortDirection.ASCENDING,
    ) -> "ReadSort":
        normalized_key = str(key or "").strip()
        resolved_key = normalized_key if normalized_key in allowed_keys else default_key
        resolved_direction = (
            ReadSortDirection.coerce(direction)
            if normalized_key in allowed_keys
            else default_direction
        )
        return cls(key=resolved_key, direction=resolved_direction)


__all__ = ["ReadSort", "ReadSortDirection"]
