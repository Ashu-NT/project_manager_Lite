from __future__ import annotations

from src.core.platform.domain.security.auth import normalize_auth_email
from src.core.platform.common.exceptions import ValidationError

class AuthValidationMixin:
    @staticmethod
    def _validate_password(password: str) -> None:
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

    @staticmethod
    def _normalize_email(email: str | None) -> str | None:
        return normalize_auth_email(email)

    @staticmethod
    def _validate_email(email: str | None) -> None:
        normalize_auth_email(email)
