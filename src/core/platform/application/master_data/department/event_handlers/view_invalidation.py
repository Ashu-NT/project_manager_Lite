from __future__ import annotations

from src.core.platform.domain.master_data.department.events import (
    DepartmentCreated,
    DepartmentProfileUpdated,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

DEPARTMENT_CATEGORY = "department"
DEPARTMENT_LIST_SCOPE_CODE = "department_list"


def build_department_list_view_invalidation_handler(channel: ViewInvalidationChannel):
    def handle_department_list_event(
        event: DepartmentCreated | DepartmentProfileUpdated,
        context: DomainEventContext,
    ) -> None:
        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(event.tenant_id, event.organization_id),
                category=DEPARTMENT_CATEGORY,
                scope_code=DEPARTMENT_LIST_SCOPE_CODE,
                entity_type="department",
                entity_id=None,
            )
        )

    return handle_department_list_event


__all__ = [
    "build_department_list_view_invalidation_handler",
    "DEPARTMENT_CATEGORY",
    "DEPARTMENT_LIST_SCOPE_CODE",
]
