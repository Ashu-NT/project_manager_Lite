"""Organization Detail's Activity feed (Overview "Recent Activity" preview
and the full Activity section) is sourced from ActivityService -- real,
curated CRUD/lifecycle events for Organization/Site/Department/Employee/
Document, each with a genuine human-readable message set at write time.
This is distinct from the tenant-wide Platform audit trail (which stays
sourced from EnterpriseAuditService and shows everything, uncurated)."""

from __future__ import annotations

from src.core.platform.api.desktop.history.activity.activity import PlatformActivityDesktopApi

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}{_COUNTER['n']}"


def test_curated_feed_covers_organization_site_department_employee_document_events(services):
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    department_service = services["department_service"]
    employee_service = services["employee_service"]
    document_service = services["document_service"]
    activity_api = PlatformActivityDesktopApi(activity_service=services["activity_service"])

    org = organization_service.list_organizations()[0]

    # Organization: create + update + deactivate + enable, all on a SECOND
    # org (not the session's active one) -- Organization Detail must be
    # able to show activity for an organization it hasn't switched into.
    other_org = organization_service.create_organization(
        organization_code=_unique("ORG-"), display_name="Secondary Org"
    )
    organization_service.update_organization(
        other_org.id, display_name="Secondary Org Renamed", expected_version=other_org.version
    )
    organization_service.disable_organization(other_org.id)
    organization_service.enable_organization(other_org.id)

    # Site: create + update.
    site = site_service.create_site(site_code=_unique("SITE-"), name="Main Warehouse")
    site_service.update_site(site.id, name="Main Warehouse Renamed", expected_version=site.version)

    # Department: create + update.
    department = department_service.create_department(department_code=_unique("DEPT-"), name="Operations")
    department_service.update_department(
        department.id, name="Operations Renamed", expected_version=department.version
    )

    # Employee: create (assigned) + a NOISE profile update (must be excluded)
    # + deactivate (removed).
    employee = employee_service.create_employee(employee_code=_unique("EMP-"), full_name="Jane Doe")
    employee = employee_service.update_employee(
        employee.id, title="Senior Engineer", expected_version=employee.version
    )
    employee_service.update_employee(employee.id, is_active=False, expected_version=employee.version)

    # Document: create (added) + a NOISE profile update (must be excluded)
    # + deactivate (removed).
    document = document_service.create_document(
        document_code=_unique("DOC-"), title="Policy Manual", storage_uri="C:/docs/policy.pdf"
    )
    document = document_service.update_document(
        document.id, notes="Reviewed annually", expected_version=document.version
    )
    document_service.update_document(document.id, is_active=False, expected_version=document.version)

    org_items = activity_api.list_for_organization_overview(other_org.id, limit=25)
    org_titles = [item.human_message for item in org_items]
    items = activity_api.list_for_organization_overview(org.id, limit=25)
    titles = [item.human_message for item in items]

    def _has(label_prefix: str, pool=titles) -> bool:
        return any(t.startswith(label_prefix) for t in pool)

    assert _has("Organization created", org_titles)
    assert _has("Organization updated", org_titles)
    assert _has("Organization deactivated", org_titles)
    assert _has("Organization enabled", org_titles)
    assert _has("Site created")
    assert _has("Site updated")
    assert _has("Department created")
    assert _has("Department updated")
    assert _has("Employee assigned")
    assert _has("Employee removed")
    assert _has("Document added")
    assert _has("Document removed")

    # Employee/Document profile-only updates record their own field values
    # (title/notes) into the change diff, not the curated message text.
    assert not any("Senior Engineer" in t for t in titles)
    assert not any("Reviewed annually" in t for t in titles)
    assert _has("Employee updated")
    assert _has("Document updated")


def test_curated_feed_respects_limit_even_with_noise_ahead_of_it(services):
    """A wide raw fetch window (or, here, the fact that noise entries are
    never even written to Activity) must never starve the curated result
    below the requested limit."""
    organization_service = services["organization_service"]
    employee_service = services["employee_service"]
    activity_api = PlatformActivityDesktopApi(activity_service=services["activity_service"])
    org = organization_service.list_organizations()[0]

    employee = employee_service.create_employee(employee_code=_unique("EMP-"), full_name="Noise Test")
    for i in range(10):
        employee = employee_service.update_employee(
            employee.id, title=f"Title {i}", expected_version=employee.version
        )
    employee_service.update_employee(employee.id, is_active=False, expected_version=employee.version)

    items = activity_api.list_for_organization_overview(org.id, limit=5)
    titles = [item.human_message for item in items]
    assert any(t.startswith("Employee removed") for t in titles), titles


def test_curated_feed_shows_document_structure_creation_as_its_own_event(services):
    document_service = services["document_service"]
    organization_service = services["organization_service"]
    activity_api = PlatformActivityDesktopApi(activity_service=services["activity_service"])
    org = organization_service.list_organizations()[0]

    structure_code = _unique("STRUCT-")
    structure = document_service.create_document_structure(structure_code=structure_code, name="General Filing")
    document = document_service.create_document(
        document_code=_unique("DOC-"),
        title="Linked Doc",
        document_structure_id=structure.id,
        storage_uri="C:/docs/linked.pdf",
    )

    items = activity_api.list_for_organization_overview(org.id, limit=25)
    titles = [item.human_message for item in items]
    assert any(t == f"Document structure created — {structure.structure_code}" for t in titles)
    assert any(t == f"Document added — {document.title}" for t in titles)
