from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.application.master_data.documents.document_access import (
    DOCUMENT_MANAGE_PERMISSION as DOCUMENT_MANAGE,
)
from src.core.platform.application.master_data.documents.document_access import (
    DOCUMENT_READ_PERMISSION,
)
from src.core.platform.application.master_data.employee.employee_context import (
    active_organization_id,
)
from src.core.platform.common.exceptions import NotFoundError

if TYPE_CHECKING:
    from src.core.platform.application.tenant.tenancy.tenant_context import (
        TenantContextService,
    )
    from src.core.platform.contract.repositories.master_data.employee.contracts import (
        EmployeeRepository,
    )

MODULE_CODE = "platform"
ENTITY_TYPE = "employee"


# Employee access alone never implies Document access: both permissions are required.
DOCUMENT_VIEW_PERMISSION = DOCUMENT_READ_PERMISSION
DOCUMENT_MANAGE_PERMISSION = DOCUMENT_MANAGE


def require_employee_in_context(
    employee_repo: EmployeeRepository,
    tenant_context_service: TenantContextService | None,
    employee_id: str,
):
    organization_id = active_organization_id(
        tenant_context_service, operation_label="access employee documents"
    )
    employee = employee_repo.get_for_organization(employee_id, organization_id)
    if employee is None:
        raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
    return employee, organization_id



__all__ = [
    "DOCUMENT_MANAGE_PERMISSION",
    "DOCUMENT_VIEW_PERMISSION",
    "ENTITY_TYPE",
    "MODULE_CODE",
    "require_employee_in_context",
]
