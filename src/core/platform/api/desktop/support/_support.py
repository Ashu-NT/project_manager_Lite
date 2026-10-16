from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.core.platform.api.desktop.models.common import (
    DesktopApiError,
    DesktopApiResult,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    DomainError,
    NotFoundError,
    ValidationError,
)

_ResultT = TypeVar("_ResultT")


def execute_desktop_operation(operation: Callable[[], _ResultT]) -> DesktopApiResult[_ResultT]:
    try:
        return DesktopApiResult(ok=True, data=operation())
    except DomainError as exc:
        return DesktopApiResult(ok=False, error=serialize_domain_error(exc))


def serialize_domain_error(exc: DomainError) -> DesktopApiError:
    if isinstance(exc, NotFoundError):
        category = "not_found"
    elif isinstance(exc, ValidationError):
        category = "validation"
    elif isinstance(exc, (BusinessRuleError, ConcurrencyError)):
        category = "conflict"
    else:
        category = "domain"
    return DesktopApiError(
        code=getattr(exc, "code", exc.__class__.__name__),
        message=str(exc),
        category=category,
    )
