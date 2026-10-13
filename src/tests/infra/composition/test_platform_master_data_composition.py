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


def test_platform_master_data_events_have_one_shared_handler_per_family(services):
    bus = services["project_service"]._uow_factory._post_commit_bus
    families = (
        (EmployeeCreated, EmployeeProfileUpdated),
        (DepartmentCreated, DepartmentProfileUpdated, DepartmentActivated, DepartmentDeactivated),
        (SiteCreated, SiteProfileUpdated, SiteActivated, SiteDeactivated, SiteArchived),
        (PartyCreated, PartyProfileUpdated),
        (DocumentCreated, DocumentProfileUpdated),
        (DocumentStructureCreated, DocumentStructureProfileUpdated),
        (DocumentReferenceLinked, DocumentReferenceUnlinked),
    )
    for family in families:
        handlers = [
            [
                handler for handler in bus._handlers[event_type]
                if handler.__module__.startswith("src.core.platform.application.master_data")
            ]
            for event_type in family
        ]
        assert all(len(entries) == 1 for entries in handlers)
        assert all(entries[0] is handlers[0][0] for entries in handlers)
