from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.core.platform.application.security.auth.commands.federated_identity import (
    normalize_federated_subject,
    normalize_identity_provider,
    validate_federated_identity,
)
from src.core.platform.application.security.auth.credentials.authentication_transactions import (
    AuthenticationTransactions,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.repositories.security.auth import UserRepository
from src.core.platform.domain.security.auth import ACCOUNT_TYPE_HUMAN
from src.core.platform.domain.security.auth.credentials.mfa import verify_totp_code
from src.core.platform.domain.security.auth.credentials.passwords import (
    hash_password,
    password_needs_rehash,
    verify_password,
)

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount


class AuthenticationHandler:
    """Password and federated sign-in: verifies credentials and MFA, then records
    the outcome through AuthenticationTransactions."""

    def __init__(
        self,
        *,
        user_repo: UserRepository,
        transactions: AuthenticationTransactions,
    ) -> None:
        self._user_repo = user_repo
        self._transactions = transactions

    def authenticate(
        self,
        username: str,
        raw_password: str,
        *,
        mfa_code: str | None = None,
        device_label: str | None = None,
    ) -> UserAccount:
        normalized = (username or "").strip().lower()
        now = datetime.now(UTC)
        user = self._user_repo.get_by_username(normalized)
        if (
            not user
            or not user.is_active
            or getattr(user, "account_type", ACCOUNT_TYPE_HUMAN) != ACCOUNT_TYPE_HUMAN
        ):
            self._transactions.persist_standalone_login_denial(
                username=normalized,
                user=user,
                reason="invalid_credentials",
            )
            raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
        if user.locked_until is not None and user.locked_until <= now:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.updated_at = now
        if user.locked_until is not None and user.locked_until > now:
            self._transactions.persist_standalone_login_denial(
                username=normalized,
                user=user,
                reason="locked_out",
                details={
                    "locked_until": user.locked_until.isoformat(),
                },
            )
            raise ValidationError(
                f"Account is locked until {user.locked_until.isoformat()}.",
                code="AUTH_LOCKED",
            )
        if not verify_password(raw_password, user.password_hash):
            self._transactions.register_failed_login(
                user,
                username=normalized,
                occurred_at=now,
                reason="invalid_credentials",
            )
            raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
        if bool(getattr(user, "mfa_enabled", False)) and not verify_totp_code(
            getattr(user, "mfa_secret", None),
            mfa_code,
            at_time=now,
        ):
            reason = "mfa_required" if not str(mfa_code or "").strip() else "mfa_invalid"
            self._transactions.register_failed_login(
                user,
                username=normalized,
                occurred_at=now,
                reason=reason,
            )
            message = (
                "Multi-factor authentication code is required."
                if reason == "mfa_required"
                else "Invalid multi-factor authentication code."
            )
            code = (
                "AUTH_MFA_REQUIRED"
                if reason == "mfa_required"
                else "AUTH_MFA_FAILED"
            )
            raise ValidationError(message, code=code)
        if user.password_hash.startswith("$argon2id$") and password_needs_rehash(
            user.password_hash
        ):
            # Persist the upgraded cost profile together with the successful-login
            # session and audit transaction. An MFA denial never mutates the hash.
            user.password_hash = hash_password(raw_password)
        self._transactions.complete_successful_authentication(
            user,
            occurred_at=now,
            auth_method="password",
            device_label=device_label,
        )
        return user

    def authenticate_federated(
        self,
        *,
        identity_provider: str,
        federated_subject: str,
        mfa_code: str | None = None,
        device_label: str | None = None,
    ) -> UserAccount:
        normalized_provider = normalize_identity_provider(identity_provider)
        normalized_subject = normalize_federated_subject(federated_subject)
        validate_federated_identity(normalized_provider, normalized_subject)
        if not normalized_provider or not normalized_subject:
            # Both absent passes validation, but must never reach the lookup:
            # NULL == NULL in SQL would match every non-federated account.
            raise ValidationError("Invalid federated identity.", code="AUTH_FAILED")
        now = datetime.now(UTC)
        user = self._user_repo.get_by_federated_identity(
            normalized_provider,
            normalized_subject,
        )
        audit_username = (
            user.username if user is not None else f"federated:{normalized_provider}"
        )
        if (
            not user
            or not user.is_active
            or getattr(user, "account_type", ACCOUNT_TYPE_HUMAN) != ACCOUNT_TYPE_HUMAN
        ):
            self._transactions.persist_standalone_login_denial(
                username=audit_username,
                user=user,
                reason="invalid_federated_identity",
                details={"identity_provider": normalized_provider},
            )
            raise ValidationError("Invalid federated identity.", code="AUTH_FAILED")
        if user.locked_until is not None and user.locked_until <= now:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.updated_at = now
        if user.locked_until is not None and user.locked_until > now:
            self._transactions.persist_standalone_login_denial(
                username=audit_username,
                user=user,
                reason="locked_out",
                details={
                    "locked_until": user.locked_until.isoformat(),
                    "identity_provider": normalized_provider,
                },
            )
            raise ValidationError(
                f"Account is locked until {user.locked_until.isoformat()}.",
                code="AUTH_LOCKED",
            )
        if bool(getattr(user, "mfa_enabled", False)) and not verify_totp_code(
            getattr(user, "mfa_secret", None),
            mfa_code,
            at_time=now,
        ):
            reason = "mfa_required" if not str(mfa_code or "").strip() else "mfa_invalid"
            self._transactions.register_failed_login(
                user,
                username=audit_username,
                occurred_at=now,
                reason=reason,
                auth_method=f"federated:{normalized_provider}",
            )
            message = (
                "Multi-factor authentication code is required."
                if reason == "mfa_required"
                else "Invalid multi-factor authentication code."
            )
            code = (
                "AUTH_MFA_REQUIRED"
                if reason == "mfa_required"
                else "AUTH_MFA_FAILED"
            )
            raise ValidationError(message, code=code)
        self._transactions.complete_successful_authentication(
            user,
            occurred_at=now,
            auth_method=f"federated:{normalized_provider}",
            device_label=device_label,
        )
        return user


__all__ = ["AuthenticationHandler"]
