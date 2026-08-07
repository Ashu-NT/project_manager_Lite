from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.platform.domain.master_data.employee import EmploymentType
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.orm.master_data.documents.documents import (
    DocumentLinkORM,
    DocumentORM,
    DocumentStructureORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.master_data.party.party import PartyORM
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM


def _seed_core_scope_rows(services) -> dict[str, str]:
    session = services["session"]
    organization_service = services["organization_service"]
    default_org = organization_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="OPS",
        display_name="Operations Hub",
        timezone_name="UTC",
        base_currency="USD",
        is_active=False,
    )
    assert default_org is not None
    assert other_org is not None

    current_tenant_id = getattr(default_org, "tenant_id", None)
    other_tenant_id = getattr(other_org, "tenant_id", None) or current_tenant_id
    now = datetime.now(timezone.utc)

    current_site = SiteORM(
        id="site-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        site_code="SITE-CUR",
        name="Current Site",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    other_site = SiteORM(
        id="site-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        site_code="SITE-OTH",
        name="Other Site",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    current_department = DepartmentORM(
        id="department-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        department_code="DEPT-CUR",
        name="Current Department",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    other_department = DepartmentORM(
        id="department-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        department_code="DEPT-OTH",
        name="Other Department",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    current_employee = EmployeeORM(
        id="employee-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        employee_code="EMP-CUR",
        full_name="Current Employee",
        employment_type=EmploymentType.FULL_TIME,
        is_active=True,
        version=1,
    )
    other_employee = EmployeeORM(
        id="employee-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        employee_code="EMP-OTH",
        full_name="Other Employee",
        employment_type=EmploymentType.FULL_TIME,
        is_active=True,
        version=1,
    )
    current_party = PartyORM(
        id="party-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        party_code="PARTY-CUR",
        party_name="Current Party",
        party_type="SUPPLIER",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    other_party = PartyORM(
        id="party-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        party_code="PARTY-OTH",
        party_name="Other Party",
        party_type="SUPPLIER",
        is_active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    current_structure = DocumentStructureORM(
        id="structure-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        structure_code="STR-CUR",
        name="Current Structure",
        object_scope="GENERAL",
        default_document_type="GENERAL",
        sort_order=0,
        is_active=True,
        version=1,
    )
    other_structure = DocumentStructureORM(
        id="structure-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        structure_code="STR-OTH",
        name="Other Structure",
        object_scope="GENERAL",
        default_document_type="GENERAL",
        sort_order=0,
        is_active=True,
        version=1,
    )
    current_document = DocumentORM(
        id="document-current",
        tenant_id=current_tenant_id,
        organization_id=default_org.id,
        document_code="DOC-CUR",
        title="Current Document",
        document_type="GENERAL",
        document_structure_id=None,
        storage_kind="FILE_PATH",
        storage_uri="/tmp/current.pdf",
        uploaded_at=now,
        is_current=True,
        is_active=True,
        version=1,
    )
    other_document = DocumentORM(
        id="document-other",
        tenant_id=other_tenant_id,
        organization_id=other_org.id,
        document_code="DOC-OTH",
        title="Other Document",
        document_type="GENERAL",
        document_structure_id=None,
        storage_kind="FILE_PATH",
        storage_uri="/tmp/other.pdf",
        uploaded_at=now,
        is_current=True,
        is_active=True,
        version=1,
    )
    current_link = DocumentLinkORM(
        id="link-current",
        organization_id=default_org.id,
        document_id=current_document.id,
        module_code="maintenance",
        entity_type="asset",
        entity_id="asset-current",
        link_role="attachment",
    )
    other_link = DocumentLinkORM(
        id="link-other",
        organization_id=other_org.id,
        document_id=other_document.id,
        module_code="maintenance",
        entity_type="asset",
        entity_id="asset-other",
        link_role="attachment",
    )

    session.add_all([
        current_site, other_site,
        current_department, other_department,
        current_employee, other_employee,
        current_party, other_party,
        current_structure, other_structure,
        current_document, other_document,
    ])
    session.flush()
    session.add_all([current_link, other_link])
    session.flush()

    return {
        "current_org_id": default_org.id,
        "other_org_id": other_org.id,
        "site_current": current_site.id,
        "site_other": other_site.id,
        "department_current": current_department.id,
        "department_other": other_department.id,
        "employee_current": current_employee.id,
        "employee_other": other_employee.id,
        "party_current": current_party.id,
        "party_other": other_party.id,
        "structure_current": current_structure.id,
        "structure_other": other_structure.id,
        "document_current": current_document.id,
        "document_other": other_document.id,
        "link_current": current_link.id,
        "link_other": other_link.id,
    }


def test_platform_root_repositories_hide_cross_organization_rows(services) -> None:
    seeded = _seed_core_scope_rows(services)

    site_repo = services["site_service"]._site_repo
    department_repo = services["department_service"]._department_repo
    employee_repo = services["employee_service"]._employee_repo
    party_repo = services["party_service"]._party_repo
    structure_repo = services["document_service"]._structure_repo
    document_repo = services["document_service"]._document_repo
    link_repo = services["document_service"]._link_repo

    assert site_repo.get(seeded["site_other"]) is None
    assert department_repo.get(seeded["department_other"]) is None
    assert employee_repo.get(seeded["employee_other"]) is None
    assert party_repo.get(seeded["party_other"]) is None
    assert structure_repo.get(seeded["structure_other"]) is None
    assert document_repo.get(seeded["document_other"]) is None
    assert link_repo.get(seeded["link_other"]) is None
    assert site_repo.get_by_code(seeded["other_org_id"], "SITE-CUR") is None
    assert department_repo.get_by_code(seeded["other_org_id"], "DEPT-CUR") is None
    assert employee_repo.get_for_organization(
        seeded["employee_current"],
        seeded["other_org_id"],
    ) is None
    assert employee_repo.get_by_code_for_organization(
        "EMP-CUR",
        seeded["other_org_id"],
    ) is None
    assert party_repo.get_by_code(seeded["other_org_id"], "PARTY-CUR") is None
    assert structure_repo.get_by_code(seeded["other_org_id"], "STR-CUR") is None
    assert document_repo.get_by_code(seeded["other_org_id"], "DOC-CUR") is None

    site_ids = {
        row.id
        for row in site_repo.list_for_organization(
            seeded["current_org_id"], active_only=None
        )
    }
    document_ids = {
        row.id
        for row in document_repo.list_for_organization(
            seeded["current_org_id"], active_only=None
        )
    }
    link_ids = {
        row.id
        for row in link_repo.list_for_entity(
            seeded["current_org_id"],
            "maintenance",
            "asset",
            "asset-current",
        )
    }

    assert site_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert (
        department_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    )
    assert (
        employee_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    )
    assert party_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    assert (
        structure_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    )
    assert (
        document_repo.list_for_organization(seeded["other_org_id"], active_only=None) == []
    )
    assert (
        link_repo.list_for_entity(
            seeded["other_org_id"],
            "maintenance",
            "asset",
            "asset-current",
        )
        == []
    )
    assert link_repo.list_for_module(seeded["other_org_id"], "maintenance") == []

    assert seeded["site_current"] in site_ids
    assert seeded["site_other"] not in site_ids
    assert seeded["document_current"] in document_ids
    assert seeded["document_other"] not in document_ids
    assert seeded["link_current"] in link_ids
    assert seeded["link_other"] not in link_ids

    link_repo.delete(seeded["link_other"])
    services["session"].flush()
    assert services["session"].get(DocumentLinkORM, seeded["link_other"]) is not None
