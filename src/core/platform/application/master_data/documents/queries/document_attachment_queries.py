from __future__ import annotations

from src.core.platform.application.master_data.documents.document_access import (
    attachment_visibility,
    is_document_visible,
)
from src.core.platform.application.master_data.documents.document_context import (
    active_organization,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.contract.port.master_data.documents.document_access_policy import (
    DocumentAccessPolicy,
)
from src.core.platform.contract.repositories.master_data.documents.contracts import (
    DocumentLinkRepository,
    DocumentRepository,
)
from src.core.platform.domain.master_data.documents import Document
from src.core.platform.domain.master_data.documents.document_link import (
    normalize_document_entity_id,
    normalize_document_entity_type,
    normalize_document_module_code,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


class DocumentAttachmentQueryHandler:
    """Entity attachment reads on behalf of another module: documents linked to an
    entity and documents available to link, under the module's own permission."""

    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        link_repo: DocumentLinkRepository,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
        access_policy: DocumentAccessPolicy,
    ) -> None:
        self._document_repo = document_repo
        self._link_repo = link_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._access_policy = access_policy

    def list_documents_for_entity(
        self,
        *,
        required_permission: str,
        operation_label: str,
        module_code: str,
        entity_type: str,
        entity_id: str,
        active_only: bool | None = None,
    ) -> list[Document]:
        require_permission(self._user_session, required_permission, operation_label=operation_label)
        organization = active_organization(self._tenant_context_service)
        links = self._link_repo.list_for_entity(
            organization.id,
            normalize_document_module_code(module_code),
            normalize_document_entity_type(entity_type),
            normalize_document_entity_id(entity_id),
        )
        visibility = attachment_visibility(self._access_policy.visibility())
        rows: list[Document] = []
        for link in links:
            document = self._document_repo.get(link.document_id)
            if document is None or document.organization_id != organization.id:
                continue
            if active_only is not None and document.is_active != bool(active_only):
                continue
            if not is_document_visible(document, visibility, self._link_repo):
                continue
            rows.append(document)
        return rows

    def list_available_documents(
        self,
        *,
        required_permission: str,
        operation_label: str,
        active_only: bool | None = None,
    ) -> list[Document]:
        require_permission(self._user_session, required_permission, operation_label=operation_label)
        organization = active_organization(self._tenant_context_service)
        visibility = attachment_visibility(self._access_policy.visibility())
        return [
            document
            for document in self._document_repo.list_for_organization(organization.id, active_only=active_only)
            if is_document_visible(document, visibility, self._link_repo)
        ]


__all__ = ["DocumentAttachmentQueryHandler"]
