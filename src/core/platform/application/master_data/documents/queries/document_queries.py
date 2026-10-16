from __future__ import annotations

from dataclasses import dataclass, field

import src.core.platform.application.master_data.documents.mappers.document as response_mapper
import src.core.platform.application.master_data.org.mappers.organization as organization_mapper
from src.core.platform.application.master_data.documents.document_access import (
    DOCUMENT_READ_PERMISSION,
    is_document_visible,
)
from src.core.platform.application.master_data.documents.document_context import (
    active_organization,
)
from src.core.platform.application.master_data.documents.dto.responses.document import (
    DocumentDto,
    DocumentLinkDto,
    DocumentPageDto,
    DocumentStructureDto,
)
from src.core.platform.application.master_data.org.dto.responses.organization import (
    OrganizationDto,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.contract.port.master_data.documents.document_access_policy import (
    DocumentAccessPolicy,
    DocumentVisibility,
)
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    DocumentRollupSummary,
    PlatformOverviewRollupReader,
)
from src.core.platform.contract.repositories.master_data.documents.contracts import (
    DocumentLinkRepository,
    DocumentRepository,
    DocumentStructureRepository,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.domain.master_data.documents import (
    Document,
    DocumentLink,
)
from src.core.platform.domain.master_data.documents.document_link import (
    normalize_document_entity_id as _normalize_document_entity_id,
)
from src.core.platform.domain.master_data.documents.document_link import (
    normalize_document_entity_type as _normalize_document_entity_type,
)
from src.core.platform.domain.master_data.documents.document_link import (
    normalize_document_module_code as _normalize_document_module_code,
)
from src.core.platform.domain.master_data.documents.support import (
    normalize_object_scope as _normalize_object_scope,
)
from src.core.platform.domain.security.auth.session import UserSessionContext

_DEFAULT_DOCUMENT_PAGE_SIZE = 25
DOCUMENT_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)


@dataclass(frozen=True)
class DocumentPage:
    items: list[Document] = field(default_factory=list)
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = _DEFAULT_DOCUMENT_PAGE_SIZE


@dataclass(frozen=True)
class EntityDocumentRow:
    document: Document
    link: DocumentLink


@dataclass(frozen=True)
class EntityDocumentPage:
    items: list[EntityDocumentRow] = field(default_factory=list)
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = _DEFAULT_DOCUMENT_PAGE_SIZE


class DocumentQueryHandler:
    """Document reads in the active organization: catalog pages, structures, links,
    entity document pages and the overview rollup."""

    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        link_repo: DocumentLinkRepository,
        structure_repo: DocumentStructureRepository,
        organization_repo: OrganizationRepository,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
        overview_rollup_reader: PlatformOverviewRollupReader | None,
        access_policy: DocumentAccessPolicy,
    ) -> None:
        self._document_repo = document_repo
        self._link_repo = link_repo
        self._structure_repo = structure_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._overview_rollup_reader = overview_rollup_reader
        self._access_policy = access_policy

    def get_context_organization(self) -> OrganizationDto:
        require_permission(self._user_session, DOCUMENT_READ_PERMISSION, operation_label="view document context")
        return organization_mapper.serialize_organization_context(active_organization(self._tenant_context_service))

    def list_documents(self, *, active_only: bool | None = None) -> list[DocumentDto]:
        require_permission(self._user_session, DOCUMENT_READ_PERMISSION, operation_label="list documents")
        organization = active_organization(self._tenant_context_service)
        visibility = self._access_policy.visibility()
        return [response_mapper.serialize_document(row) for row in ([
            document
            for document in self._document_repo.list_for_organization(organization.id, active_only=active_only)
            if self._is_visible(document, visibility)
        ])]

    def list_documents_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_DOCUMENT_PAGE_SIZE,
        search: str = "",
        active_only: bool | None = None,
    ) -> DocumentPageDto:
        """Tenant-scoped read for ANY organization in the caller's tenant --
        unlike list_documents(), not limited to the session's active
        organization. For Organization Detail's Documents tab, where an
        admin may be viewing an organization they haven't switched into.

        Read-only: never used by create/update, which keep using
        active_organization(self._tenant_context_service) (the existing, unchanged domain rule).
        Never gates on the organization's own lifecycle status -- inactive
        and archived organizations' document history remains readable
        here. Does not touch DocumentLink at all -- link/unlink semantics
        are completely untouched by this addition.
        """
        require_permission(
            self._user_session, DOCUMENT_READ_PERMISSION, operation_label="list documents for organization"
        )
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Tenant context is required to list documents.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="list documents for organization"
        )
        target_organization = self._organization_repo.get_for_tenant(organization_id, tenant_id)
        if target_organization is None:
            raise NotFoundError(
                "Organization not found in the current tenant.",
                code="ORGANIZATION_NOT_FOUND",
            )
        normalized_page = max(1, page)
        normalized_page_size = (
            page_size if page_size in DOCUMENT_PAGE_SIZE_OPTIONS else _DEFAULT_DOCUMENT_PAGE_SIZE
        )
        items, total, filtered_total = self._document_repo.list_page_for_organization_in_tenant(
            organization_id,
            tenant_id,
            page=normalized_page,
            page_size=normalized_page_size,
            visibility=self._access_policy.visibility(),
            search=search,
            active_only=active_only,
        )
        return response_mapper.serialize_document_page(DocumentPage(
            items=items,
            total=total,
            filtered_total=filtered_total,
            page=normalized_page,
            page_size=normalized_page_size,
        ))

    def get_document_rollup_summary(self) -> DocumentRollupSummary:
        require_permission(self._user_session, DOCUMENT_READ_PERMISSION, operation_label="view document rollup summary")
        organization = active_organization(self._tenant_context_service)
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="view document rollup summary",
        )
        if self._overview_rollup_reader is None:
            raise RuntimeError("Platform overview rollup reader is not configured.")
        return self._overview_rollup_reader.get_document_summary(
            organization_id=organization.id,
            tenant_id=tenant_id,
        )

    def list_document_structures(
        self,
        *,
        active_only: bool | None = None,
        object_scope: str | None = None,
    ) -> list[DocumentStructureDto]:
        require_permission(self._user_session, DOCUMENT_READ_PERMISSION, operation_label="list document structures")
        organization = active_organization(self._tenant_context_service)
        resolved_scope = _normalize_object_scope(object_scope) if object_scope is not None else None
        return [response_mapper.serialize_document_structure(row) for row in (self._structure_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            object_scope=resolved_scope,
        ))]

    def list_links(self, document_id: str) -> list[DocumentLinkDto]:
        require_permission(self._user_session, DOCUMENT_READ_PERMISSION, operation_label="list document links")
        document = self._require_document_in_context(document_id)
        return [response_mapper.serialize_document_link(row) for row in (self._link_repo.list_for_document(document.id))]

    def list_links_for_entity(self, *, module_code: str, entity_type: str, entity_id: str) -> list[DocumentLink]:
        require_permission(self._user_session, DOCUMENT_READ_PERMISSION, operation_label="list entity document links")
        organization = active_organization(self._tenant_context_service)
        links = self._link_repo.list_for_entity(
            organization.id,
            _normalize_document_module_code(module_code),
            _normalize_document_entity_type(entity_type),
            _normalize_document_entity_id(entity_id),
        )
        visibility = self._access_policy.visibility()
        return [link for link in links if self._is_document_id_visible(link.document_id, visibility)]

    def get_document(self, document_id: str) -> DocumentDto:
        require_permission(self._user_session, DOCUMENT_READ_PERMISSION, operation_label="view document")
        return response_mapper.serialize_document(self._require_document_in_context(document_id))

    def get_link(self, link_id: str) -> DocumentLink:
        require_permission(self._user_session, DOCUMENT_READ_PERMISSION, operation_label="view document link")
        link = self._link_repo.get(link_id)
        organization = active_organization(self._tenant_context_service)
        if (
            link is None
            or link.organization_id != organization.id
            or not self._is_document_id_visible(link.document_id, self._access_policy.visibility())
        ):
            raise NotFoundError("Document link not found.", code="DOCUMENT_LINK_NOT_FOUND")
        return link

    def list_documents_page_for_entity(
        self,
        *,
        module_code: str,
        entity_type: str,
        entity_id: str,
        page: int = 1,
        page_size: int = _DEFAULT_DOCUMENT_PAGE_SIZE,
        search: str = "",
        active_only: bool | None = None,
        document_type: str | None = None,
    ) -> DocumentPageDto:
        """The real entity-scoped, paginated, Document-joined read
        list_links_for_entity() never provided. Always scoped to the
        caller's active organization (consistent with list_links_for_entity
        and with how every current entity consumer -- e.g. Employee --
        always operates in its own active-organization context; there is
        no cross-organization admin use case for this read today)."""
        require_permission(self._user_session, DOCUMENT_READ_PERMISSION, operation_label="list entity documents")
        organization = active_organization(self._tenant_context_service)
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="list entity documents",
        )
        normalized_page = max(1, page)
        normalized_page_size = (
            page_size if page_size in DOCUMENT_PAGE_SIZE_OPTIONS else _DEFAULT_DOCUMENT_PAGE_SIZE
        )
        rows, total, filtered_total = self._link_repo.list_page_for_entity_in_tenant(
            organization.id,
            tenant_id,
            module_code=_normalize_document_module_code(module_code),
            entity_type=_normalize_document_entity_type(entity_type),
            entity_id=_normalize_document_entity_id(entity_id),
            page=normalized_page,
            page_size=normalized_page_size,
            visibility=self._access_policy.visibility(),
            search=search,
            active_only=active_only,
            document_type=document_type,
        )
        return response_mapper.serialize_entity_document_page(EntityDocumentPage(
            items=[EntityDocumentRow(document=document, link=link) for document, link in rows],
            total=total,
            filtered_total=filtered_total,
            page=normalized_page,
            page_size=normalized_page_size,
        ))

    def _require_document_in_context(self, document_id: str) -> Document:
        organization = active_organization(self._tenant_context_service)
        document = self._document_repo.get(document_id)
        # A hidden document is reported exactly like a missing one.
        if (
            document is None
            or document.organization_id != organization.id
            or not self._is_visible(document, self._access_policy.visibility())
        ):
            raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")
        return document

    def _is_visible(self, document: Document, visibility: DocumentVisibility) -> bool:
        return is_document_visible(document, visibility, self._link_repo)

    def _is_document_id_visible(self, document_id: str, visibility: DocumentVisibility) -> bool:
        document = self._document_repo.get(document_id)
        return document is not None and self._is_visible(document, visibility)


__all__ = ["DOCUMENT_PAGE_SIZE_OPTIONS", "DocumentPage", "DocumentQueryHandler", "EntityDocumentPage", "EntityDocumentRow"]
