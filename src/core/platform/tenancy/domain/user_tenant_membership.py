from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import re

from pydantic import field_validator, model_validator

from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.common.ids import generate_id


MEMBERSHIP_STATUS_INVITED = "invited"
MEMBERSHIP_STATUS_ACTIVE = "active"
MEMBERSHIP_STATUS_SUSPENDED = "suspended"
MEMBERSHIP_STATUS_REMOVED = "removed"
MEMBERSHIP_STATUSES = frozenset(
    {
        MEMBERSHIP_STATUS_INVITED,
        MEMBERSHIP_STATUS_ACTIVE,
        MEMBERSHIP_STATUS_SUSPENDED,
        MEMBERSHIP_STATUS_REMOVED,
    }
)
_INVITATION_TOKEN_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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


def normalize_user_tenant_membership_status(value: object) -> str:
    normalized = normalize_required_text(
        value,
        message="Membership status is required.",
        code="USER_TENANT_MEMBERSHIP_STATUS_REQUIRED",
    ).lower()
    if normalized not in MEMBERSHIP_STATUSES:
        raise ValidationError(
            f"Unsupported membership status '{normalized}'.",
            code="USER_TENANT_MEMBERSHIP_STATUS_INVALID",
        )
    return normalized


def normalize_membership_invitation_token_hash(value: object) -> str | None:
    normalized = normalize_optional_text(value).lower() or None
    if normalized is not None and not _INVITATION_TOKEN_HASH_PATTERN.fullmatch(
        normalized
    ):
        raise ValidationError(
            "Invitation token hash must be a SHA-256 hexadecimal digest.",
            code="USER_TENANT_MEMBERSHIP_INVITATION_TOKEN_HASH_INVALID",
        )
    return normalized


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
    status: str = MEMBERSHIP_STATUS_ACTIVE
    is_active: bool = True
    tenant_role: str = "member"
    invited_by_user_id: str | None = None
    invited_at: datetime | None = None
    invitation_expires_at: datetime | None = None
    invitation_token_hash: str | None = None
    accepted_at: datetime | None = None
    joined_at: datetime | None = None
    suspended_at: datetime | None = None
    revoked_at: datetime | None = None
    removed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

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

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> str:
        return normalize_user_tenant_membership_status(value)

    @field_validator("tenant_role", mode="before")
    @classmethod
    def _normalize_tenant_role(cls, value: object) -> str:
        return normalize_user_tenant_membership_role(value)

    @field_validator("invited_by_user_id", mode="before")
    @classmethod
    def _normalize_invited_by_user_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("invitation_token_hash", mode="before")
    @classmethod
    def _normalize_invitation_token_hash(cls, value: object) -> str | None:
        return normalize_membership_invitation_token_hash(value)

    @field_validator(
        "invited_at",
        "invitation_expires_at",
        "accepted_at",
        "joined_at",
        "suspended_at",
        "revoked_at",
        "removed_at",
        mode="before",
    )
    @classmethod
    def _validate_optional_timestamps(cls, value: object) -> datetime | None:
        return normalize_user_tenant_membership_datetime(
            value,
            code="USER_TENANT_MEMBERSHIP_TIMESTAMP_INVALID",
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

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        try:
            normalized = int(value if value not in (None, "") else 1)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Membership version must be a positive integer.",
                code="USER_TENANT_MEMBERSHIP_VERSION_INVALID",
            ) from exc
        if normalized < 1:
            raise ValidationError(
                "Membership version must be a positive integer.",
                code="USER_TENANT_MEMBERSHIP_VERSION_INVALID",
            )
        return normalized

    @model_validator(mode="after")
    def _validate_lifecycle_state(self) -> "UserTenantMembership":
        should_be_active = self.status == MEMBERSHIP_STATUS_ACTIVE
        if bool(self.is_active) != should_be_active:
            raise ValidationError(
                "Membership status and compatibility active flag do not match.",
                code="USER_TENANT_MEMBERSHIP_STATE_MISMATCH",
            )

        if self.status == MEMBERSHIP_STATUS_INVITED:
            if (
                self.invited_by_user_id is None
                or self.invited_at is None
                or self.invitation_expires_at is None
                or self.invitation_token_hash is None
            ):
                raise ValidationError(
                    "Invited memberships require issuer, invitation, expiry, and token metadata.",
                    code="USER_TENANT_MEMBERSHIP_INVITATION_REQUIRED",
                )
            if self.invitation_expires_at <= self.invited_at:
                raise ValidationError(
                    "Invitation expiry must be after invitation time.",
                    code="USER_TENANT_MEMBERSHIP_INVITATION_EXPIRY_INVALID",
                )
            if self.accepted_at is not None or self.joined_at is not None:
                raise ValidationError(
                    "An invited membership cannot already be accepted.",
                    code="USER_TENANT_MEMBERSHIP_INVITATION_STATE_INVALID",
                )
        elif self.invitation_token_hash is not None:
            raise ValidationError(
                "Only invited memberships can retain an invitation token hash.",
                code="USER_TENANT_MEMBERSHIP_INVITATION_TOKEN_STATE_INVALID",
            )

        if self.status in {
            MEMBERSHIP_STATUS_ACTIVE,
            MEMBERSHIP_STATUS_SUSPENDED,
        }:
            accepted_at = self.accepted_at or self.joined_at
            if accepted_at is None:
                raise ValidationError(
                    "Active or suspended memberships require acceptance metadata.",
                    code="USER_TENANT_MEMBERSHIP_ACCEPTED_AT_REQUIRED",
                )
            if self.accepted_at is None:
                object.__setattr__(self, "accepted_at", accepted_at)
            if self.joined_at is None:
                object.__setattr__(self, "joined_at", accepted_at)

        if (
            self.status == MEMBERSHIP_STATUS_SUSPENDED
            and self.suspended_at is None
        ):
            raise ValidationError(
                "Suspended memberships require a suspension timestamp.",
                code="USER_TENANT_MEMBERSHIP_SUSPENDED_AT_REQUIRED",
            )
        if self.status == MEMBERSHIP_STATUS_REMOVED and self.removed_at is None:
            raise ValidationError(
                "Removed memberships require a removal timestamp.",
                code="USER_TENANT_MEMBERSHIP_REMOVED_AT_REQUIRED",
            )
        if self.revoked_at is not None and self.status != MEMBERSHIP_STATUS_REMOVED:
            raise ValidationError(
                "Invitation revocation requires removed membership state.",
                code="USER_TENANT_MEMBERSHIP_REVOCATION_STATE_INVALID",
            )
        if (
            self.accepted_at is not None
            and self.invited_at is not None
            and self.accepted_at < self.invited_at
        ):
            raise ValidationError(
                "Membership acceptance cannot predate its invitation.",
                code="USER_TENANT_MEMBERSHIP_ACCEPTANCE_INVALID",
            )
        return self

    @staticmethod
    def create(
        user_id: str,
        tenant_id: str,
        *,
        tenant_role: str = "member",
        is_active: bool = True,
    ) -> "UserTenantMembership":
        now = datetime.now(timezone.utc)
        status = (
            MEMBERSHIP_STATUS_ACTIVE
            if is_active
            else MEMBERSHIP_STATUS_SUSPENDED
        )
        return UserTenantMembership(
            id=generate_id(),
            user_id=user_id,
            tenant_id=tenant_id,
            status=status,
            is_active=is_active,
            tenant_role=tenant_role,
            invited_by_user_id=None,
            invited_at=None,
            invitation_expires_at=None,
            invitation_token_hash=None,
            accepted_at=now,
            joined_at=now,
            suspended_at=None if is_active else now,
            revoked_at=None,
            removed_at=None,
            created_at=now,
            updated_at=now,
            version=1,
        )

    @staticmethod
    def invite(
        user_id: str,
        tenant_id: str,
        *,
        invited_by_user_id: str,
        expires_at: datetime,
        invitation_token_hash: str,
        invited_at: datetime | None = None,
    ) -> "UserTenantMembership":
        now = invited_at or datetime.now(timezone.utc)
        return UserTenantMembership(
            id=generate_id(),
            user_id=user_id,
            tenant_id=tenant_id,
            status=MEMBERSHIP_STATUS_INVITED,
            is_active=False,
            tenant_role="member",
            invited_by_user_id=invited_by_user_id,
            invited_at=now,
            invitation_expires_at=expires_at,
            invitation_token_hash=invitation_token_hash,
            accepted_at=None,
            joined_at=None,
            suspended_at=None,
            revoked_at=None,
            removed_at=None,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def invitation_is_expired(self, *, at: datetime | None = None) -> bool:
        if self.invitation_expires_at is None:
            return False
        evaluated_at = ensure_utc_datetime(at or datetime.now(timezone.utc))
        return evaluated_at >= self.invitation_expires_at

    def accept_invitation(
        self,
        *,
        accepted_at: datetime | None = None,
    ) -> "UserTenantMembership":
        if self.status != MEMBERSHIP_STATUS_INVITED:
            raise BusinessRuleError(
                "Only invited memberships can be accepted.",
                code="USER_TENANT_MEMBERSHIP_ACCEPT_INVALID_TRANSITION",
            )
        now = ensure_utc_datetime(accepted_at or datetime.now(timezone.utc))
        if self.invitation_is_expired(at=now):
            raise BusinessRuleError(
                "The tenant invitation has expired.",
                code="USER_TENANT_MEMBERSHIP_INVITATION_EXPIRED",
            )
        return replace(
            self,
            status=MEMBERSHIP_STATUS_ACTIVE,
            is_active=True,
            accepted_at=now,
            joined_at=now,
            invitation_token_hash=None,
            suspended_at=None,
            revoked_at=None,
            removed_at=None,
            updated_at=now,
        )

    def suspend(
        self,
        *,
        suspended_at: datetime | None = None,
    ) -> "UserTenantMembership":
        if self.status != MEMBERSHIP_STATUS_ACTIVE:
            raise BusinessRuleError(
                "Only active memberships can be suspended.",
                code="USER_TENANT_MEMBERSHIP_SUSPEND_INVALID_TRANSITION",
            )
        now = ensure_utc_datetime(suspended_at or datetime.now(timezone.utc))
        return replace(
            self,
            status=MEMBERSHIP_STATUS_SUSPENDED,
            is_active=False,
            suspended_at=now,
            updated_at=now,
        )

    def reactivate(
        self,
        *,
        reactivated_at: datetime | None = None,
    ) -> "UserTenantMembership":
        if self.status != MEMBERSHIP_STATUS_SUSPENDED:
            raise BusinessRuleError(
                "Only suspended memberships can be reactivated.",
                code="USER_TENANT_MEMBERSHIP_REACTIVATE_INVALID_TRANSITION",
            )
        now = ensure_utc_datetime(reactivated_at or datetime.now(timezone.utc))
        return replace(
            self,
            status=MEMBERSHIP_STATUS_ACTIVE,
            is_active=True,
            suspended_at=None,
            updated_at=now,
        )

    def revoke_invitation(
        self,
        *,
        revoked_at: datetime | None = None,
    ) -> "UserTenantMembership":
        if self.status != MEMBERSHIP_STATUS_INVITED:
            raise BusinessRuleError(
                "Only invited memberships can be revoked.",
                code="USER_TENANT_MEMBERSHIP_REVOKE_INVALID_TRANSITION",
            )
        now = ensure_utc_datetime(revoked_at or datetime.now(timezone.utc))
        return replace(
            self,
            status=MEMBERSHIP_STATUS_REMOVED,
            is_active=False,
            invitation_token_hash=None,
            revoked_at=now,
            removed_at=now,
            updated_at=now,
        )

    def remove(
        self,
        *,
        removed_at: datetime | None = None,
    ) -> "UserTenantMembership":
        if self.status not in {
            MEMBERSHIP_STATUS_ACTIVE,
            MEMBERSHIP_STATUS_SUSPENDED,
        }:
            raise BusinessRuleError(
                "Only active or suspended memberships can be removed.",
                code="USER_TENANT_MEMBERSHIP_REMOVE_INVALID_TRANSITION",
            )
        now = ensure_utc_datetime(removed_at or datetime.now(timezone.utc))
        return replace(
            self,
            status=MEMBERSHIP_STATUS_REMOVED,
            is_active=False,
            suspended_at=None,
            removed_at=now,
            updated_at=now,
        )

    def reinvite(
        self,
        *,
        invited_by_user_id: str,
        expires_at: datetime,
        invitation_token_hash: str,
        invited_at: datetime | None = None,
    ) -> "UserTenantMembership":
        if self.status not in {
            MEMBERSHIP_STATUS_INVITED,
            MEMBERSHIP_STATUS_REMOVED,
        }:
            raise BusinessRuleError(
                "Only invited or removed memberships can be reinvited.",
                code="USER_TENANT_MEMBERSHIP_REINVITE_INVALID_TRANSITION",
            )
        now = ensure_utc_datetime(invited_at or datetime.now(timezone.utc))
        return replace(
            self,
            status=MEMBERSHIP_STATUS_INVITED,
            is_active=False,
            invited_by_user_id=invited_by_user_id,
            invited_at=now,
            invitation_expires_at=expires_at,
            invitation_token_hash=invitation_token_hash,
            accepted_at=None,
            joined_at=None,
            suspended_at=None,
            revoked_at=None,
            removed_at=None,
            updated_at=now,
        )


__all__ = [
    "MEMBERSHIP_STATUSES",
    "MEMBERSHIP_STATUS_ACTIVE",
    "MEMBERSHIP_STATUS_INVITED",
    "MEMBERSHIP_STATUS_REMOVED",
    "MEMBERSHIP_STATUS_SUSPENDED",
    "UserTenantMembership",
    "normalize_user_tenant_membership_datetime",
    "normalize_user_tenant_membership_id",
    "normalize_membership_invitation_token_hash",
    "normalize_user_tenant_membership_role",
    "normalize_user_tenant_membership_status",
    "normalize_user_tenant_membership_tenant_id",
    "normalize_user_tenant_membership_user_id",
]
