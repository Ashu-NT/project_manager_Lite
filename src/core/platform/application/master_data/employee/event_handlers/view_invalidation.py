from __future__ import annotations

from src.core.platform.domain.master_data.employee.events import (
    EmployeeCreated,
    EmployeeProfileUpdated,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

EMPLOYEE_CATEGORY = "employee"
EMPLOYEE_LIST_SCOPE_CODE = "employee_list"


def build_employee_list_view_invalidation_handler(channel: ViewInvalidationChannel):
    def handle_employee_list_event(
        event: EmployeeCreated | EmployeeProfileUpdated,
        context: DomainEventContext,
    ) -> None:
        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(event.tenant_id, event.organization_id),
                category=EMPLOYEE_CATEGORY,
                scope_code=EMPLOYEE_LIST_SCOPE_CODE,
                entity_type="employee",
                entity_id=None,
            )
        )

    return handle_employee_list_event


__all__ = [
    "build_employee_list_view_invalidation_handler",
    "EMPLOYEE_CATEGORY",
    "EMPLOYEE_LIST_SCOPE_CODE",
]
