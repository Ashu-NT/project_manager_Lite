from __future__ import annotations

from typing import Callable, TypeVar

from src.api.desktop.platform.models import DesktopApiError, DesktopApiResult, OrganizationDto
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.org.domain import Organization

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


def serialize_organization(organization: Organization) -> OrganizationDto:
    return OrganizationDto(
        id=organization.id,
        organization_code=organization.organization_code,
        display_name=organization.display_name,
        timezone_name=organization.timezone_name,
        base_currency=organization.base_currency,
        is_active=organization.is_active,
        version=organization.version,
    )
