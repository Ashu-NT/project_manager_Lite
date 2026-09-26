from __future__ import annotations

from src.core.platform.common.exceptions import DomainError

DEFAULT_SAFE_FAILURE_MESSAGE = "The action could not be completed. Please try again."


def safe_exception_message(exc: Exception, *, fallback: str = DEFAULT_SAFE_FAILURE_MESSAGE) -> str:
    """Return UI-safe text for an unexpected exception.

    DomainError (and subclasses such as ValidationError, NotFoundError,
    ConcurrencyError) already carry curated, user-facing messages and are
    shown as-is. Everything else -- SQLAlchemy errors, stdlib exceptions,
    third-party stack fragments -- may contain raw SQL, bound parameter
    values, or internal identifiers and must never reach the UI. Callers
    are expected to log the raw exception separately before calling this.
    """
    if isinstance(exc, DomainError):
        return str(exc)
    return fallback


__all__ = ["DEFAULT_SAFE_FAILURE_MESSAGE", "safe_exception_message"]
