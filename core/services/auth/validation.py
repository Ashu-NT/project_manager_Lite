from __future__ import annotations

import re

from core.exceptions import ValidationError


_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


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
        value = (email or "").strip().lower()
        return value or None

    @staticmethod
    def _validate_email(email: str | None) -> None:
        if email is None:
            return
        if not _EMAIL_RE.match(email):
            raise ValidationError(
                "Invalid email format.",
                code="INVALID_EMAIL",
            )

