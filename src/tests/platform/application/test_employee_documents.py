"""Employee Documents -- the first real production consumer of the generic
Platform DocumentLink capability. Employee's own service boundary takes an
explicit employee_id and translates internally to the generic
entity_type="employee" contract; QML/application code never constructs
that pair itself. Mirrors the Calendar/Activity vertical-slice pattern
already proven for Employee, applied to Documents."""

from __future__ import annotations

import pytest

from src.core.platform.application.master_data.department.dto.commands.department import (
    DepartmentCreateCommand,
)
from src.core.platform.application.master_data.documents.dto.commands.documents import (
    DocumentCreateCommand,
)
from src.core.platform.application.master_data.employee.dto.commands.employee import (
    EmployeeCreateCommand,
)
from src.core.platform.common.exceptions import NotFoundError


def test_list_employee_documents_page_returns_only_linked_documents(services) -> None:
    document_commands = services["document_commands"]

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EDOC-D1", name="Docs Dept"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EDOC-E1", full_name="Doc Employee One", department_id=department.id))
    other_employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EDOC-E2", full_name="Doc Employee Two", department_id=department.id))
    document = document_commands.create_document(DocumentCreateCommand(document_code="EDOC-DOC-1", title="Employment Contract", document_type="POLICY", storage_kind="FILE_PATH", storage_uri="C:/docs/contract.pdf"))
    other_document = document_commands.create_document(DocumentCreateCommand(document_code="EDOC-DOC-2", title="Other Contract", document_type="POLICY", storage_kind="FILE_PATH", storage_uri="C:/docs/other.pdf"))
    services["employee_document_commands"].link_employee_document(employee.id, document.id)
    services["employee_document_commands"].link_employee_document(other_employee.id, other_document.id)

    page = services["employee_query"].list_employee_documents_page(employee.id)
    assert page.filtered_total == 1
    assert [row.document.id for row in page.items] == [document.id]


def test_link_employee_document_appears_on_employee_activity_feed(services) -> None:
    document_commands = services["document_commands"]

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EDOC-D2", name="Docs Dept Two"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EDOC-E3", full_name="Doc Employee Three", department_id=department.id))
    document = document_commands.create_document(DocumentCreateCommand(document_code="EDOC-DOC-3", title="Insurance Certificate", document_type="CERTIFICATE", storage_kind="FILE_PATH", storage_uri="C:/docs/insurance.pdf"))

    services["employee_document_commands"].link_employee_document(employee.id, document.id)

    activity_service = services["activity_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id
    entries = activity_service.list_recent_for_entity("employee", employee.id, organization_id, limit=10)
    messages = [entry.human_message for entry in entries]
    assert any("Insurance Certificate" in message for message in messages)


def test_unlink_employee_document_removes_link_not_document(services) -> None:
    document_commands = services["document_commands"]
    document_query = services["document_query"]

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EDOC-D3", name="Docs Dept Three"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EDOC-E4", full_name="Doc Employee Four", department_id=department.id))
    document = document_commands.create_document(DocumentCreateCommand(document_code="EDOC-DOC-4", title="NDA", document_type="POLICY", storage_kind="FILE_PATH", storage_uri="C:/docs/nda.pdf"))
    link = services["employee_document_commands"].link_employee_document(employee.id, document.id)

    services["employee_document_commands"].unlink_employee_document(employee.id, link.id)

    page = services["employee_query"].list_employee_documents_page(employee.id)
    assert page.filtered_total == 0
    # The Document itself must still exist -- unlink is relationship-only.
    still_exists = document_query.get_document(document.id)
    assert still_exists.id == document.id


def test_unlink_employee_document_rejects_link_belonging_to_another_employee(services) -> None:
    document_commands = services["document_commands"]

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EDOC-D4", name="Docs Dept Four"))
    employee_one = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EDOC-E5", full_name="Doc Employee Five", department_id=department.id))
    employee_two = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EDOC-E6", full_name="Doc Employee Six", department_id=department.id))
    document = document_commands.create_document(DocumentCreateCommand(document_code="EDOC-DOC-5", title="Contract Five", document_type="POLICY", storage_kind="FILE_PATH", storage_uri="C:/docs/five.pdf"))
    link = services["employee_document_commands"].link_employee_document(employee_one.id, document.id)

    with pytest.raises(NotFoundError) as exc_info:
        services["employee_document_commands"].unlink_employee_document(employee_two.id, link.id)
    assert exc_info.value.code == "EMPLOYEE_DOCUMENT_LINK_NOT_FOUND"


def test_employee_deactivation_does_not_affect_linked_documents(services) -> None:
    document_commands = services["document_commands"]

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EDOC-D5", name="Docs Dept Five"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EDOC-E7", full_name="Doc Employee Seven", department_id=department.id))
    document = document_commands.create_document(DocumentCreateCommand(document_code="EDOC-DOC-6", title="Historical Contract", document_type="POLICY", storage_kind="FILE_PATH", storage_uri="C:/docs/historical.pdf"))
    services["employee_document_commands"].link_employee_document(employee.id, document.id)

    services["employee_commands"].deactivate_employee(employee.id)

    page = services["employee_query"].list_employee_documents_page(employee.id)
    assert page.filtered_total == 1
    assert page.items[0].document.id == document.id
