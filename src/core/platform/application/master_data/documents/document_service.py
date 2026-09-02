from __future__ import annotations

from datetime import date, datetime
from typing import Any

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    DocumentRollupSummary,
    PlatformOverviewRollupReader,
)
from src.core.platform.contract.repositories.master_data.documents.contracts import (
    DocumentLinkRepository,
    DocumentRepository,
    DocumentStructureRepository,
)
from src.core.platform.contract.uow.document_unit_of_work import DocumentUnitOfWorkFactory
from src.core.platform.domain.master_data.documents import (
    Document,
    DocumentClassification,
    DocumentLink,
    DocumentStorageKind,
    DocumentStructure,
    DocumentType,
)
from src.core.platform.domain.master_data.documents.document_link import (
    normalize_document_entity_id as _normalize_document_entity_id,
    normalize_document_entity_type as _normalize_document_entity_type,
    normalize_document_module_code as _normalize_document_module_code,
)
from src.core.platform.domain.master_data.documents.support import (
    normalize_object_scope as _normalize_object_scope,
)
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock
from sqlalchemy.orm import Session

from . import document_commands as _cmd
from .document_context import active_organization, resolve_structure_for_context


class DocumentService:
    def __init__(
        self,
        session: Session,
        document_repo: DocumentRepository,
        link_repo: DocumentLinkRepository,
        structure_repo: DocumentStructureRepository,
        *,
        organization_repo: OrganizationRepository,
        user_session: Any = None,
        enterprise_audit_service: Any = None,
        tenant_context_service: TenantContextService | None = None,
        overview_rollup_reader: PlatformOverviewRollupReader | None = None,
        uow_factory: DocumentUnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._session = session
        self._document_repo = document_repo
        self._link_repo = link_repo
        self._structure_repo = structure_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._clock = clock
        self._enterprise_audit_service = enterprise_audit_service
        self._tenant_context_service = tenant_context_service
        self._overview_rollup_reader = overview_rollup_reader
        self._uow_factory = uow_factory

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    def get_context_organization(self) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="view document context")
        return self._active_organization()

    def list_documents(self, *, active_only: bool | None = None) -> list[Document]:
        require_permission(self._user_session, "settings.manage", operation_label="list documents")
        organization = self._active_organization()
        return self._document_repo.list_for_organization(organization.id, active_only=active_only)

    def get_document_rollup_summary(self) -> DocumentRollupSummary:
        require_permission(self._user_session, "settings.manage", operation_label="view document rollup summary")
        organization = self._active_organization()
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
    ) -> list[DocumentStructure]:
        require_permission(self._user_session, "settings.manage", operation_label="list document structures")
        organization = self._active_organization()
        resolved_scope = _normalize_object_scope(object_scope) if object_scope is not None else None
        return self._structure_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            object_scope=resolved_scope,
        )

    def create_document_structure(
        self,
        *,
        structure_code: str,
        name: str,
        description: str = "",
        parent_structure_id: str | None = None,
        object_scope: str = "GENERAL",
        default_document_type: DocumentType | str | None = None,
        sort_order: int = 0,
        is_active: bool = True,
        notes: str = "",
    ) -> DocumentStructure:
        return _cmd.create_document_structure(
            self,
            structure_code=structure_code,
            name=name,
            description=description,
            parent_structure_id=parent_structure_id,
            object_scope=object_scope,
            default_document_type=default_document_type,
            sort_order=sort_order,
            is_active=is_active,
            notes=notes,
        )

    def update_document_structure(
        self,
        structure_id: str,
        *,
        structure_code: str | None = None,
        name: str | None = None,
        description: str | None = None,
        parent_structure_id: str | None = None,
        object_scope: str | None = None,
        default_document_type: DocumentType | str | None = None,
        sort_order: int | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> DocumentStructure:
        return _cmd.update_document_structure(
            self,
            structure_id,
            structure_code=structure_code,
            name=name,
            description=description,
            parent_structure_id=parent_structure_id,
            object_scope=object_scope,
            default_document_type=default_document_type,
            sort_order=sort_order,
            is_active=is_active,
            notes=notes,
            expected_version=expected_version,
        )

    def create_document(
        self,
        *,
        document_code: str,
        title: str,
        document_type: DocumentType | str | None = None,
        classification: DocumentClassification | str | None = None,
        document_structure_id: str | None = None,
        storage_kind: DocumentStorageKind | str = DocumentStorageKind.FILE_PATH,
        storage_uri: str | None = None,
        storage_ref: str | None = None,
        file_name: str = "",
        mime_type: str = "",
        source_system: str = "",
        uploaded_at: datetime | None = None,
        uploaded_by_user_id: str | None = None,
        effective_date: date | None = None,
        review_date: date | None = None,
        confidentiality_level: str = "",
        business_version_label: str = "",
        revision: str = "",
        is_current: bool = True,
        notes: str = "",
        is_active: bool = True,
    ) -> Document:
        return _cmd.create_document(
            self,
            document_code=document_code,
            title=title,
            document_type=document_type,
            classification=classification,
            document_structure_id=document_structure_id,
            storage_kind=storage_kind,
            storage_uri=storage_uri,
            storage_ref=storage_ref,
            file_name=file_name,
            mime_type=mime_type,
            source_system=source_system,
            uploaded_at=uploaded_at,
            uploaded_by_user_id=uploaded_by_user_id,
            effective_date=effective_date,
            review_date=review_date,
            confidentiality_level=confidentiality_level,
            business_version_label=business_version_label,
            revision=revision,
            is_current=is_current,
            notes=notes,
            is_active=is_active,
        )

    def update_document(
        self,
        document_id: str,
        *,
        document_code: str | None = None,
        title: str | None = None,
        document_type: DocumentType | str | None = None,
        classification: DocumentClassification | str | None = None,
        document_structure_id: str | None = None,
        storage_kind: DocumentStorageKind | str | None = None,
        storage_uri: str | None = None,
        storage_ref: str | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
        source_system: str | None = None,
        uploaded_at: datetime | None = None,
        uploaded_by_user_id: str | None = None,
        effective_date: date | None = None,
        review_date: date | None = None,
        confidentiality_level: str | None = None,
        business_version_label: str | None = None,
        revision: str | None = None,
        is_current: bool | None = None,
        notes: str | None = None,
        is_active: bool | None = None,
        expected_version: int | None = None,
    ) -> Document:
        return _cmd.update_document(
            self,
            document_id,
            document_code=document_code,
            title=title,
            document_type=document_type,
            classification=classification,
            document_structure_id=document_structure_id,
            storage_kind=storage_kind,
            storage_uri=storage_uri,
            storage_ref=storage_ref,
            file_name=file_name,
            mime_type=mime_type,
            source_system=source_system,
            uploaded_at=uploaded_at,
            uploaded_by_user_id=uploaded_by_user_id,
            effective_date=effective_date,
            review_date=review_date,
            confidentiality_level=confidentiality_level,
            business_version_label=business_version_label,
            revision=revision,
            is_current=is_current,
            notes=notes,
            is_active=is_active,
            expected_version=expected_version,
        )

    def list_links(self, document_id: str) -> list[DocumentLink]:
        require_permission(self._user_session, "settings.manage", operation_label="list document links")
        document = self._require_document_in_context(document_id)
        return self._link_repo.list_for_document(document.id)

    def add_link(
        self,
        *,
        document_id: str,
        module_code: str,
        entity_type: str,
        entity_id: str,
        link_role: str = "",
    ) -> DocumentLink:
        return _cmd.add_link(
            self,
            document_id=document_id,
            module_code=module_code,
            entity_type=entity_type,
            entity_id=entity_id,
            link_role=link_role,
        )

    def remove_link(self, link_id: str) -> None:
        _cmd.remove_link(self, link_id)

    def list_links_for_entity(self, *, module_code: str, entity_type: str, entity_id: str) -> list[DocumentLink]:
        require_permission(self._user_session, "settings.manage", operation_label="list entity document links")
        organization = self._active_organization()
        return self._link_repo.list_for_entity(
            organization.id,
            _normalize_document_module_code(module_code),
            _normalize_document_entity_type(entity_type),
            _normalize_document_entity_id(entity_id),
        )

    def _require_document_in_context(self, document_id: str) -> Document:
        organization = self._active_organization()
        document = self._document_repo.get(document_id)
        if document is None or document.organization_id != organization.id:
            raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")
        return document

    def _resolve_structure_for_context(
        self,
        structure_id: str | None,
        *,
        organization: Organization,
    ) -> DocumentStructure | None:
        return resolve_structure_for_context(
            structure_id, organization=organization, structure_repo=self._structure_repo
        )

    def _active_organization(self) -> Organization:
        return active_organization(self)


__all__ = ["DocumentService"]
