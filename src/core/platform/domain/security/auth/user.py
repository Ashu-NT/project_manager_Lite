from __future__ import annotations

import re
from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from src.core.platform.domain.security.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.domain.security.authorization.roles.role_binding import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
    normalize_role_scope_type,
)

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
ACCOUNT_TYPE_HUMAN = "human"
ACCOUNT_TYPE_SERVICE = "service"
VALID_ACCOUNT_TYPES = frozenset({ACCOUNT_TYPE_HUMAN, ACCOUNT_TYPE_SERVICE})


def normalize_auth_username(value: object) -> str:
    return normalize_required_text(
        value,
        message="Username is required.",
        code="USERNAME_REQUIRED",
    ).lower()


def normalize_auth_password_hash(value: object) -> str:
    return normalize_required_text(
        value,
        message="Password hash is required.",
        code="PASSWORD_HASH_REQUIRED",
    )


def normalize_auth_optional_text(value: object) -> str | None:
    normalized = normalize_optional_text(value)
    return normalized or None


def normalize_auth_email(value: object) -> str | None:
    normalized = normalize_optional_text(value).lower() or None
    if normalized is None:
        return None
    if not _EMAIL_RE.match(normalized):
        raise ValidationError(
            "Invalid email format.",
            code="INVALID_EMAIL",
        )
    return normalized


def validate_auth_email(value: object) -> None:
    normalize_auth_email(value)


def normalize_auth_identity_provider(value: object) -> str | None:
    normalized = normalize_optional_text(value).lower()
    return normalized or None


def normalize_auth_federated_subject(value: object) -> str | None:
    normalized = normalize_optional_text(value)
    return normalized or None


def normalize_auth_device_label(value: object) -> str | None:
    normalized = normalize_optional_text(value)
    return normalized or None


def normalize_auth_session_timeout_override(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Session timeout override must be an integer number of minutes.",
            code="AUTH_SESSION_TIMEOUT_INVALID",
        ) from exc
    if normalized < 5 or normalized > 1_440:
        raise ValidationError(
            "Session timeout override must be between 5 and 1440 minutes.",
            code="AUTH_SESSION_TIMEOUT_INVALID",
        )
    return normalized


def normalize_auth_session_revision(value: object) -> int:
    try:
        normalized = int(value if value not in (None, "") else 1)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Session revision must be a positive integer.",
            code="AUTH_SESSION_REVISION_INVALID",
        ) from exc
    if normalized < 1:
        raise ValidationError(
            "Session revision must be a positive integer.",
            code="AUTH_SESSION_REVISION_INVALID",
        )
    return normalized


def normalize_auth_failed_login_attempts(value: object) -> int:
    try:
        normalized = int(value if value not in (None, "") else 0)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Failed login attempts must be zero or greater.",
            code="AUTH_FAILED_LOGIN_ATTEMPTS_INVALID",
        ) from exc
    if normalized < 0:
        raise ValidationError(
            "Failed login attempts must be zero or greater.",
            code="AUTH_FAILED_LOGIN_ATTEMPTS_INVALID",
        )
    return normalized


def normalize_auth_version(value: object) -> int:
    try:
        normalized = int(value if value not in (None, "") else 1)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "User version must be a positive integer.",
            code="AUTH_USER_VERSION_INVALID",
        ) from exc
    if normalized < 1:
        raise ValidationError(
            "User version must be a positive integer.",
            code="AUTH_USER_VERSION_INVALID",
        )
    return normalized


def normalize_auth_datetime(value: object, *, code: str) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Authentication timestamps must be valid datetimes.",
            code=code,
        )
    return ensure_utc_datetime(value)


def normalize_auth_role_id(value: object) -> str:
    return normalize_required_text(
        value,
        message="Role id is required.",
        code="ROLE_ID_REQUIRED",
    )


def normalize_auth_permission_id(value: object) -> str:
    return normalize_required_text(
        value,
        message="Permission id is required.",
        code="PERMISSION_ID_REQUIRED",
    )


def normalize_auth_role_name(value: object) -> str:
    return normalize_required_text(
        value,
        message="Role name is required.",
        code="AUTH_ROLE_NAME_REQUIRED",
    ).lower()


def normalize_auth_permission_code(value: object) -> str:
    return normalize_required_text(
        value,
        message="Permission code is required.",
        code="AUTH_PERMISSION_CODE_REQUIRED",
    ).lower()


@validated_dataclass
class UserAccount:
    id: str
    username: str
    password_hash: str
    account_type: str = ACCOUNT_TYPE_HUMAN
    display_name: str | None = None
    email: str | None = None
    identity_provider: str | None = None
    federated_subject: str | None = None
    mfa_secret: str | None = None
    mfa_enabled: bool = False
    session_timeout_minutes_override: int | None = None
    session_revision: int = 1
    last_login_auth_method: str | None = None
    last_login_device_label: str | None = None
    is_active: bool = True
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    session_expires_at: datetime | None = None
    password_changed_at: datetime | None = None
    must_change_password: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1
    active_session_id: str | None = None

    @field_validator("username", mode="before")
    @classmethod
    def _validate_username(cls, value: object) -> str:
        return normalize_auth_username(value)

    @field_validator("password_hash", mode="before")
    @classmethod
    def _validate_password_hash(cls, value: object) -> str:
        return normalize_auth_password_hash(value)

    @field_validator("account_type", mode="before")
    @classmethod
    def _validate_account_type(cls, value: object) -> str:
        normalized = normalize_optional_text(value).lower() or ACCOUNT_TYPE_HUMAN
        if normalized not in VALID_ACCOUNT_TYPES:
            raise ValidationError(
                "Account type is invalid.",
                code="AUTH_ACCOUNT_TYPE_INVALID",
            )
        return normalized

    @field_validator("display_name", "mfa_secret", "last_login_auth_method", mode="before")
    @classmethod
    def _normalize_optional_text_fields(cls, value: object) -> str | None:
        return normalize_auth_optional_text(value)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> str | None:
        return normalize_auth_email(value)

    @field_validator("identity_provider", mode="before")
    @classmethod
    def _normalize_identity_provider(cls, value: object) -> str | None:
        return normalize_auth_identity_provider(value)

    @field_validator("federated_subject", mode="before")
    @classmethod
    def _normalize_federated_subject(cls, value: object) -> str | None:
        return normalize_auth_federated_subject(value)

    @field_validator("last_login_device_label", mode="before")
    @classmethod
    def _normalize_device_label(cls, value: object) -> str | None:
        return normalize_auth_device_label(value)

    @field_validator("session_timeout_minutes_override", mode="before")
    @classmethod
    def _validate_session_timeout_override(cls, value: object) -> int | None:
        return normalize_auth_session_timeout_override(value)

    @field_validator("session_revision", mode="before")
    @classmethod
    def _validate_session_revision(cls, value: object) -> int:
        return normalize_auth_session_revision(value)

    @field_validator("failed_login_attempts", mode="before")
    @classmethod
    def _validate_failed_login_attempts(cls, value: object) -> int:
        return normalize_auth_failed_login_attempts(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_auth_version(value)

    @field_validator("active_session_id", mode="before")
    @classmethod
    def _normalize_active_session_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator(
        "locked_until",
        "last_login_at",
        "session_expires_at",
        "password_changed_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def _validate_datetimes(cls, value: object) -> datetime | None:
        return normalize_auth_datetime(value, code="AUTH_TIMESTAMP_INVALID")

    @model_validator(mode="after")
    def _validate_federated_identity_pair(self) -> "UserAccount":
        if bool(self.identity_provider) != bool(self.federated_subject):
            raise ValidationError(
                "Identity provider and federated subject must be set together.",
                code="FEDERATED_IDENTITY_INCOMPLETE",
            )
        return self

    @staticmethod
    def create(
        username: str,
        password_hash: str,
        display_name: str | None = None,
        email: str | None = None,
        is_active: bool = True,
        *,
        identity_provider: str | None = None,
        federated_subject: str | None = None,
        session_timeout_minutes_override: int | str | None = None,
        must_change_password: bool = False,
        account_type: str = ACCOUNT_TYPE_HUMAN,
    ) -> "UserAccount":
        now = datetime.now(timezone.utc)
        return UserAccount(
            id=generate_id(),
            username=username,
            password_hash=password_hash,
            account_type=account_type,
            display_name=display_name,
            email=email,
            identity_provider=identity_provider,
            federated_subject=federated_subject,
            mfa_secret=None,
            mfa_enabled=False,
            session_timeout_minutes_override=session_timeout_minutes_override,
            session_revision=1,
            last_login_auth_method=None,
            last_login_device_label=None,
            is_active=is_active,
            failed_login_attempts=0,
            locked_until=None,
            last_login_at=None,
            session_expires_at=None,
            password_changed_at=now,
            must_change_password=must_change_password,
            created_at=now,
            updated_at=now,
            version=1,
            active_session_id=None,
        )


@validated_dataclass
class Role:
    id: str
    name: str
    description: str = ""
    is_system: bool = True
    tenant_id: str | None = None
    display_name: str = ""
    allowed_scope_type: str = ROLE_SCOPE_TENANT
    is_assignable: bool = True
    status: str = "active"
    policy_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_auth_role_id(value)

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_auth_role_name(value)

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _normalize_tenant_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("display_name", mode="before")
    @classmethod
    def _normalize_display_name(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("allowed_scope_type", mode="before")
    @classmethod
    def _validate_allowed_scope_type(cls, value: object) -> str:
        return normalize_role_scope_type(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> str:
        normalized = normalize_required_text(
            value,
            message="Role status is required.",
            code="AUTH_ROLE_STATUS_REQUIRED",
        ).lower()
        if normalized not in {"active", "inactive", "retired"}:
            raise ValidationError(
                f"Unsupported role status '{normalized}'.",
                code="AUTH_ROLE_STATUS_INVALID",
            )
        return normalized

    @field_validator("policy_version", mode="before")
    @classmethod
    def _validate_policy_version(cls, value: object) -> int:
        try:
            normalized = int(value if value not in (None, "") else 1)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Role policy version must be a positive integer.",
                code="AUTH_ROLE_POLICY_VERSION_INVALID",
            ) from exc
        if normalized < 1:
            raise ValidationError(
                "Role policy version must be a positive integer.",
                code="AUTH_ROLE_POLICY_VERSION_INVALID",
            )
        return normalized

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _normalize_timestamps(cls, value: object) -> datetime | None:
        return normalize_auth_datetime(
            value,
            code="AUTH_ROLE_TIMESTAMP_INVALID",
        )

    @model_validator(mode="after")
    def _initialize_metadata(self) -> "Role":
        if self.is_system and self.tenant_id is not None:
            raise ValidationError(
                "System role definitions cannot be tenant-owned.",
                code="AUTH_SYSTEM_ROLE_TENANT_INVALID",
            )
        if not self.is_system and self.tenant_id is None:
            raise ValidationError(
                "Custom role definitions require tenant ownership.",
                code="AUTH_CUSTOM_ROLE_TENANT_REQUIRED",
            )
        if not self.is_system and self.allowed_scope_type == ROLE_SCOPE_PLATFORM:
            raise ValidationError(
                "Tenant-owned roles cannot use platform scope.",
                code="AUTH_CUSTOM_ROLE_SCOPE_INVALID",
            )
        now = datetime.now(timezone.utc)
        if not self.display_name:
            object.__setattr__(
                self,
                "display_name",
                self.name.replace("_", " ").title(),
            )
        if self.created_at is None:
            object.__setattr__(self, "created_at", now)
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", self.created_at)
        return self

    @staticmethod
    def create(
        name: str,
        description: str = "",
        is_system: bool = True,
        *,
        tenant_id: str | None = None,
        display_name: str = "",
        allowed_scope_type: str = ROLE_SCOPE_TENANT,
        is_assignable: bool = True,
        policy_version: int = 1,
    ) -> "Role":
        now = datetime.now(timezone.utc)
        return Role(
            id=generate_id(),
            name=name,
            description=description,
            is_system=is_system,
            tenant_id=tenant_id,
            display_name=display_name,
            allowed_scope_type=allowed_scope_type,
            is_assignable=is_assignable,
            status="active",
            policy_version=policy_version,
            created_at=now,
            updated_at=now,
        )


@validated_dataclass
class Permission:
    id: str
    code: str
    description: str = ""

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_auth_permission_id(value)

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, value: object) -> str:
        return normalize_auth_permission_code(value)

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: object) -> str:
        return normalize_optional_text(value)

    @staticmethod
    def create(code: str, description: str = "") -> "Permission":
        return Permission(
            id=generate_id(),
            code=code,
            description=description,
        )


@validated_dataclass
class RolePermissionBinding:
    id: str
    role_id: str
    permission_id: str

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Role-permission binding id is required.",
            code="AUTH_ROLE_PERMISSION_BINDING_ID_REQUIRED",
        )

    @field_validator("role_id", mode="before")
    @classmethod
    def _validate_role_id(cls, value: object) -> str:
        return normalize_auth_role_id(value)

    @field_validator("permission_id", mode="before")
    @classmethod
    def _validate_permission_id(cls, value: object) -> str:
        return normalize_auth_permission_id(value)

    @staticmethod
    def create(role_id: str, permission_id: str) -> "RolePermissionBinding":
        return RolePermissionBinding(
            id=generate_id(),
            role_id=role_id,
            permission_id=permission_id,
        )


__all__ = [
    "ACCOUNT_TYPE_HUMAN",
    "ACCOUNT_TYPE_SERVICE",
    "Permission",
    "Role",
    "RolePermissionBinding",
    "UserAccount",
    "normalize_auth_device_label",
    "normalize_auth_email",
    "normalize_auth_federated_subject",
    "normalize_auth_identity_provider",
    "normalize_auth_password_hash",
    "normalize_auth_session_revision",
    "normalize_auth_session_timeout_override",
    "normalize_auth_username",
    "validate_auth_email",
]
