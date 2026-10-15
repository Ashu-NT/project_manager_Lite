"""PlatformEmployeeDesktopApi's Employee Documents surface -- the thin
desktop-facing adapter over the Employee handlers' own explicit employee_id
boundary (see employee_documents.py)."""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.master_data.department.dto.commands.department import (
    DepartmentCreateCommand,
)
from src.core.platform.application.master_data.documents.dto.commands.documents import (
    DocumentCreateCommand,
)
from src.core.platform.application.master_data.employee.dto.commands.employee import (
    EmployeeCreateCommand,
)


def test_desktop_api_links_lists_and_unlinks_employee_documents(services) -> None:
    document_commands = services["document_commands"]

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="EDAPI-D1", name="API Docs Dept"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EDAPI-E1", full_name="API Doc Employee", department_id=department.id))
    document = document_commands.create_document(DocumentCreateCommand(document_code="EDAPI-DOC-1", title="API Contract", document_type="POLICY", storage_kind="FILE_PATH", storage_uri="C:/docs/api-contract.pdf"))

    registry = build_desktop_api_registry(services)
    link_result = registry.platform_employee.link_employee_document(employee.id, document.id)
    assert link_result.ok, link_result.error

    page_result = registry.platform_employee.list_employee_documents_page(employee.id)
    assert page_result.ok
    assert page_result.data.filtered_total == 1
    row = page_result.data.items[0]
    assert row.title == "API Contract"
    assert row.link_id == link_result.data.id

    unlink_result = registry.platform_employee.unlink_employee_document(employee.id, row.link_id)
    assert unlink_result.ok, unlink_result.error

    page_after = registry.platform_employee.list_employee_documents_page(employee.id)
    assert page_after.data.filtered_total == 0
