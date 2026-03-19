from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository
from core.platform.common.models import Organization
from core.platform.documents.domain import (
    Document,
    DocumentClassification,
    DocumentLink,
    DocumentStorageKind,
    DocumentType,
)
from core.platform.documents.interfaces import DocumentLinkRepository, DocumentRepository
from core.platform.notifications.domain_events import domain_events
from core.platform.org.support import normalize_code, normalize_name


def _normalize_optional_text(value: str | None) -> str:
    return (value or "").strip()


def _normalize_module_code(value: str) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        raise ValidationError("Module code is required.", code="DOCUMENT_MODULE_REQUIRED")
    return normalized


def _normalize_entity_label(value: str, *, code: str, label: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValidationError(f"{label} is required.", code=code)
    return normalized


def _coerce_document_type(value: DocumentType | str | None) -> DocumentType:
    if isinstance(value, DocumentType):
        return value
    raw = str(value or DocumentType.GENERAL.value).strip().upper()
    try:
        return DocumentType(raw)
    except ValueError as exc:
        raise ValidationError("Document type is invalid.", code="DOCUMENT_TYPE_INVALID") from exc


def _coerce_storage_kind(value: DocumentStorageKind | str | None) -> DocumentStorageKind:
    if isinstance(value, DocumentStorageKind):
        return value
    raw = str(value or DocumentStorageKind.FILE_PATH.value).strip().upper()
    try:
        return DocumentStorageKind(raw)
    except ValueError as exc:
        raise ValidationError("Document storage kind is invalid.", code="DOCUMENT_STORAGE_KIND_INVALID") from exc


def _normalize_optional_date(value: date | None) -> date | None:
    return value


def _normalize_confidentiality(value: str | None) -> str:
    return _normalize_optional_text(value).upper()


def _default_file_name(storage_uri: str, explicit_file_name: str | None) -> str:
    normalized = _normalize_optional_text(explicit_file_name)
    if normalized:
        return normalized
    candidate = storage_uri.rstrip("/\\").split("/")[-1].split("\\")[-1]
    return candidate.split("?")[0].strip()


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
        *,
        organization_repo: OrganizationRepository,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._document_repo = document_repo
        self._link_repo = link_repo
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

    def create_document(
        self,
        *,
        document_code: str,
        title: str,
        document_type: DocumentType | str | None = None,
        classification: DocumentClassification | str | None = None,
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
        principal = self._user_session.principal if self._user_session is not None else None
        document = Document.create(
            organization_id=organization.id,
            document_code=normalized_code,
            title=normalized_title,
            document_type=_coerce_document_type(document_type if document_type is not None else classification),
            storage_kind=_coerce_storage_kind(storage_kind),
            storage_uri=normalized_uri,
            file_name=_default_file_name(normalized_uri, file_name),
            mime_type=_normalize_optional_text(mime_type),
            source_system=_normalize_optional_text(source_system) or "platform",
            uploaded_at=uploaded_at or datetime.now(timezone.utc),
            uploaded_by_user_id=uploaded_by_user_id or (principal.user_id if principal is not None else None),
            effective_date=_normalize_optional_date(effective_date),
            review_date=_normalize_optional_date(review_date),
            confidentiality_level=_normalize_confidentiality(confidentiality_level),
            revision=_normalize_optional_text(revision),
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
            document.mime_type = _normalize_optional_text(mime_type)
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
        if revision is not None:
            document.revision = _normalize_optional_text(revision)
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

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization


__all__ = ["DocumentService"]
