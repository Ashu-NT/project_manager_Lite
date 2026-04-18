from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.org.domain import Organization
from core.platform.documents.domain import (
    Document,
    DocumentClassification,
    DocumentLink,
    DocumentStorageKind,
    DocumentStructure,
    DocumentType,
)
from core.platform.documents.interfaces import (
    DocumentLinkRepository,
    DocumentRepository,
    DocumentStructureRepository,
)
from core.platform.documents.support import (
    coerce_document_type as _coerce_document_type,
    coerce_storage_kind as _coerce_storage_kind,
    default_file_name as _default_file_name,
    infer_mime_type as _infer_mime_type,
    normalize_confidentiality as _normalize_confidentiality,
    normalize_entity_label as _normalize_entity_label,
    normalize_module_code as _normalize_module_code,
    normalize_object_scope as _normalize_object_scope,
    normalize_optional_text as _normalize_optional_text,
    normalize_structure_code as _normalize_structure_code,
    normalize_structure_name as _normalize_structure_name,
)
from core.platform.notifications.domain_events import domain_events
from src.core.platform.org.support import normalize_code, normalize_name


def _normalize_optional_date(value: date | None) -> date | None:
    return value


def _validate_document_dates(*, effective_date: date | None, review_date: date | None) -> None:
    if effective_date is not None and review_date is not None and review_date < effective_date:
        raise ValidationError(
            "Document review date cannot be earlier than the effective date.",
            code="DOCUMENT_REVIEW_DATE_INVALID",
        )


class DocumentService:
    def __init__(
        self,
        session: Session,
        document_repo: DocumentRepository,
        link_repo: DocumentLinkRepository,
        structure_repo: DocumentStructureRepository,
        *,
        organization_repo: OrganizationRepository,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._document_repo = document_repo
        self._link_repo = link_repo
        self._structure_repo = structure_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def get_context_organization(self) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="view document context")
        return self._active_organization()

    def list_documents(self, *, active_only: bool | None = None) -> list[Document]:
        require_permission(self._user_session, "settings.manage", operation_label="list documents")
        organization = self._active_organization()
        return self._document_repo.list_for_organization(organization.id, active_only=active_only)

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
        require_permission(self._user_session, "settings.manage", operation_label="create document structure")
        organization = self._active_organization()
        normalized_code = _normalize_structure_code(structure_code)
        if self._structure_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError(
                "Document structure code already exists in the active organization.",
                code="DOCUMENT_STRUCTURE_CODE_EXISTS",
            )
        parent = self._resolve_structure_for_context(parent_structure_id, organization=organization)
        structure = DocumentStructure.create(
            organization_id=organization.id,
            structure_code=normalized_code,
            name=_normalize_structure_name(name),
            description=_normalize_optional_text(description),
            parent_structure_id=parent.id if parent is not None else None,
            object_scope=_normalize_object_scope(object_scope),
            default_document_type=_coerce_document_type(default_document_type),
            sort_order=int(sort_order or 0),
            is_active=bool(is_active),
            notes=_normalize_optional_text(notes),
        )
        try:
            self._structure_repo.add(structure)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Document structure code already exists in the active organization.",
                code="DOCUMENT_STRUCTURE_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="document_structure.create",
            entity_type="document_structure",
            entity_id=structure.id,
            details={
                "organization_id": organization.id,
                "structure_code": structure.structure_code,
                "object_scope": structure.object_scope,
                "default_document_type": structure.default_document_type.value,
            },
        )
        domain_events.documents_changed.emit(structure.id)
        return structure

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
        require_permission(self._user_session, "settings.manage", operation_label="update document structure")
        organization = self._active_organization()
        structure = self._structure_repo.get(structure_id)
        if structure is None or structure.organization_id != organization.id:
            raise NotFoundError("Document structure not found in the active organization.", code="DOCUMENT_STRUCTURE_NOT_FOUND")
        if expected_version is not None and structure.version != expected_version:
            raise ConcurrencyError(
                "Document structure changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if structure_code is not None:
            normalized_code = _normalize_structure_code(structure_code)
            existing = self._structure_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != structure.id:
                raise ValidationError(
                    "Document structure code already exists in the active organization.",
                    code="DOCUMENT_STRUCTURE_CODE_EXISTS",
                )
            structure.structure_code = normalized_code
        if name is not None:
            structure.name = _normalize_structure_name(name)
        if description is not None:
            structure.description = _normalize_optional_text(description)
        if parent_structure_id is not None:
            parent = self._resolve_structure_for_context(parent_structure_id, organization=organization)
            if parent is not None and parent.id == structure.id:
                raise ValidationError("A document structure cannot be its own parent.", code="DOCUMENT_STRUCTURE_PARENT_INVALID")
            structure.parent_structure_id = parent.id if parent is not None else None
        if object_scope is not None:
            structure.object_scope = _normalize_object_scope(object_scope)
        if default_document_type is not None:
            structure.default_document_type = _coerce_document_type(default_document_type)
        if sort_order is not None:
            structure.sort_order = int(sort_order or 0)
        if is_active is not None:
            structure.is_active = bool(is_active)
        if notes is not None:
            structure.notes = _normalize_optional_text(notes)
        try:
            self._structure_repo.update(structure)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Document structure code already exists in the active organization.",
                code="DOCUMENT_STRUCTURE_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="document_structure.update",
            entity_type="document_structure",
            entity_id=structure.id,
            details={
                "organization_id": organization.id,
                "structure_code": structure.structure_code,
                "object_scope": structure.object_scope,
                "default_document_type": structure.default_document_type.value,
                "is_active": structure.is_active,
            },
        )
        domain_events.documents_changed.emit(structure.id)
        return structure

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
        require_permission(self._user_session, "settings.manage", operation_label="create document")
        organization = self._active_organization()
        normalized_code = normalize_code(document_code, label="Document code")
        normalized_title = normalize_name(title, label="Document title")
        normalized_uri = _normalize_entity_label(
            storage_uri if storage_uri is not None else storage_ref,
            code="DOCUMENT_STORAGE_REF_REQUIRED",
            label="Document storage URI",
        )
        _validate_document_dates(effective_date=effective_date, review_date=review_date)
        if self._document_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError("Document code already exists in the active organization.", code="DOCUMENT_CODE_EXISTS")
        structure = self._resolve_structure_for_context(document_structure_id, organization=organization)
        principal = self._user_session.principal if self._user_session is not None else None
        normalized_file_name = _default_file_name(normalized_uri, file_name)
        normalized_mime_type = _normalize_optional_text(mime_type) or _infer_mime_type(normalized_file_name or normalized_uri)
        document = Document.create(
            organization_id=organization.id,
            document_code=normalized_code,
            title=normalized_title,
            document_type=_coerce_document_type(document_type if document_type is not None else classification),
            document_structure_id=structure.id if structure is not None else None,
            storage_kind=_coerce_storage_kind(storage_kind),
            storage_uri=normalized_uri,
            file_name=normalized_file_name,
            mime_type=normalized_mime_type,
            source_system=_normalize_optional_text(source_system) or "platform",
            uploaded_at=uploaded_at or datetime.now(timezone.utc),
            uploaded_by_user_id=uploaded_by_user_id or (principal.user_id if principal is not None else None),
            effective_date=_normalize_optional_date(effective_date),
            review_date=_normalize_optional_date(review_date),
            confidentiality_level=_normalize_confidentiality(confidentiality_level),
            business_version_label=_normalize_optional_text(business_version_label or revision),
            is_current=bool(is_current),
            notes=_normalize_optional_text(notes),
            is_active=bool(is_active),
        )
        try:
            self._document_repo.add(document)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Document code already exists in the active organization.", code="DOCUMENT_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="document.create",
            entity_type="document",
            entity_id=document.id,
            details={
                "organization_id": organization.id,
                "document_code": document.document_code,
                "title": document.title,
                "document_type": document.document_type.value,
                "document_structure_id": document.document_structure_id,
                "storage_kind": document.storage_kind.value,
            },
        )
        domain_events.documents_changed.emit(document.id)
        return document

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
        require_permission(self._user_session, "settings.manage", operation_label="update document")
        organization = self._active_organization()
        document = self._document_repo.get(document_id)
        if document is None or document.organization_id != organization.id:
            raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")
        if expected_version is not None and document.version != expected_version:
            raise ConcurrencyError("Document changed since you opened it. Refresh and try again.", code="STALE_WRITE")
        if document_code is not None:
            normalized_code = normalize_code(document_code, label="Document code")
            existing = self._document_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != document.id:
                raise ValidationError("Document code already exists in the active organization.", code="DOCUMENT_CODE_EXISTS")
            document.document_code = normalized_code
        if title is not None:
            document.title = normalize_name(title, label="Document title")
        if document_type is not None or classification is not None:
            document.document_type = _coerce_document_type(
                document_type if document_type is not None else classification
            )
        if document_structure_id is not None:
            structure = self._resolve_structure_for_context(document_structure_id, organization=organization)
            document.document_structure_id = structure.id if structure is not None else None
        if storage_kind is not None:
            document.storage_kind = _coerce_storage_kind(storage_kind)
        if storage_uri is not None or storage_ref is not None:
            document.storage_uri = _normalize_entity_label(
                storage_uri if storage_uri is not None else storage_ref,
                code="DOCUMENT_STORAGE_REF_REQUIRED",
                label="Document storage URI",
            )
        if file_name is not None:
            document.file_name = _default_file_name(document.storage_uri, file_name)
        if mime_type is not None:
            document.mime_type = _normalize_optional_text(mime_type) or _infer_mime_type(
                document.file_name or document.storage_uri
            )
        elif storage_uri is not None or file_name is not None:
            document.mime_type = _normalize_optional_text(document.mime_type) or _infer_mime_type(
                document.file_name or document.storage_uri
            )
        if source_system is not None:
            document.source_system = _normalize_optional_text(source_system)
        if uploaded_at is not None:
            document.uploaded_at = uploaded_at
        if uploaded_by_user_id is not None:
            document.uploaded_by_user_id = _normalize_optional_text(uploaded_by_user_id) or None
        next_effective_date = effective_date if effective_date is not None else document.effective_date
        next_review_date = review_date if review_date is not None else document.review_date
        _validate_document_dates(effective_date=next_effective_date, review_date=next_review_date)
        if effective_date is not None:
            document.effective_date = _normalize_optional_date(effective_date)
        if review_date is not None:
            document.review_date = _normalize_optional_date(review_date)
        if confidentiality_level is not None:
            document.confidentiality_level = _normalize_confidentiality(confidentiality_level)
        if business_version_label is not None or revision is not None:
            document.business_version_label = _normalize_optional_text(
                business_version_label if business_version_label is not None else revision
            )
        if is_current is not None:
            document.is_current = bool(is_current)
        if notes is not None:
            document.notes = _normalize_optional_text(notes)
        if is_active is not None:
            document.is_active = bool(is_active)
        try:
            self._document_repo.update(document)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Document code already exists in the active organization.", code="DOCUMENT_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="document.update",
            entity_type="document",
            entity_id=document.id,
            details={
                "organization_id": organization.id,
                "document_code": document.document_code,
                "title": document.title,
                "document_type": document.document_type.value,
                "document_structure_id": document.document_structure_id,
                "storage_kind": document.storage_kind.value,
                "is_active": str(document.is_active),
            },
        )
        domain_events.documents_changed.emit(document.id)
        return document

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
        require_permission(self._user_session, "settings.manage", operation_label="link document")
        document = self._require_document_in_context(document_id)
        normalized_module = _normalize_module_code(module_code)
        normalized_entity_type = _normalize_entity_label(
            entity_type,
            code="DOCUMENT_ENTITY_TYPE_REQUIRED",
            label="Entity type",
        )
        normalized_entity_id = _normalize_entity_label(
            entity_id,
            code="DOCUMENT_ENTITY_ID_REQUIRED",
            label="Entity id",
        )
        normalized_role = _normalize_optional_text(link_role)
        existing = self._link_repo.find_existing(
            document_id=document.id,
            module_code=normalized_module,
            entity_type=normalized_entity_type,
            entity_id=normalized_entity_id,
            link_role=normalized_role,
        )
        if existing is not None:
            raise ValidationError("This document link already exists.", code="DOCUMENT_LINK_EXISTS")
        link = DocumentLink.create(
            organization_id=document.organization_id,
            document_id=document.id,
            module_code=normalized_module,
            entity_type=normalized_entity_type,
            entity_id=normalized_entity_id,
            link_role=normalized_role,
        )
        try:
            self._link_repo.add(link)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("This document link already exists.", code="DOCUMENT_LINK_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="document.link",
            entity_type="document",
            entity_id=document.id,
            details={
                "module_code": link.module_code,
                "entity_type": link.entity_type,
                "entity_id": link.entity_id,
                "link_role": link.link_role,
            },
        )
        domain_events.documents_changed.emit(document.id)
        return link

    def remove_link(self, link_id: str) -> None:
        require_permission(self._user_session, "settings.manage", operation_label="unlink document")
        link = self._link_repo.get(link_id)
        if link is None:
            raise NotFoundError("Document link not found.", code="DOCUMENT_LINK_NOT_FOUND")
        document = self._require_document_in_context(link.document_id)
        try:
            self._link_repo.delete(link.id)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="document.unlink",
            entity_type="document",
            entity_id=document.id,
            details={
                "module_code": link.module_code,
                "entity_type": link.entity_type,
                "entity_id": link.entity_id,
                "link_role": link.link_role,
            },
        )
        domain_events.documents_changed.emit(document.id)

    def list_links_for_entity(self, *, module_code: str, entity_type: str, entity_id: str) -> list[DocumentLink]:
        require_permission(self._user_session, "settings.manage", operation_label="list entity document links")
        organization = self._active_organization()
        return self._link_repo.list_for_entity(
            organization.id,
            _normalize_module_code(module_code),
            _normalize_entity_label(entity_type, code="DOCUMENT_ENTITY_TYPE_REQUIRED", label="Entity type"),
            _normalize_entity_label(entity_id, code="DOCUMENT_ENTITY_ID_REQUIRED", label="Entity id"),
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
        normalized_id = _normalize_optional_text(structure_id)
        if not normalized_id:
            return None
        structure = self._structure_repo.get(normalized_id)
        if structure is None or structure.organization_id != organization.id:
            raise NotFoundError("Document structure not found in the active organization.", code="DOCUMENT_STRUCTURE_NOT_FOUND")
        return structure

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization


__all__ = ["DocumentService"]
