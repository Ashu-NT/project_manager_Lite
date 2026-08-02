from __future__ import annotations

from dataclasses import field
from datetime import datetime, timezone
from typing import Iterable

from pydantic import field_validator

from src.core.platform.access.domain.feature_access import ScopedRolePolicyRegistry
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


def normalize_access_scope_type(value: object) -> str:
    return ScopedRolePolicyRegistry.normalize_scope_type(str(value or ""))


def normalize_access_scope_id(value: object) -> str:
    return normalize_required_text(
        value,
        message="Scope id is required.",
        code="SCOPE_ID_REQUIRED",
    )


def normalize_access_user_id(value: object) -> str:
    return normalize_required_text(
        value,
        message="User id is required.",
        code="USER_ID_REQUIRED",
    )


def normalize_access_scope_role(value: object) -> str:
    return normalize_optional_text(value).lower() or "viewer"


def normalize_access_permission_codes(value: Iterable[object] | object | None) -> list[str]:
    if value in (None, ""):
        return []
    items: list[object]
    if isinstance(value, (str, bytes)):
        items = [value]
    else:
        try:
            items = list(value)
        except TypeError:
            items = [value]
    return sorted(
        {
            code
            for item in items
            if (code := normalize_optional_text(item))
        }
    )


def _validate_created_at(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("Created at must be a valid datetime.", code=code)
    return value


@validated_dataclass
class ScopedAccessGrant:
    id: str
    scope_type: str
    scope_id: str
    user_id: str
    scope_role: str
    permission_codes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("scope_type", mode="before")
    @classmethod
    def _validate_scope_type(cls, value: object) -> str:
        return normalize_access_scope_type(value)

    @field_validator("scope_id", mode="before")
    @classmethod
    def _validate_scope_id(cls, value: object) -> str:
        return normalize_access_scope_id(value)

    @field_validator("user_id", mode="before")
    @classmethod
    def _validate_user_id(cls, value: object) -> str:
        return normalize_access_user_id(value)

    @field_validator("scope_role", mode="before")
    @classmethod
    def _normalize_scope_role(cls, value: object) -> str:
        return normalize_access_scope_role(value)

    @field_validator("permission_codes", mode="before")
    @classmethod
    def _normalize_permission_codes(cls, value: Iterable[object] | object | None) -> list[str]:
        return normalize_access_permission_codes(value)

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: object) -> datetime:
        return _validate_created_at(value, code="SCOPED_ACCESS_CREATED_AT_INVALID")

    @staticmethod
    def create(
        *,
        scope_type: str,
        scope_id: str,
        user_id: str,
        scope_role: str,
        permission_codes: Iterable[str] | None = None,
    ) -> "ScopedAccessGrant":
        return ScopedAccessGrant(
            id=generate_id(),
            scope_type=scope_type,
            scope_id=scope_id,
            user_id=user_id,
            scope_role=scope_role,
            permission_codes=permission_codes,
        )


__all__ = [
    "ScopedAccessGrant",
    "normalize_access_permission_codes",
    "normalize_access_scope_id",
    "normalize_access_scope_role",
    "normalize_access_scope_type",
    "normalize_access_user_id",
]
