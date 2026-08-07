from __future__ import annotations

from datetime import datetime, timezone
import re

from pydantic import field_validator, model_validator

from src.core.platform.domain.security.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.domain.security.authorization.roles.role_binding import normalize_role_scope_type
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_required_text,
    validated_dataclass,
)


def _normalize_delegation_datetime(
    value: object,
    *,
    code: str,
    required: bool = False,
) -> datetime | None:
    if value in (None, ""):
        if required:
            raise ValidationError(
                "Role delegation timestamp is required.",
                code=code,
            )
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Role delegation timestamp must be a valid datetime.",
            code=code,
        )
    return ensure_utc_datetime(value)


@validated_dataclass
class RoleDelegationPolicy:
    """Explicit authority for one actor role to assign another role."""

    id: str
    tenant_id: str | None
    actor_role_id: str
    assignable_role_id: str
    target_scope_type: str
    assignable_role_policy_version: int
    assignable_permission_set_hash: str
    created_by: str
    created_at: datetime
    revoked_at: datetime | None = None

    @field_validator(
        "id",
        "actor_role_id",
        "assignable_role_id",
        "created_by",
        mode="before",
    )
    @classmethod
    def _validate_required_ids(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Role delegation references are required.",
            code="AUTH_ROLE_DELEGATION_REFERENCE_REQUIRED",
        )

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _normalize_tenant_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("target_scope_type", mode="before")
    @classmethod
    def _validate_scope_type(cls, value: object) -> str:
        return normalize_role_scope_type(value)

    @field_validator("assignable_role_policy_version", mode="before")
    @classmethod
    def _validate_policy_version(cls, value: object) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Delegated role policy version must be a positive integer.",
                code="AUTH_ROLE_DELEGATION_POLICY_VERSION_INVALID",
            ) from exc
        if normalized < 1:
            raise ValidationError(
                "Delegated role policy version must be a positive integer.",
                code="AUTH_ROLE_DELEGATION_POLICY_VERSION_INVALID",
            )
        return normalized

    @field_validator("assignable_permission_set_hash", mode="before")
    @classmethod
    def _validate_permission_set_hash(cls, value: object) -> str:
        normalized = normalize_required_text(
            value,
            message="Delegated permission-set hash is required.",
            code="AUTH_ROLE_DELEGATION_PERMISSION_HASH_REQUIRED",
        ).lower()
        if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
            raise ValidationError(
                "Delegated permission-set hash must be a SHA-256 digest.",
                code="AUTH_ROLE_DELEGATION_PERMISSION_HASH_INVALID",
            )
        return normalized

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: object) -> datetime:
        return _normalize_delegation_datetime(
            value,
            code="AUTH_ROLE_DELEGATION_CREATED_AT_REQUIRED",
            required=True,
        )

    @field_validator("revoked_at", mode="before")
    @classmethod
    def _validate_revoked_at(cls, value: object) -> datetime | None:
        return _normalize_delegation_datetime(
            value,
            code="AUTH_ROLE_DELEGATION_REVOKED_AT_INVALID",
        )

    @model_validator(mode="after")
    def _validate_lifecycle(self) -> "RoleDelegationPolicy":
        if self.revoked_at is not None and self.revoked_at < self.created_at:
            raise ValidationError(
                "Role delegation revocation cannot predate creation.",
                code="AUTH_ROLE_DELEGATION_REVOCATION_INVALID",
            )
        return self

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    @staticmethod
    def create(
        *,
        actor_role_id: str,
        assignable_role_id: str,
        target_scope_type: str,
        assignable_role_policy_version: int,
        assignable_permission_set_hash: str,
        created_by: str,
        tenant_id: str | None = None,
    ) -> "RoleDelegationPolicy":
        return RoleDelegationPolicy(
            id=generate_id(),
            tenant_id=tenant_id,
            actor_role_id=actor_role_id,
            assignable_role_id=assignable_role_id,
            target_scope_type=target_scope_type,
            assignable_role_policy_version=assignable_role_policy_version,
            assignable_permission_set_hash=assignable_permission_set_hash,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
            revoked_at=None,
        )


__all__ = ["RoleDelegationPolicy"]
