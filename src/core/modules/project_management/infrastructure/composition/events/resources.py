from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.resources.catalog.resource_capability_events import (
    ResourceCapabilityChanged,
)
from src.core.modules.project_management.application.resources.catalog.resource_master_events import (
    ResourceMasterChanged,
)
from src.core.modules.project_management.application.resources.event_handlers.view_invalidation import (
    build_linked_employee_resource_view_invalidation_handler,
    build_resource_capabilities_view_invalidation_handler,
    build_resource_list_view_invalidation_handler,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceIdentityReader,
)
from src.core.platform.domain.master_data.employee.events import EmployeeProfileUpdated
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_resource_view_invalidation(
    session: Session,
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    post_commit_bus.subscribe(
        ResourceMasterChanged,
        build_resource_list_view_invalidation_handler(view_channel),
    )
    post_commit_bus.subscribe(
        EmployeeProfileUpdated,
        build_linked_employee_resource_view_invalidation_handler(
            view_channel,
            SqlAlchemyResourceIdentityReader(session=session).find_linked_resource_id,
        ),
    )
    post_commit_bus.subscribe(
        ResourceCapabilityChanged,
        build_resource_capabilities_view_invalidation_handler(view_channel),
    )
