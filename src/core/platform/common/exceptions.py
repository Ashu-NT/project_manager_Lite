from __future__ import annotations


class DomainError(Exception):
    """Base class for domain-level errors."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code or self.__class__.__name__


class ValidationError(DomainError):
    """Raised when data is invalid or violates constraints."""


class NotFoundError(DomainError):
    """Raised when an entity is not found."""


class BusinessRuleError(DomainError):
    """Raised when business rules are violated."""


class AuthenticationError(BusinessRuleError):
    """Raised when an operation cannot authenticate its caller."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or "AUTHENTICATION_REQUIRED")


class AuthorizationError(BusinessRuleError):
    """Raised when a caller lacks permission for an operation."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or "PERMISSION_DENIED")


class ConfigurationError(DomainError):
    """Raised when a required runtime dependency is not configured."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or "CONFIGURATION_ERROR")


class ConcurrencyError(DomainError):
    """Raised when optimistic locking detects a stale update."""


class OperationNotPermittedError(DomainError):
    """Raised when an operation is structurally forbidden on an entity (e.g. update/delete on append-only logs)."""

class UnsupportedOperationError(DomainError):
    """Raised when a requested operation is not implemented or supported."""

__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "BusinessRuleError",
    "ConcurrencyError",
    "ConfigurationError",
    "DomainError",
    "NotFoundError",
    "OperationNotPermittedError",
    "UnsupportedOperationError",
    "ValidationError",
]
