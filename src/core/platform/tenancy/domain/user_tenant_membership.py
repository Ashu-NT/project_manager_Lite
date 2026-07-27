from __future__ import annotations

from datetime import datetime, timezone

from pydantic import field_validator

from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.common.ids import generate_id


def normalize_user_tenant_membership_id(value: object) -> str:
    return normalize_required_text(
        value,
        message="Membership id is required.",
        code="USER_TENANT_MEMBERSHIP_ID_REQUIRED",
    )


def normalize_user_tenant_membership_user_id(value: object) -> str:
    return normalize_required_text(
        value,
        message="User id is required.",
        code="USER_ID_REQUIRED",
    )


def normalize_user_tenant_membership_tenant_id(value: object) -> str:
    return normalize_required_text(
        value,
        message="Tenant id is required.",
        code="TENANT_ID_REQUIRED",
    )


def normalize_user_tenant_membership_role(value: object) -> str:
    return normalize_optional_text(value).lower() or "member"


def normalize_user_tenant_membership_datetime(
    value: object,
    *,
    code: str,
    required: bool = False,
) -> datetime | None:
    if value in (None, ""):
        if required:
            raise ValidationError(
                "Membership timestamps must be valid datetimes.",
                code=code,
            )
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Membership timestamps must be valid datetimes.",
            code=code,
        )
    return ensure_utc_datetime(value)


@validated_dataclass
class UserTenantMembership:
    id: str
    user_id: str
    tenant_id: str
    is_active: bool = True
    tenant_role: str = "member"
    invited_at: datetime | None = None
    joined_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_user_tenant_membership_id(value)

    @field_validator("user_id", mode="before")
    @classmethod
    def _validate_user_id(cls, value: object) -> str:
        return normalize_user_tenant_membership_user_id(value)

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _validate_tenant_id(cls, value: object) -> str:
        return normalize_user_tenant_membership_tenant_id(value)

    @field_validator("tenant_role", mode="before")
    @classmethod
    def _normalize_tenant_role(cls, value: object) -> str:
        return normalize_user_tenant_membership_role(value)

    @field_validator("invited_at", mode="before")
    @classmethod
    def _validate_invited_at(cls, value: object) -> datetime | None:
        return normalize_user_tenant_membership_datetime(
            value,
            code="USER_TENANT_MEMBERSHIP_INVITED_AT_INVALID",
        )

    @field_validator("joined_at", mode="before")
    @classmethod
    def _validate_joined_at(cls, value: object) -> datetime | None:
        return normalize_user_tenant_membership_datetime(
            value,
            code="USER_TENANT_MEMBERSHIP_JOINED_AT_INVALID",
        )

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: object) -> datetime | None:
        return normalize_user_tenant_membership_datetime(
            value,
            code="USER_TENANT_MEMBERSHIP_CREATED_AT_INVALID",
            required=True,
        )

    @field_validator("updated_at", mode="before")
    @classmethod
    def _validate_updated_at(cls, value: object) -> datetime | None:
        return normalize_user_tenant_membership_datetime(
            value,
            code="USER_TENANT_MEMBERSHIP_UPDATED_AT_INVALID",
            required=True,
        )

    @staticmethod
    def create(
        user_id: str,
        tenant_id: str,
        *,
        tenant_role: str = "member",
        is_active: bool = True,
    ) -> "UserTenantMembership":
        now = datetime.now(timezone.utc)
        return UserTenantMembership(
            id=generate_id(),
            user_id=user_id,
            tenant_id=tenant_id,
            is_active=is_active,
            tenant_role=tenant_role,
            invited_at=None,
            joined_at=now,
            created_at=now,
            updated_at=now,
        )


__all__ = [
    "UserTenantMembership",
    "normalize_user_tenant_membership_datetime",
    "normalize_user_tenant_membership_id",
    "normalize_user_tenant_membership_role",
    "normalize_user_tenant_membership_tenant_id",
    "normalize_user_tenant_membership_user_id",
]
