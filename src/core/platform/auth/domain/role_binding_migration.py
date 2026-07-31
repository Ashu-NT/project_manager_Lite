from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.auth.domain.role_binding import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    normalize_role_scope_type,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_required_text,
    validated_dataclass,
)


# RBAC-TRANSITION-ONLY: Remove after CANONICAL_ONLY and the ADR-003 evidence
# retention gate. These records make legacy-to-canonical backfill reversible.
AUTHORIZATION_MIGRATION_BATCH_PREPARED = "prepared"
AUTHORIZATION_MIGRATION_BATCH_APPLIED = "applied"
AUTHORIZATION_MIGRATION_BATCH_ROLLED_BACK = "rolled_back"
AUTHORIZATION_MIGRATION_BATCH_STATUSES = frozenset(
    {
        AUTHORIZATION_MIGRATION_BATCH_PREPARED,
        AUTHORIZATION_MIGRATION_BATCH_APPLIED,
        AUTHORIZATION_MIGRATION_BATCH_ROLLED_BACK,
    }
)

LEGACY_BINDING_MIGRATION_READY = "ready"
LEGACY_BINDING_MIGRATION_QUARANTINED = "quarantined"
LEGACY_BINDING_MIGRATION_APPLIED = "applied"
LEGACY_BINDING_MIGRATION_ROLLED_BACK = "rolled_back"
LEGACY_BINDING_MIGRATION_STATUSES = frozenset(
    {
        LEGACY_BINDING_MIGRATION_READY,
        LEGACY_BINDING_MIGRATION_QUARANTINED,
        LEGACY_BINDING_MIGRATION_APPLIED,
        LEGACY_BINDING_MIGRATION_ROLLED_BACK,
    }
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _normalize_sha256(value: object, *, code: str) -> str:
    normalized = normalize_required_text(
        value,
        message="Migration snapshot SHA-256 is required.",
        code=code,
    ).lower()
    if _SHA256_RE.fullmatch(normalized) is None:
        raise ValidationError(
            "Migration snapshot SHA-256 must be a 64-character hex digest.",
            code=code,
        )
    return normalized


def _normalize_migration_datetime(
    value: object,
    *,
    code: str,
    required: bool = False,
) -> datetime | None:
    if value in (None, ""):
        if required:
            raise ValidationError(
                "Migration timestamp is required.",
                code=code,
            )
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Migration timestamp must be a valid datetime.",
            code=code,
        )
    return ensure_utc_datetime(value)


def legacy_role_binding_snapshot_sha256(
    *,
    legacy_binding_id: str,
    user_id: str,
    role_id: str,
    organization_id: str | None,
) -> str:
    payload = {
        "legacy_binding_id": normalize_required_text(
            legacy_binding_id,
            message="Legacy role-binding id is required.",
            code="AUTH_MIGRATION_LEGACY_BINDING_ID_REQUIRED",
        ),
        "organization_id": normalize_optional_identifier(organization_id),
        "role_id": normalize_required_text(
            role_id,
            message="Legacy role id is required.",
            code="AUTH_MIGRATION_SOURCE_ROLE_ID_REQUIRED",
        ),
        "user_id": normalize_required_text(
            user_id,
            message="Legacy user id is required.",
            code="AUTH_MIGRATION_SOURCE_USER_ID_REQUIRED",
        ),
    }
    serialized = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


@validated_dataclass
class AuthorizationMigrationBatch:
    id: str
    source_inventory_sha256: str
    source_record_count: int
    reviewed_plan_sha256: str
    reviewer_id: str
    reviewed_at: datetime
    status: str
    created_by: str
    created_at: datetime
    applied_at: datetime | None = None
    rolled_back_at: datetime | None = None
    version: int = 1

    @field_validator("id", "created_by", "reviewer_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Migration batch references are required.",
            code="AUTH_MIGRATION_BATCH_REFERENCE_REQUIRED",
        )

    @field_validator("source_inventory_sha256", mode="before")
    @classmethod
    def _validate_inventory_hash(cls, value: object) -> str:
        return _normalize_sha256(
            value,
            code="AUTH_MIGRATION_INVENTORY_HASH_INVALID",
        )

    @field_validator("reviewed_plan_sha256", mode="before")
    @classmethod
    def _validate_plan_hash(cls, value: object) -> str:
        return _normalize_sha256(
            value,
            code="AUTH_MIGRATION_PLAN_HASH_INVALID",
        )

    @field_validator("source_record_count", mode="before")
    @classmethod
    def _validate_record_count(cls, value: object) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Migration source record count must be non-negative.",
                code="AUTH_MIGRATION_RECORD_COUNT_INVALID",
            ) from exc
        if normalized < 0:
            raise ValidationError(
                "Migration source record count must be non-negative.",
                code="AUTH_MIGRATION_RECORD_COUNT_INVALID",
            )
        return normalized

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> str:
        normalized = normalize_required_text(
            value,
            message="Migration batch status is required.",
            code="AUTH_MIGRATION_BATCH_STATUS_REQUIRED",
        ).lower()
        if normalized not in AUTHORIZATION_MIGRATION_BATCH_STATUSES:
            raise ValidationError(
                f"Unsupported migration batch status '{normalized}'.",
                code="AUTH_MIGRATION_BATCH_STATUS_INVALID",
            )
        return normalized

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: object) -> datetime:
        return _normalize_migration_datetime(
            value,
            code="AUTH_MIGRATION_BATCH_CREATED_AT_REQUIRED",
            required=True,
        )

    @field_validator("reviewed_at", mode="before")
    @classmethod
    def _validate_reviewed_at(cls, value: object) -> datetime:
        return _normalize_migration_datetime(
            value,
            code="AUTH_MIGRATION_BATCH_REVIEWED_AT_REQUIRED",
            required=True,
        )

    @field_validator("applied_at", "rolled_back_at", mode="before")
    @classmethod
    def _validate_optional_timestamps(cls, value: object) -> datetime | None:
        return _normalize_migration_datetime(
            value,
            code="AUTH_MIGRATION_BATCH_TIMESTAMP_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Migration batch version must be positive.",
                code="AUTH_MIGRATION_BATCH_VERSION_INVALID",
            ) from exc
        if normalized < 1:
            raise ValidationError(
                "Migration batch version must be positive.",
                code="AUTH_MIGRATION_BATCH_VERSION_INVALID",
            )
        return normalized

    @model_validator(mode="after")
    def _validate_lifecycle(self) -> "AuthorizationMigrationBatch":
        if self.reviewed_at > self.created_at:
            raise ValidationError(
                "Migration batch review cannot postdate batch creation.",
                code="AUTH_MIGRATION_BATCH_REVIEW_INVALID",
            )
        if self.status == AUTHORIZATION_MIGRATION_BATCH_PREPARED:
            if self.applied_at is not None or self.rolled_back_at is not None:
                raise ValidationError(
                    "A prepared migration batch cannot have completion timestamps.",
                    code="AUTH_MIGRATION_BATCH_LIFECYCLE_INVALID",
                )
        elif self.status == AUTHORIZATION_MIGRATION_BATCH_APPLIED:
            if self.applied_at is None or self.rolled_back_at is not None:
                raise ValidationError(
                    "An applied migration batch requires only an applied timestamp.",
                    code="AUTH_MIGRATION_BATCH_LIFECYCLE_INVALID",
                )
        elif self.applied_at is None or self.rolled_back_at is None:
            raise ValidationError(
                "A rolled-back migration batch requires apply and rollback timestamps.",
                code="AUTH_MIGRATION_BATCH_LIFECYCLE_INVALID",
            )
        if (
            self.applied_at is not None
            and self.applied_at < self.created_at
        ):
            raise ValidationError(
                "Migration application cannot predate batch creation.",
                code="AUTH_MIGRATION_BATCH_LIFECYCLE_INVALID",
            )
        if (
            self.rolled_back_at is not None
            and self.applied_at is not None
            and self.rolled_back_at < self.applied_at
        ):
            raise ValidationError(
                "Migration rollback cannot predate application.",
                code="AUTH_MIGRATION_BATCH_LIFECYCLE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        source_inventory_sha256: str,
        source_record_count: int,
        reviewed_plan_sha256: str,
        reviewer_id: str,
        reviewed_at: datetime,
        created_by: str,
    ) -> "AuthorizationMigrationBatch":
        return AuthorizationMigrationBatch(
            id=generate_id(),
            source_inventory_sha256=source_inventory_sha256,
            source_record_count=source_record_count,
            reviewed_plan_sha256=reviewed_plan_sha256,
            reviewer_id=reviewer_id,
            reviewed_at=reviewed_at,
            status=AUTHORIZATION_MIGRATION_BATCH_PREPARED,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
        )


@validated_dataclass
class LegacyRoleBindingMigrationRecord:
    id: str
    batch_id: str
    legacy_binding_id: str
    source_user_id: str
    source_role_id: str
    source_organization_id: str | None
    source_snapshot_sha256: str
    status: str
    quarantine_reason_code: str | None
    resolved_tenant_id: str | None
    resolved_scope_type: str | None
    resolved_scope_id: str | None
    canonical_binding_id: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int = 1

    @field_validator(
        "id",
        "batch_id",
        "legacy_binding_id",
        "source_user_id",
        "source_role_id",
        mode="before",
    )
    @classmethod
    def _validate_required_ids(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Migration record references are required.",
            code="AUTH_MIGRATION_RECORD_REFERENCE_REQUIRED",
        )

    @field_validator(
        "source_organization_id",
        "resolved_tenant_id",
        "resolved_scope_id",
        "canonical_binding_id",
        "reviewed_by",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("source_snapshot_sha256", mode="before")
    @classmethod
    def _validate_source_hash(cls, value: object) -> str:
        return _normalize_sha256(
            value,
            code="AUTH_MIGRATION_SOURCE_HASH_INVALID",
        )

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> str:
        normalized = normalize_required_text(
            value,
            message="Migration record status is required.",
            code="AUTH_MIGRATION_RECORD_STATUS_REQUIRED",
        ).lower()
        if normalized not in LEGACY_BINDING_MIGRATION_STATUSES:
            raise ValidationError(
                f"Unsupported migration record status '{normalized}'.",
                code="AUTH_MIGRATION_RECORD_STATUS_INVALID",
            )
        return normalized

    @field_validator("quarantine_reason_code", mode="before")
    @classmethod
    def _normalize_reason(cls, value: object) -> str | None:
        normalized = normalize_optional_identifier(value)
        return normalized.upper() if normalized is not None else None

    @field_validator("resolved_scope_type", mode="before")
    @classmethod
    def _normalize_scope_type(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return normalize_role_scope_type(value)

    @field_validator("reviewed_at", mode="before")
    @classmethod
    def _validate_reviewed_at(cls, value: object) -> datetime | None:
        return _normalize_migration_datetime(
            value,
            code="AUTH_MIGRATION_REVIEWED_AT_INVALID",
        )

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_required_timestamps(cls, value: object) -> datetime:
        return _normalize_migration_datetime(
            value,
            code="AUTH_MIGRATION_RECORD_TIMESTAMP_REQUIRED",
            required=True,
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Migration record version must be positive.",
                code="AUTH_MIGRATION_RECORD_VERSION_INVALID",
            ) from exc
        if normalized < 1:
            raise ValidationError(
                "Migration record version must be positive.",
                code="AUTH_MIGRATION_RECORD_VERSION_INVALID",
            )
        return normalized

    @model_validator(mode="after")
    def _validate_snapshot_and_resolution(
        self,
    ) -> "LegacyRoleBindingMigrationRecord":
        expected_hash = legacy_role_binding_snapshot_sha256(
            legacy_binding_id=self.legacy_binding_id,
            user_id=self.source_user_id,
            role_id=self.source_role_id,
            organization_id=self.source_organization_id,
        )
        if self.source_snapshot_sha256 != expected_hash:
            raise ValidationError(
                "Legacy role-binding snapshot does not match its digest.",
                code="AUTH_MIGRATION_SOURCE_HASH_MISMATCH",
            )
        if self.updated_at < self.created_at:
            raise ValidationError(
                "Migration record update cannot predate creation.",
                code="AUTH_MIGRATION_RECORD_TIMESTAMP_INVALID",
            )
        if (self.reviewed_by is None) != (self.reviewed_at is None):
            raise ValidationError(
                "Migration reviewer and review timestamp must be recorded together.",
                code="AUTH_MIGRATION_REVIEW_INVALID",
            )
        if self.reviewed_at is not None and self.reviewed_at > self.created_at:
            raise ValidationError(
                "Migration review cannot postdate record creation.",
                code="AUTH_MIGRATION_REVIEW_INVALID",
            )

        if self.status == LEGACY_BINDING_MIGRATION_QUARANTINED:
            if self.quarantine_reason_code is None:
                raise ValidationError(
                    "A quarantined binding requires a reason code.",
                    code="AUTH_MIGRATION_QUARANTINE_REASON_REQUIRED",
                )
            if self.canonical_binding_id is not None:
                raise ValidationError(
                    "A quarantined binding cannot reference a canonical binding.",
                    code="AUTH_MIGRATION_QUARANTINE_INVALID",
                )
            if any(
                value is not None
                for value in (
                    self.resolved_tenant_id,
                    self.resolved_scope_type,
                    self.resolved_scope_id,
                )
            ):
                raise ValidationError(
                    "A quarantined binding cannot claim a resolved scope.",
                    code="AUTH_MIGRATION_QUARANTINE_INVALID",
                )
            return self

        if self.quarantine_reason_code is not None:
            raise ValidationError(
                "Only quarantined bindings may carry a quarantine reason.",
                code="AUTH_MIGRATION_QUARANTINE_INVALID",
            )
        self._validate_resolved_scope()
        if self.reviewed_by is None:
            raise ValidationError(
                "A migration-ready binding requires explicit review.",
                code="AUTH_MIGRATION_REVIEW_REQUIRED",
            )
        if self.status in {
            LEGACY_BINDING_MIGRATION_APPLIED,
            LEGACY_BINDING_MIGRATION_ROLLED_BACK,
        } and self.canonical_binding_id is None:
            raise ValidationError(
                "Applied or rolled-back migration records require a canonical binding id.",
                code="AUTH_MIGRATION_CANONICAL_BINDING_REQUIRED",
            )
        if (
            self.status == LEGACY_BINDING_MIGRATION_READY
            and self.canonical_binding_id is not None
        ):
            raise ValidationError(
                "A ready migration record cannot already reference a canonical binding.",
                code="AUTH_MIGRATION_CANONICAL_BINDING_INVALID",
            )
        return self

    def _validate_resolved_scope(self) -> None:
        if self.resolved_scope_type is None:
            raise ValidationError(
                "A non-quarantined migration record requires a resolved scope.",
                code="AUTH_MIGRATION_SCOPE_REQUIRED",
            )
        if self.resolved_scope_type == ROLE_SCOPE_PLATFORM:
            valid = (
                self.resolved_tenant_id is None
                and self.resolved_scope_id is None
            )
        elif self.resolved_scope_type == ROLE_SCOPE_TENANT:
            valid = (
                self.resolved_tenant_id is not None
                and self.resolved_scope_id is None
            )
        else:
            valid = (
                self.resolved_tenant_id is not None
                and self.resolved_scope_id is not None
            )
        if not valid:
            raise ValidationError(
                "Resolved migration scope has an invalid tenant/resource shape.",
                code="AUTH_MIGRATION_SCOPE_INVALID",
            )


__all__ = [
    "AUTHORIZATION_MIGRATION_BATCH_APPLIED",
    "AUTHORIZATION_MIGRATION_BATCH_PREPARED",
    "AUTHORIZATION_MIGRATION_BATCH_ROLLED_BACK",
    "AUTHORIZATION_MIGRATION_BATCH_STATUSES",
    "AuthorizationMigrationBatch",
    "LEGACY_BINDING_MIGRATION_APPLIED",
    "LEGACY_BINDING_MIGRATION_QUARANTINED",
    "LEGACY_BINDING_MIGRATION_READY",
    "LEGACY_BINDING_MIGRATION_ROLLED_BACK",
    "LEGACY_BINDING_MIGRATION_STATUSES",
    "LegacyRoleBindingMigrationRecord",
    "legacy_role_binding_snapshot_sha256",
]
