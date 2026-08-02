from __future__ import annotations

from dataclasses import field
from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)

SERVICE_PRINCIPAL_STATUS_ACTIVE = "active"
SERVICE_PRINCIPAL_STATUS_DISABLED = "disabled"


def _required_id(value: object, *, label: str, code: str) -> str:
    return normalize_required_text(value, message=f"{label} is required.", code=code)


def _optional_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Identity timestamp must be a datetime.",
            code="IDENTITY_TIMESTAMP_INVALID",
        )
    return ensure_utc_datetime(value)


@validated_dataclass
class ServicePrincipal:
    id: str
    tenant_id: str
    organization_id: str
    user_id: str
    name: str
    description: str = ""
    status: str = SERVICE_PRINCIPAL_STATUS_ACTIVE
    created_by_user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("id", "tenant_id", "organization_id", "user_id", mode="before")
    @classmethod
    def _validate_ids(cls, value: object) -> str:
        return _required_id(
            value,
            label="Service-principal identity",
            code="SERVICE_PRINCIPAL_ID_REQUIRED",
        )

    @field_validator("created_by_user_id", mode="before")
    @classmethod
    def _normalize_creator(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Service-principal name is required.",
            code="SERVICE_PRINCIPAL_NAME_REQUIRED",
        )[:128]

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: object) -> str:
        return normalize_optional_text(value)[:1000]

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> str:
        normalized = normalize_optional_text(value).lower() or SERVICE_PRINCIPAL_STATUS_ACTIVE
        if normalized not in {
            SERVICE_PRINCIPAL_STATUS_ACTIVE,
            SERVICE_PRINCIPAL_STATUS_DISABLED,
        }:
            raise ValidationError(
                "Service-principal status is invalid.",
                code="SERVICE_PRINCIPAL_STATUS_INVALID",
            )
        return normalized

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _normalize_datetimes(cls, value: object) -> datetime | None:
        return _optional_datetime(value)

    @model_validator(mode="after")
    def _initialize_timestamps(self) -> "ServicePrincipal":
        now = datetime.now(timezone.utc)
        if self.created_at is None:
            object.__setattr__(self, "created_at", now)
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", self.created_at)
        return self

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        user_id: str,
        name: str,
        description: str = "",
        created_by_user_id: str | None = None,
    ) -> "ServicePrincipal":
        return ServicePrincipal(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            user_id=user_id,
            name=name,
            description=description,
            created_by_user_id=created_by_user_id,
        )


@validated_dataclass
class ApiKeyCredential:
    id: str
    tenant_id: str
    service_principal_id: str
    name: str
    key_prefix: str
    secret_hash: str
    permission_scopes: tuple[str, ...] = field(default_factory=tuple)
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    created_by_user_id: str | None = None
    created_at: datetime | None = None

    @field_validator("id", "tenant_id", "service_principal_id", mode="before")
    @classmethod
    def _validate_ids(cls, value: object) -> str:
        return _required_id(
            value,
            label="API-key identity",
            code="API_KEY_ID_REQUIRED",
        )

    @field_validator("created_by_user_id", mode="before")
    @classmethod
    def _normalize_creator(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="API-key name is required.",
            code="API_KEY_NAME_REQUIRED",
        )[:128]

    @field_validator("key_prefix", "secret_hash", mode="before")
    @classmethod
    def _validate_secret_metadata(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="API-key secret metadata is required.",
            code="API_KEY_SECRET_REQUIRED",
        )

    @field_validator("permission_scopes", mode="before")
    @classmethod
    def _normalize_scopes(cls, value: object) -> tuple[str, ...]:
        if value in (None, ""):
            return ()
        return tuple(
            sorted(
                {
                    str(scope or "").strip().lower()
                    for scope in value
                    if str(scope or "").strip()
                }
            )
        )

    @field_validator("expires_at", "last_used_at", "revoked_at", "created_at", mode="before")
    @classmethod
    def _normalize_datetimes(cls, value: object) -> datetime | None:
        return _optional_datetime(value)

    @model_validator(mode="after")
    def _validate_lifecycle(self) -> "ApiKeyCredential":
        if not self.permission_scopes:
            raise ValidationError(
                "API keys require at least one permission scope.",
                code="API_KEY_SCOPE_REQUIRED",
            )
        now = datetime.now(timezone.utc)
        if self.created_at is None:
            object.__setattr__(self, "created_at", now)
        if self.expires_at is None or self.expires_at <= self.created_at:
            raise ValidationError(
                "API-key expiry must be after creation.",
                code="API_KEY_EXPIRY_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        tenant_id: str,
        service_principal_id: str,
        name: str,
        key_prefix: str,
        secret_hash: str,
        permission_scopes: tuple[str, ...],
        expires_at: datetime,
        created_by_user_id: str | None,
    ) -> "ApiKeyCredential":
        return ApiKeyCredential(
            id=generate_id(),
            tenant_id=tenant_id,
            service_principal_id=service_principal_id,
            name=name,
            key_prefix=key_prefix,
            secret_hash=secret_hash,
            permission_scopes=permission_scopes,
            expires_at=expires_at,
            created_by_user_id=created_by_user_id,
        )


@validated_dataclass(frozen=True)
class IssuedApiKey:
    credential: ApiKeyCredential
    token: str


__all__ = [
    "ApiKeyCredential",
    "IssuedApiKey",
    "SERVICE_PRINCIPAL_STATUS_ACTIVE",
    "SERVICE_PRINCIPAL_STATUS_DISABLED",
    "ServicePrincipal",
]
