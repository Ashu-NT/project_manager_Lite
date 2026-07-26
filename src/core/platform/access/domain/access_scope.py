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


def normalize_project_membership_project_id(value: object) -> str:
    return normalize_required_text(
        value,
        message="Project id is required.",
        code="PROJECT_ID_REQUIRED",
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


@validated_dataclass
class ProjectMembership:
    id: str
    project_id: str
    user_id: str
    scope_role: str
    permission_codes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("project_id", mode="before")
    @classmethod
    def _validate_project_id(cls, value: object) -> str:
        return normalize_project_membership_project_id(value)

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
        return _validate_created_at(value, code="PROJECT_MEMBERSHIP_CREATED_AT_INVALID")

    @staticmethod
    def create(
        *,
        project_id: str,
        user_id: str,
        scope_role: str,
        permission_codes: Iterable[str] | None = None,
    ) -> "ProjectMembership":
        return ProjectMembership(
            id=generate_id(),
            project_id=project_id,
            user_id=user_id,
            scope_role=scope_role,
            permission_codes=permission_codes,
        )

    @property
    def scope_type(self) -> str:
        return "project"

    @property
    def scope_id(self) -> str:
        return self.project_id

    def as_scoped_access_grant(self) -> ScopedAccessGrant:
        return ScopedAccessGrant(
            id=self.id,
            scope_type=self.scope_type,
            scope_id=self.project_id,
            user_id=self.user_id,
            scope_role=self.scope_role,
            permission_codes=list(self.permission_codes or []),
            created_at=self.created_at,
        )

    @staticmethod
    def from_scoped_access_grant(grant: ScopedAccessGrant) -> "ProjectMembership":
        if (grant.scope_type or "").strip().lower() != "project":
            raise ValueError("ProjectMembership can only be created from a project-scoped grant.")
        return ProjectMembership(
            id=grant.id,
            project_id=grant.scope_id,
            user_id=grant.user_id,
            scope_role=grant.scope_role,
            permission_codes=list(grant.permission_codes or []),
            created_at=grant.created_at,
        )

__all__ = [
    "ProjectMembership",
    "ScopedAccessGrant",
    "normalize_access_permission_codes",
    "normalize_access_scope_id",
    "normalize_access_scope_role",
    "normalize_access_scope_type",
    "normalize_access_user_id",
    "normalize_project_membership_project_id",
]
