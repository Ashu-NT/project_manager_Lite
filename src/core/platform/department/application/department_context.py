from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.org.domain import Organization

if TYPE_CHECKING:
    from .department_service import DepartmentService


def active_organization(service: DepartmentService) -> Organization:
    if service._tenant_context_service is None:
        raise BusinessRuleError(
            "Active organization context is required.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    organization = service._tenant_context_service.get_active_organization()
    if organization is None:
        raise BusinessRuleError(
            "Active organization context is required.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    return organization


__all__ = ["active_organization"]
