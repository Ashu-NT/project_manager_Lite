from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.shared.activity import record_activity

if TYPE_CHECKING:
    from src.core.platform.application.master_data.documents.document_service import (
        EntityDocumentPage,
    )
    from src.core.platform.application.master_data.employee.employee_service import (
        EmployeeService,
    )
    from src.core.platform.domain.master_data.documents import Document, DocumentLink

_MODULE_CODE = "platform"
_ENTITY_TYPE = "employee"

# Today every Document-view/manage check below is the same broad
# "settings.manage" DocumentService itself enforces internally (see the
# Documents stack audit -- no narrower documents.read/documents.manage
# permission exists yet). Checking it explicitly here, in addition to
# DocumentService's own internal check, documents the dual-permission
# intent in code (Employee access does not by itself imply Document
# access) rather than relying on an implementation detail of what
# DocumentService happens to enforce downstream.
#
# Forward-looking seam (not implemented now -- no real requirement exists
# yet, per the anti-premature-complexity guidance this pass follows):
# Document already carries its own `confidentiality_level` field. A future
# per-document visibility rule (e.g. an HR-confidential work contract
# hidden from a non-HR viewer who otherwise has employee.read +
# settings.manage) would slot in as an additional filter inside
# DocumentLinkRepository.list_page_for_entity_in_tenant's own query and a
# matching check in DocumentService.get_document/add_link/remove_link --
# it does not require restructuring this entity-link boundary.
_DOCUMENT_VIEW_PERMISSION = "settings.manage"
_DOCUMENT_MANAGE_PERMISSION = "settings.manage"


def _require_employee_in_context(service: EmployeeService, employee_id: str):
    organization_id = service._active_organization_id(operation_label="access employee documents")
    employee = service._employee_repo.get_for_organization(employee_id, organization_id)
    if employee is None:
        raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
    return employee, organization_id


def _require_document_service(service: EmployeeService):
    if service._document_service is None:
        raise RuntimeError("Document service is not configured.")
    return service._document_service


def list_employee_documents_page(
    service: EmployeeService,
    employee_id: str,
    *,
    page: int = 1,
    page_size: int = 25,
    search: str = "",
    active_only: bool | None = None,
    document_type: str | None = None,
) -> EntityDocumentPage:
    require_permission(service._user_session, "employee.read", operation_label="list employee documents")
    require_permission(service._user_session, _DOCUMENT_VIEW_PERMISSION, operation_label="list employee documents")
    _require_employee_in_context(service, employee_id)
    document_service = _require_document_service(service)
    return document_service.list_documents_page_for_entity(
        module_code=_MODULE_CODE,
        entity_type=_ENTITY_TYPE,
        entity_id=employee_id,
        page=page,
        page_size=page_size,
        search=search,
        active_only=active_only,
        document_type=document_type,
    )


def link_employee_document(service: EmployeeService, employee_id: str, document_id: str) -> DocumentLink:
    """Links an existing Document to this Employee -- the generic
    DocumentLink relationship, translated internally from the explicit
    employee_id the caller provides (never a raw entity_type/entity_id pair
    constructed outside this boundary). Goes through DocumentService.
    add_link() itself (never the repository directly) so every existing
    central Documents guarantee -- duplicate-link rejection, audit entry,
    the DocumentReferenceLinked event -- stays intact and is never
    bypassed. The additional record_activity() call below is this
    boundary's own responsibility: add_link() only ever writes to the
    Document's own activity timeline (entity_type="document"), so without
    this second, explicit call here, linking a Document would never appear
    on the Employee's own Activity feed."""
    require_permission(service._user_session, "employee.manage", operation_label="link employee document")
    require_permission(service._user_session, _DOCUMENT_MANAGE_PERMISSION, operation_label="link employee document")
    employee, organization_id = _require_employee_in_context(service, employee_id)
    document_service = _require_document_service(service)
    document: Document = document_service.get_document(document_id)
    link = document_service.add_link(
        document_id=document_id,
        module_code=_MODULE_CODE,
        entity_type=_ENTITY_TYPE,
        entity_id=employee_id,
    )
    with service._uow_factory.create(context=service._new_context()) as uow:
        record_activity(
            uow,
            action="employee.document_link",
            entity_type=_ENTITY_TYPE,
            entity_id=employee_id,
            module=_MODULE_CODE,
            organization_id=organization_id,
            message=f"Document linked - {document.title}",
            icon="documents",
            commit=False,
        )
        uow.commit()
    return link


def unlink_employee_document(service: EmployeeService, employee_id: str, link_id: str) -> None:
    """The reverse of link_employee_document -- same dual permission gate,
    goes through DocumentService.remove_link() itself (never the
    repository directly). remove_link() deletes only the DocumentLink
    relationship row; it never touches the underlying Document (see the
    Documents stack audit) -- unlinking a Document from an Employee can
    never delete that Document."""
    require_permission(service._user_session, "employee.manage", operation_label="unlink employee document")
    require_permission(service._user_session, _DOCUMENT_MANAGE_PERMISSION, operation_label="unlink employee document")
    employee, organization_id = _require_employee_in_context(service, employee_id)
    document_service = _require_document_service(service)
    link = document_service.get_link(link_id)
    if link.entity_type != _ENTITY_TYPE or link.entity_id != employee_id or link.module_code != _MODULE_CODE:
        raise NotFoundError("Document link not found for this employee.", code="EMPLOYEE_DOCUMENT_LINK_NOT_FOUND")
    document = document_service.get_document(link.document_id)
    document_title = document.title
    document_service.remove_link(link_id)
    with service._uow_factory.create(context=service._new_context()) as uow:
        record_activity(
            uow,
            action="employee.document_unlink",
            entity_type=_ENTITY_TYPE,
            entity_id=employee_id,
            module=_MODULE_CODE,
            organization_id=organization_id,
            message=f"Document unlinked - {document_title}",
            icon="documents",
            type="warning",
            commit=False,
        )
        uow.commit()


__all__ = ["link_employee_document", "list_employee_documents_page", "unlink_employee_document"]
