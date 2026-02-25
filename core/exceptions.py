# core/exceptions.py

class DomainError(Exception):
    """Base class for domain-level errors."""
    def __init__(self, message: str,*, code: str | None = None):
        super().__init__(message)
        self.code = code or self.__class__.__name__


class ValidationError(DomainError):
    """Raised when data is invalid or violates constraints."""


class NotFoundError(DomainError):
    """Raised when an entity is not found."""


class BusinessRuleError(DomainError):
    """Raised when business rules are violated (e.g., circular dependencies)."""


class ConcurrencyError(DomainError):
    """Raised when optimistic locking detects a stale update."""
