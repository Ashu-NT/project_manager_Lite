from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.shared.audit import record_audit_entry
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.contract.repositories.master_data.documents.contracts import (
    DocumentLinkRepository,
    DocumentRepository,
    DocumentStructureRepository,
)
from src.core.platform.contract.uow.document_unit_of_work import DocumentUnitOfWorkFactory
from src.core.platform.domain.master_data.documents import Document, DocumentLink, DocumentType
from src.core.platform.domain.master_data.documents.events import (
    DocumentCreated,
    DocumentReferenceLinked,
    DocumentReferenceUnlinked,
)
from src.core.platform.domain.master_data.documents.document_link import (
    normalize_document_entity_id,
    normalize_document_entity_type,
    normalize_document_link_role,
    normalize_document_module_code,
)
from src.core.platform.domain.master_data.documents.support import (
    coerce_document_type,
    infer_file_name,
    infer_mime_type,
    infer_storage_kind,
    infer_title,
    normalize_optional_text,
)
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock

from .document_context import active_organization, resolve_structure_for_context


def _build_document_code(*, module_code: str, entity_type: str) -> str:
    prefix = f"{module_code}-{entity_type}".replace("_", "-").upper()
    return f"{prefix}-{uuid4().hex[:12].upper()}"


def register_entity_attachments_in_uow(
    *,
    uow: Any,
    organization: Organization,
    module_code: str,
    entity_type: str,
    entity_id: str,
    attachments: list[str] | None,
    clock: Clock,
    document_type: DocumentType | str | None = None,
    document_structure_id: str | None = None,
    business_version_label: str = "",
    revision: str = "",
    source_system: str = "",
    link_role: str = "attachment",
    uploaded_by_user_id: str | None = None,
    notes: str = "",
) -> list[Document]:

    tokens = [normalize_optional_text(item) for item in (attachments or []) if normalize_optional_text(item)]
    if not tokens:
        return []
    normalized_module = normalize_document_module_code(module_code)
    normalized_entity_type = normalize_document_entity_type(entity_type)
    normalized_entity_id = normalize_document_entity_id(entity_id)
    normalized_role = normalize_document_link_role(link_role)
    resolved_type = coerce_document_type(document_type)
    structure = resolve_structure_for_context(
        document_structure_id, organization=organization, structure_repo=uow.structures
    )
    created: list[Document] = []
    for token in tokens:
        now = clock.now()
        document = Document.create(
            organization_id=organization.id,
            document_code=_build_document_code(
                module_code=normalized_module,
                entity_type=normalized_entity_type,
            ),
            title=infer_title(token),
            document_type=resolved_type,
            document_structure_id=structure.id if structure is not None else None,
            storage_kind=infer_storage_kind(token),
            storage_uri=token,
            file_name=infer_file_name(token),
            mime_type=infer_mime_type(token),
            source_system=normalize_optional_text(source_system) or normalized_module,
            uploaded_at=now,
            uploaded_by_user_id=uploaded_by_user_id,
            business_version_label=normalize_optional_text(business_version_label or revision),
            notes=normalize_optional_text(notes),
        )
        uow.documents.add(document)
        uow._session.flush()
        link = DocumentLink.create(
            organization_id=organization.id,
            document_id=document.id,
            module_code=normalized_module,
            entity_type=normalized_entity_type,
            entity_id=normalized_entity_id,
            link_role=normalized_role,
        )
        uow.links.add(link)
        created.append(document)
        record_audit_entry(
            uow,
            operation="create",
            entity_type="document",
            entity_id=document.id,
            module="platform",
            severity="low",
            metadata={
                "action": "document.linked_attachment.create",
                "module_code": normalized_module,
                "entity_type": normalized_entity_type,
                "entity_id": normalized_entity_id,
                "link_role": normalized_role,
                "storage_kind": document.storage_kind.value,
                "storage_uri": document.storage_uri,
                "document_structure_id": document.document_structure_id,
            },
            commit=False,
            fail_closed=True,
        )
        uow.record_event(
            DocumentCreated(
                tenant_id=organization.tenant_id,
                organization_id=organization.id,
                document_id=document.id,
                occurred_at=now,
            )
        )
        uow.record_event(
            DocumentReferenceLinked(
                tenant_id=organization.tenant_id,
                organization_id=organization.id,
                document_id=document.id,
                module_code=normalized_module,
                entity_type=normalized_entity_type,
                entity_id=normalized_entity_id,
                link_role=normalized_role,
                occurred_at=now,
            )
        )
    return created


def link_existing_document_in_uow(
    *,
    uow: Any,
    organization: Organization,
    module_code: str,
    entity_type: str,
    entity_id: str,
    document_id: str,
    clock: Clock,
    link_role: str = "reference",
) -> DocumentLink:
    """Transaction-neutral core of `link_existing_document` -- see `register_entity_attachments_
    in_uow`'s docstring for the same never-commits/never-rolls-back/never-publishes contract."""
    document = uow.documents.get(document_id)
    if document is None or document.organization_id != organization.id:
        raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")
    if not document.is_active:
        raise ValidationError("Document must be active before it can be linked.", code="DOCUMENT_INACTIVE")
    normalized_module = normalize_document_module_code(module_code)
    normalized_entity_type = normalize_document_entity_type(entity_type)
    normalized_entity_id = normalize_document_entity_id(entity_id)
    normalized_role = normalize_document_link_role(link_role)
    link = DocumentLink.create(
        organization_id=organization.id,
        document_id=document.id,
        module_code=normalized_module,
        entity_type=normalized_entity_type,
        entity_id=normalized_entity_id,
        link_role=normalized_role,
    )
    existing = uow.links.find_existing(
        document_id=link.document_id,
        module_code=link.module_code,
        entity_type=link.entity_type,
        entity_id=link.entity_id,
        link_role=link.link_role,
    )
    if existing is not None:
        raise ValidationError("Document link already exists.", code="DOCUMENT_LINK_EXISTS")
    uow.links.add(link)
    record_audit_entry(
        uow,
        operation="update",
        entity_type="document",
        entity_id=document.id,
        module="platform",
        severity="low",
        metadata={
            "action": "document.link_existing",
            "module_code": normalized_module,
            "entity_type": normalized_entity_type,
            "entity_id": normalized_entity_id,
            "link_role": normalized_role,
        },
        commit=False,
        fail_closed=True,
    )
    uow.record_event(
        DocumentReferenceLinked(
            tenant_id=organization.tenant_id,
            organization_id=organization.id,
            document_id=document.id,
            module_code=normalized_module,
            entity_type=normalized_entity_type,
            entity_id=normalized_entity_id,
            link_role=normalized_role,
            occurred_at=clock.now(),
        )
    )
    return link


class DocumentIntegrationService:
    """Shared document plumbing for business modules after module-level auth has passed."""

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
        uow_factory: DocumentUnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._session = session
        self._document_repo = document_repo
        self._link_repo = link_repo
        self._structure_repo = structure_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._tenant_context_service = tenant_context_service
        self._uow_factory = uow_factory
        self._clock = clock

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    def register_entity_attachments(
        self,
        *,
        required_permission: str,
        operation_label: str,
        module_code: str,
        entity_type: str,
        entity_id: str,
        attachments: list[str] | None,
        document_type: DocumentType | str | None = None,
        document_structure_id: str | None = None,
        business_version_label: str = "",
        revision: str = "",
        source_system: str = "",
        link_role: str = "attachment",
        uploaded_by_user_id: str | None = None,
        notes: str = "",
    ) -> list[Document]:
        require_permission(self._user_session, required_permission, operation_label=operation_label)
        tokens = [normalize_optional_text(item) for item in (attachments or []) if normalize_optional_text(item)]
        if not tokens:
            return []
        organization = self._active_organization()
        principal = self._user_session.principal if self._user_session is not None else None
        uploader = uploaded_by_user_id or getattr(principal, "user_id", None)
        with self._uow_factory.create(context=self._new_context()) as uow:
            created = register_entity_attachments_in_uow(
                uow=uow,
                organization=organization,
                module_code=module_code,
                entity_type=entity_type,
                entity_id=entity_id,
                attachments=tokens,
                clock=self._clock,
                document_type=document_type,
                document_structure_id=document_structure_id,
                business_version_label=business_version_label,
                revision=revision,
                source_system=source_system,
                link_role=link_role,
                uploaded_by_user_id=uploader,
                notes=notes,
            )
            uow.commit()
        return created

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
        organization = self._active_organization()
        links = self._link_repo.list_for_entity(
            organization.id,
            normalize_document_module_code(module_code),
            normalize_document_entity_type(entity_type),
            normalize_document_entity_id(entity_id),
        )
        rows: list[Document] = []
        for link in links:
            document = self._document_repo.get(link.document_id)
            if document is None or document.organization_id != organization.id:
                continue
            if active_only is not None and document.is_active != bool(active_only):
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
        organization = self._active_organization()
        return self._document_repo.list_for_organization(organization.id, active_only=active_only)

    def link_existing_document(
        self,
        *,
        required_permission: str,
        operation_label: str,
        module_code: str,
        entity_type: str,
        entity_id: str,
        document_id: str,
        link_role: str = "reference",
    ) -> DocumentLink:
        require_permission(self._user_session, required_permission, operation_label=operation_label)
        organization = self._active_organization()
        with self._uow_factory.create(context=self._new_context()) as uow:
            try:
                link = link_existing_document_in_uow(
                    uow=uow,
                    organization=organization,
                    module_code=module_code,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    document_id=document_id,
                    clock=self._clock,
                    link_role=link_role,
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError("Document link already exists.", code="DOCUMENT_LINK_EXISTS") from exc
        return link

    def unlink_existing_document(
        self,
        *,
        required_permission: str,
        operation_label: str,
        module_code: str,
        entity_type: str,
        entity_id: str,
        document_id: str,
        link_role: str = "reference",
    ) -> None:
        require_permission(self._user_session, required_permission, operation_label=operation_label)
        organization = self._active_organization()
        with self._uow_factory.create(context=self._new_context()) as uow:
            document = uow.documents.get(document_id)
            if document is None or document.organization_id != organization.id:
                raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")
            normalized_module = normalize_document_module_code(module_code)
            normalized_entity_type = normalize_document_entity_type(entity_type)
            normalized_entity_id = normalize_document_entity_id(entity_id)
            normalized_role = normalize_document_link_role(link_role)
            existing = uow.links.find_existing(
                document_id=document.id,
                module_code=normalized_module,
                entity_type=normalized_entity_type,
                entity_id=normalized_entity_id,
                link_role=normalized_role,
            )
            if existing is None:
                raise NotFoundError("Document link not found.", code="DOCUMENT_LINK_NOT_FOUND")
            uow.links.delete(existing.id)
            record_audit_entry(
                uow,
                operation="delete",
                entity_type="document",
                entity_id=document.id,
                module="platform",
                severity="low",
                metadata={
                    "action": "document.unlink_existing",
                    "module_code": normalized_module,
                    "entity_type": normalized_entity_type,
                    "entity_id": normalized_entity_id,
                    "link_role": normalized_role,
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                DocumentReferenceUnlinked(
                    tenant_id=organization.tenant_id,
                    organization_id=organization.id,
                    document_id=document.id,
                    module_code=normalized_module,
                    entity_type=normalized_entity_type,
                    entity_id=normalized_entity_id,
                    link_role=normalized_role,
                    occurred_at=self._clock.now(),
                )
            )
            uow.commit()

    def _resolve_structure_for_context(
        self,
        structure_id: str | None,
        *,
        organization: Organization,
    ) -> Any:
        return resolve_structure_for_context(
            structure_id, organization=organization, structure_repo=self._structure_repo
        )

    def _active_organization(self) -> Organization:
        return active_organization(self)


__all__ = ["DocumentIntegrationService"]
