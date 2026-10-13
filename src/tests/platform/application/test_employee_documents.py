"""Employee Documents -- the first real production consumer of the generic
Platform DocumentLink capability. Employee's own service boundary takes an
explicit employee_id and translates internally to the generic
entity_type="employee" contract; QML/application code never constructs
that pair itself. Mirrors the Calendar/Activity vertical-slice pattern
already proven for Employee, applied to Documents."""

from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import NotFoundError


def test_list_employee_documents_page_returns_only_linked_documents(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    document_service = services["document_service"]

    department = department_service.create_department(department_code="EDOC-D1", name="Docs Dept")
    employee = employee_service.create_employee(
        employee_code="EDOC-E1", full_name="Doc Employee One", department_id=department.id
    )
    other_employee = employee_service.create_employee(
        employee_code="EDOC-E2", full_name="Doc Employee Two", department_id=department.id
    )
    document = document_service.create_document(
        document_code="EDOC-DOC-1", title="Employment Contract", document_type="POLICY",
        storage_kind="FILE_PATH", storage_uri="C:/docs/contract.pdf",
    )
    other_document = document_service.create_document(
        document_code="EDOC-DOC-2", title="Other Contract", document_type="POLICY",
        storage_kind="FILE_PATH", storage_uri="C:/docs/other.pdf",
    )
    employee_service.link_employee_document(employee.id, document.id)
    employee_service.link_employee_document(other_employee.id, other_document.id)

    page = employee_service.list_employee_documents_page(employee.id)
    assert page.filtered_total == 1
    assert [row.document.id for row in page.items] == [document.id]


def test_link_employee_document_appears_on_employee_activity_feed(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    document_service = services["document_service"]

    department = department_service.create_department(department_code="EDOC-D2", name="Docs Dept Two")
    employee = employee_service.create_employee(
        employee_code="EDOC-E3", full_name="Doc Employee Three", department_id=department.id
    )
    document = document_service.create_document(
        document_code="EDOC-DOC-3", title="Insurance Certificate", document_type="CERTIFICATE",
        storage_kind="FILE_PATH", storage_uri="C:/docs/insurance.pdf",
    )

    employee_service.link_employee_document(employee.id, document.id)

    activity_service = services["activity_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id
    entries = activity_service.list_recent_for_entity("employee", employee.id, organization_id, limit=10)
    messages = [entry.human_message for entry in entries]
    assert any("Insurance Certificate" in message for message in messages)


def test_unlink_employee_document_removes_link_not_document(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    document_service = services["document_service"]

    department = department_service.create_department(department_code="EDOC-D3", name="Docs Dept Three")
    employee = employee_service.create_employee(
        employee_code="EDOC-E4", full_name="Doc Employee Four", department_id=department.id
    )
    document = document_service.create_document(
        document_code="EDOC-DOC-4", title="NDA", document_type="POLICY",
        storage_kind="FILE_PATH", storage_uri="C:/docs/nda.pdf",
    )
    link = employee_service.link_employee_document(employee.id, document.id)

    employee_service.unlink_employee_document(employee.id, link.id)

    page = employee_service.list_employee_documents_page(employee.id)
    assert page.filtered_total == 0
    # The Document itself must still exist -- unlink is relationship-only.
    still_exists = document_service.get_document(document.id)
    assert still_exists.id == document.id


def test_unlink_employee_document_rejects_link_belonging_to_another_employee(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    document_service = services["document_service"]

    department = department_service.create_department(department_code="EDOC-D4", name="Docs Dept Four")
    employee_one = employee_service.create_employee(
        employee_code="EDOC-E5", full_name="Doc Employee Five", department_id=department.id
    )
    employee_two = employee_service.create_employee(
        employee_code="EDOC-E6", full_name="Doc Employee Six", department_id=department.id
    )
    document = document_service.create_document(
        document_code="EDOC-DOC-5", title="Contract Five", document_type="POLICY",
        storage_kind="FILE_PATH", storage_uri="C:/docs/five.pdf",
    )
    link = employee_service.link_employee_document(employee_one.id, document.id)

    with pytest.raises(NotFoundError) as exc_info:
        employee_service.unlink_employee_document(employee_two.id, link.id)
    assert exc_info.value.code == "EMPLOYEE_DOCUMENT_LINK_NOT_FOUND"


def test_employee_deactivation_does_not_affect_linked_documents(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    document_service = services["document_service"]

    department = department_service.create_department(department_code="EDOC-D5", name="Docs Dept Five")
    employee = employee_service.create_employee(
        employee_code="EDOC-E7", full_name="Doc Employee Seven", department_id=department.id
    )
    document = document_service.create_document(
        document_code="EDOC-DOC-6", title="Historical Contract", document_type="POLICY",
        storage_kind="FILE_PATH", storage_uri="C:/docs/historical.pdf",
    )
    employee_service.link_employee_document(employee.id, document.id)

    employee_service.deactivate_employee(employee.id)

    page = employee_service.list_employee_documents_page(employee.id)
    assert page.filtered_total == 1
    assert page.items[0].document.id == document.id
