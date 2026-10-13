"""Post-commit invalidation registrations for Platform master data."""

from src.core.platform.application.master_data.department.event_handlers.view_invalidation import (
    build_department_list_view_invalidation_handler,
)
from src.core.platform.application.master_data.documents.event_handlers.view_invalidation import (
    build_document_links_view_invalidation_handler,
    build_document_list_view_invalidation_handler,
    build_document_structure_list_view_invalidation_handler,
)
from src.core.platform.application.master_data.employee.event_handlers.view_invalidation import (
    build_employee_list_view_invalidation_handler,
)
from src.core.platform.application.master_data.party.event_handlers.view_invalidation import (
    build_party_list_view_invalidation_handler,
)
from src.core.platform.application.master_data.site.event_handlers.view_invalidation import (
    build_site_list_view_invalidation_handler,
)
from src.core.platform.domain.master_data.department.events import (
    DepartmentActivated,
    DepartmentCreated,
    DepartmentDeactivated,
    DepartmentProfileUpdated,
)
from src.core.platform.domain.master_data.documents.events import (
    DocumentCreated,
    DocumentProfileUpdated,
    DocumentReferenceLinked,
    DocumentReferenceUnlinked,
    DocumentStructureCreated,
    DocumentStructureProfileUpdated,
)
from src.core.platform.domain.master_data.employee.events import (
    EmployeeCreated,
    EmployeeProfileUpdated,
)
from src.core.platform.domain.master_data.party.events import (
    PartyCreated,
    PartyProfileUpdated,
)
from src.core.platform.domain.master_data.site.events import (
    SiteActivated,
    SiteArchived,
    SiteCreated,
    SiteDeactivated,
    SiteProfileUpdated,
)
from src.core.shared.events.domain_event_subscriber import PostCommitEventSubscriber
from src.core.shared.events.view_invalidation import ViewInvalidationChannel


def register_master_data_view_invalidation(
    bus: PostCommitEventSubscriber,
    channel: ViewInvalidationChannel,
) -> None:
    employee_handler = build_employee_list_view_invalidation_handler(channel)
    for employee_event_type in (EmployeeCreated, EmployeeProfileUpdated):
        bus.subscribe(employee_event_type, employee_handler)

    department_handler = build_department_list_view_invalidation_handler(channel)
    for department_event_type in (
        DepartmentCreated, DepartmentProfileUpdated, DepartmentActivated, DepartmentDeactivated,
    ):
        bus.subscribe(department_event_type, department_handler)

    site_handler = build_site_list_view_invalidation_handler(channel)
    for site_event_type in (
        SiteCreated, SiteProfileUpdated, SiteActivated, SiteDeactivated, SiteArchived,
    ):
        bus.subscribe(site_event_type, site_handler)

    party_handler = build_party_list_view_invalidation_handler(channel)
    for party_event_type in (PartyCreated, PartyProfileUpdated):
        bus.subscribe(party_event_type, party_handler)

    document_handler = build_document_list_view_invalidation_handler(channel)
    for document_event_type in (DocumentCreated, DocumentProfileUpdated):
        bus.subscribe(document_event_type, document_handler)

    structure_handler = build_document_structure_list_view_invalidation_handler(channel)
    for structure_event_type in (DocumentStructureCreated, DocumentStructureProfileUpdated):
        bus.subscribe(structure_event_type, structure_handler)

    links_handler = build_document_links_view_invalidation_handler(channel)
    for link_event_type in (DocumentReferenceLinked, DocumentReferenceUnlinked):
        bus.subscribe(link_event_type, links_handler)


__all__ = ["register_master_data_view_invalidation"]
