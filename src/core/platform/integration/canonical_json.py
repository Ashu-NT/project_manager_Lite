from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


def _json_default(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Unsupported canonical JSON value: {type(value).__name__}")


def canonical_json_bytes(value: BaseModel | Mapping[str, object]) -> bytes:
    """Serialize exact transport evidence using the shared hashing convention."""
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(
        payload,
        allow_nan=False,
        default=_json_default,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_json_sha256(value: BaseModel | Mapping[str, object]) -> str:
    """Return a stable SHA-256 digest for a contract payload."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


__all__ = ["canonical_json_bytes", "canonical_json_sha256"]
