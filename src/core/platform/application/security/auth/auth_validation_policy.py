"""Stateless credential/identity input validation rules for Platform auth."""

from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.security.auth import normalize_auth_email


class AuthValidationPolicy:
    def validate_password(self, password: str) -> None:
        pwd = password or ""
        if len(pwd) < 8:
            raise ValidationError(
                "Password must be at least 8 characters.",
                code="WEAK_PASSWORD",
            )
        if not any(ch.islower() for ch in pwd):
            raise ValidationError(
                "Password must include a lowercase letter.",
                code="WEAK_PASSWORD",
            )
        if not any(ch.isupper() for ch in pwd):
            raise ValidationError(
                "Password must include an uppercase letter.",
                code="WEAK_PASSWORD",
            )
        if not any(ch.isdigit() for ch in pwd):
            raise ValidationError(
                "Password must include a digit.",
                code="WEAK_PASSWORD",
            )

    def normalize_email(self, email: str | None) -> str | None:
        return normalize_auth_email(email)

    def validate_email(self, email: str | None) -> None:
        normalize_auth_email(email)


__all__ = ["AuthValidationPolicy"]
