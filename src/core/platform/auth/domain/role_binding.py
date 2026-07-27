from __future__ import annotations

from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_required_text,
    validated_dataclass,
)

ROLE_SCOPE_PLATFORM = "platform"
ROLE_SCOPE_TENANT = "tenant"
RESOURCE_ROLE_SCOPE_TYPES = frozenset(
    {
        "organization",
        "site",
        "department",
        "project",
        "storeroom",
    }
)
ROLE_SCOPE_TYPES = frozenset(
    {ROLE_SCOPE_PLATFORM, ROLE_SCOPE_TENANT, *RESOURCE_ROLE_SCOPE_TYPES}
)
ROLE_PRINCIPAL_USER = "user"


def normalize_role_scope_type(value: object) -> str:
    normalized = normalize_required_text(
        value,
        message="Role scope type is required.",
        code="AUTH_ROLE_SCOPE_TYPE_REQUIRED",
    ).lower()
    if normalized not in ROLE_SCOPE_TYPES:
        raise ValidationError(
            f"Unsupported role scope type '{normalized}'.",
            code="AUTH_ROLE_SCOPE_TYPE_INVALID",
        )
    return normalized


def _normalize_binding_datetime(
    value: object,
    *,
    code: str,
    required: bool = False,
) -> datetime | None:
    if value in (None, ""):
        if required:
            raise ValidationError(
                "Role binding timestamp is required.",
                code=code,
            )
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Role binding timestamp must be a valid datetime.",
            code=code,
        )
    return ensure_utc_datetime(value)


@validated_dataclass
class RoleBinding:
    id: str
    principal_type: str
    principal_id: str
    role_id: str
    tenant_id: str | None
    actual_scope_type: str
    actual_scope_id: str | None
    assigned_by: str | None
    assigned_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    version: int = 1

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Role binding id is required.",
            code="AUTH_ROLE_BINDING_ID_REQUIRED",
        )

    @field_validator("principal_type", mode="before")
    @classmethod
    def _validate_principal_type(cls, value: object) -> str:
        normalized = normalize_required_text(
            value,
            message="Principal type is required.",
            code="AUTH_ROLE_BINDING_PRINCIPAL_TYPE_REQUIRED",
        ).lower()
        if normalized != ROLE_PRINCIPAL_USER:
            raise ValidationError(
                "Only user role bindings are currently supported.",
                code="AUTH_ROLE_BINDING_PRINCIPAL_TYPE_INVALID",
            )
        return normalized

    @field_validator("principal_id", "role_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Role binding principal and role ids are required.",
            code="AUTH_ROLE_BINDING_REFERENCE_REQUIRED",
        )

    @field_validator(
        "tenant_id",
        "actual_scope_id",
        "assigned_by",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("actual_scope_type", mode="before")
    @classmethod
    def _validate_scope_type(cls, value: object) -> str:
        return normalize_role_scope_type(value)

    @field_validator("assigned_at", mode="before")
    @classmethod
    def _validate_assigned_at(cls, value: object) -> datetime:
        return _normalize_binding_datetime(
            value,
            code="AUTH_ROLE_BINDING_ASSIGNED_AT_REQUIRED",
            required=True,
        )

    @field_validator("expires_at", "revoked_at", mode="before")
    @classmethod
    def _validate_optional_datetimes(cls, value: object) -> datetime | None:
        return _normalize_binding_datetime(
            value,
            code="AUTH_ROLE_BINDING_TIMESTAMP_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        try:
            normalized = int(value if value not in (None, "") else 1)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Role binding version must be a positive integer.",
                code="AUTH_ROLE_BINDING_VERSION_INVALID",
            ) from exc
        if normalized < 1:
            raise ValidationError(
                "Role binding version must be a positive integer.",
                code="AUTH_ROLE_BINDING_VERSION_INVALID",
            )
        return normalized

    @model_validator(mode="after")
    def _validate_scope_shape(self) -> "RoleBinding":
        if self.actual_scope_type == ROLE_SCOPE_PLATFORM:
            if self.tenant_id is not None or self.actual_scope_id is not None:
                raise ValidationError(
                    "Platform role bindings cannot carry tenant or resource scope.",
                    code="AUTH_ROLE_BINDING_SCOPE_INVALID",
                )
        elif self.actual_scope_type == ROLE_SCOPE_TENANT:
            if self.tenant_id is None or self.actual_scope_id is not None:
                raise ValidationError(
                    "Tenant role bindings require a tenant and no resource id.",
                    code="AUTH_ROLE_BINDING_SCOPE_INVALID",
                )
        elif self.tenant_id is None or self.actual_scope_id is None:
            raise ValidationError(
                "Resource role bindings require tenant and resource ids.",
                code="AUTH_ROLE_BINDING_SCOPE_INVALID",
            )
        if self.expires_at is not None and self.expires_at <= self.assigned_at:
            raise ValidationError(
                "Role binding expiry must be after assignment.",
                code="AUTH_ROLE_BINDING_EXPIRY_INVALID",
            )
        if self.revoked_at is not None and self.revoked_at < self.assigned_at:
            raise ValidationError(
                "Role binding revocation cannot predate assignment.",
                code="AUTH_ROLE_BINDING_REVOCATION_INVALID",
            )
        return self

    @property
    def is_active(self) -> bool:
        now = datetime.now(timezone.utc)
        return self.revoked_at is None and (
            self.expires_at is None or self.expires_at > now
        )

    @staticmethod
    def create(
        *,
        principal_id: str,
        role_id: str,
        actual_scope_type: str,
        tenant_id: str | None = None,
        actual_scope_id: str | None = None,
        assigned_by: str | None = None,
        expires_at: datetime | None = None,
    ) -> "RoleBinding":
        return RoleBinding(
            id=generate_id(),
            principal_type=ROLE_PRINCIPAL_USER,
            principal_id=principal_id,
            role_id=role_id,
            tenant_id=tenant_id,
            actual_scope_type=actual_scope_type,
            actual_scope_id=actual_scope_id,
            assigned_by=assigned_by,
            assigned_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            revoked_at=None,
            version=1,
        )


__all__ = [
    "RESOURCE_ROLE_SCOPE_TYPES",
    "ROLE_PRINCIPAL_USER",
    "ROLE_SCOPE_PLATFORM",
    "ROLE_SCOPE_TENANT",
    "ROLE_SCOPE_TYPES",
    "RoleBinding",
    "normalize_role_scope_type",
]
