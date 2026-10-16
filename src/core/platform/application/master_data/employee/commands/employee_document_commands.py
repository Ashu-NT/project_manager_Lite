from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.application.master_data.documents.commands.document_commands import (
    DocumentCommandHandler,
)
from src.core.platform.application.master_data.documents.dto.commands.links import (
    DocumentLinkCreateCommand,
)
from src.core.platform.application.master_data.documents.dto.responses.document import (
    DocumentDto,
    DocumentLinkDto,
)
from src.core.platform.application.master_data.documents.queries.document_queries import (
    DocumentQueryHandler,
)
from src.core.platform.application.master_data.employee.employee_document_access import (
    DOCUMENT_MANAGE_PERMISSION as _DOCUMENT_MANAGE_PERMISSION,
)
from src.core.platform.application.master_data.employee.employee_document_access import (
    ENTITY_TYPE as _ENTITY_TYPE,
)
from src.core.platform.application.master_data.employee.employee_document_access import (
    MODULE_CODE as _MODULE_CODE,
)
from src.core.platform.application.master_data.employee.employee_document_access import (
    require_employee_in_context,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.shared.activity import record_activity

if TYPE_CHECKING:
    from src.core.platform.application.tenant.tenancy.tenant_context import (
        TenantContextService,
    )
    from src.core.platform.contract.repositories.master_data.employee.contracts import (
        EmployeeRepository,
    )
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.uow.master_data.employee_unit_of_work import (
    EmployeeUnitOfWorkFactory,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.events.domain_event_context import DomainEventContext


def _new_context(*, causation_id: str | None = None) -> DomainEventContext:
    return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


class EmployeeDocumentCommandHandler:
    """Links and unlinks Platform Documents on an Employee, through the Document handlers'
    own authorization and audit, recording Employee activity in one UoW."""

    def __init__(
        self,
        *,
        employee_repo: EmployeeRepository,
        document_commands: DocumentCommandHandler,
        document_query: DocumentQueryHandler,
        uow_factory: EmployeeUnitOfWorkFactory,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
    ) -> None:
        self._employee_repo = employee_repo
        self._document_commands = document_commands
        self._document_query = document_query
        self._uow_factory = uow_factory
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def link_employee_document(self, employee_id: str, document_id: str) -> DocumentLinkDto:
        """Links an existing Document to this Employee -- the generic
        DocumentLink relationship, translated internally from the explicit
        employee_id the caller provides (never a raw entity_type/entity_id pair
        constructed outside this boundary). Goes through the Document handlers.
        add_link() itself (never the repository directly) so every existing
        central Documents guarantee -- duplicate-link rejection, audit entry,
        the DocumentReferenceLinked event -- stays intact and is never
        bypassed. The additional record_activity() call below is this
        boundary's own responsibility: add_link() only ever writes to the
        Document's own activity timeline (entity_type="document"), so without
        this second, explicit call here, linking a Document would never appear
        on the Employee's own Activity feed."""
        require_permission(self._user_session, "employee.manage", operation_label="link employee document")
        require_permission(self._user_session, _DOCUMENT_MANAGE_PERMISSION, operation_label="link employee document")
        _employee, organization_id = require_employee_in_context(self._employee_repo, self._tenant_context_service, employee_id)
        document: DocumentDto = self._document_query.get_document(document_id)
        link = self._document_commands.add_link(DocumentLinkCreateCommand(document_id=document_id, module_code=_MODULE_CODE, entity_type=_ENTITY_TYPE, entity_id=employee_id))
        with self._uow_factory.create(context=_new_context()) as uow:
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

    def unlink_employee_document(self, employee_id: str, link_id: str) -> None:
        """The reverse of link_employee_document -- same dual permission gate,
        goes through DocumentCommandHandler.remove_link() itself (never the
        repository directly). remove_link() deletes only the DocumentLink
        relationship row; it never touches the underlying Document (see the
        Documents stack audit) -- unlinking a Document from an Employee can
        never delete that Document."""
        require_permission(self._user_session, "employee.manage", operation_label="unlink employee document")
        require_permission(self._user_session, _DOCUMENT_MANAGE_PERMISSION, operation_label="unlink employee document")
        _employee, organization_id = require_employee_in_context(self._employee_repo, self._tenant_context_service, employee_id)
        link = self._document_query.get_link(link_id)
        if link.entity_type != _ENTITY_TYPE or link.entity_id != employee_id or link.module_code != _MODULE_CODE:
            raise NotFoundError("Document link not found for this employee.", code="EMPLOYEE_DOCUMENT_LINK_NOT_FOUND")
        document = self._document_query.get_document(link.document_id)
        document_title = document.title
        self._document_commands.remove_link(link_id)
        with self._uow_factory.create(context=_new_context()) as uow:
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


__all__ = ["EmployeeDocumentCommandHandler"]
