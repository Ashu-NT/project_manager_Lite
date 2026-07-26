from __future__ import annotations

from pydantic import field_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_required_text,
    normalize_optional_text,
    validated_dataclass,
)

TENANT_STATUS_ACTIVE = "active"
TENANT_STATUS_SUSPENDED = "suspended"
TENANT_STATUS_ARCHIVED = "archived"

VALID_TENANT_STATUSES: frozenset[str] = frozenset({
    TENANT_STATUS_ACTIVE,
    TENANT_STATUS_SUSPENDED,
    TENANT_STATUS_ARCHIVED,
})


def normalize_tenant_status(value: object) -> str:
    normalized = normalize_optional_text(value).lower() or TENANT_STATUS_ACTIVE
    if normalized not in VALID_TENANT_STATUSES:
        raise ValidationError(
            "Tenant status is invalid.",
            code="TENANT_STATUS_INVALID",
        )
    return normalized


@validated_dataclass
class Tenant:
    id: str
    tenant_code: str
    display_name: str
    tenant_status: str = TENANT_STATUS_ACTIVE
    version: int = 1

    @property
    def is_active(self) -> bool:
        return self.tenant_status == TENANT_STATUS_ACTIVE

    @field_validator("tenant_code", mode="before")
    @classmethod
    def _validate_tenant_code(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Tenant code is required.",
            code="TENANT_CODE_REQUIRED",
        ).upper()

    @field_validator("display_name", mode="before")
    @classmethod
    def _validate_display_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Display name is required.",
            code="TENANT_DISPLAY_NAME_REQUIRED",
        )

    @field_validator("tenant_status", mode="before")
    @classmethod
    def _validate_tenant_status(cls, value: object) -> str:
        return normalize_tenant_status(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        try:
            resolved = int(value if value not in (None, "") else 1)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Tenant version must be positive.",
                code="TENANT_VERSION_INVALID",
            ) from exc
        if resolved < 1:
            raise ValidationError(
                "Tenant version must be positive.",
                code="TENANT_VERSION_INVALID",
            )
        return resolved

    @staticmethod
    def create(
        tenant_code: str,
        display_name: str,
        *,
        is_active: bool = True,
        tenant_status: str | None = None,
    ) -> "Tenant":
        resolved_status = tenant_status or (TENANT_STATUS_ACTIVE if is_active else TENANT_STATUS_SUSPENDED)
        return Tenant(
            id=generate_id(),
            tenant_code=tenant_code,
            display_name=display_name,
            tenant_status=resolved_status,
            version=1,
        )


__all__ = [
    "TENANT_STATUS_ACTIVE",
    "TENANT_STATUS_ARCHIVED",
    "TENANT_STATUS_SUSPENDED",
    "VALID_TENANT_STATUSES",
    "Tenant",
]
