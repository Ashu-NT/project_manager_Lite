from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository
from core.platform.org.domain import Organization
from core.platform.documents.domain import Document, DocumentLink, DocumentType
from core.platform.documents.interfaces import DocumentLinkRepository, DocumentRepository
from core.platform.documents.support import (
    coerce_document_type,
    infer_file_name,
    infer_mime_type,
    infer_storage_kind,
    infer_title,
    normalize_entity_label,
    normalize_module_code,
    normalize_optional_text,
)
from core.platform.notifications.domain_events import domain_events


def _build_document_code(*, module_code: str, entity_type: str) -> str:
    prefix = f"{module_code}-{entity_type}".replace("_", "-").upper()
    return f"{prefix}-{uuid4().hex[:12].upper()}"


class DocumentIntegrationService:
    """Shared document plumbing for business modules after module-level auth has passed."""

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
        source_system: str = "",
        link_role: str = "attachment",
        uploaded_by_user_id: str | None = None,
    ) -> list[Document]:
        require_permission(self._user_session, required_permission, operation_label=operation_label)
        tokens = [normalize_optional_text(item) for item in (attachments or []) if normalize_optional_text(item)]
        if not tokens:
            return []
        organization = self._active_organization()
        normalized_module = normalize_module_code(module_code)
        normalized_entity_type = normalize_entity_label(
            entity_type,
            code="DOCUMENT_ENTITY_TYPE_REQUIRED",
            label="Entity type",
        )
        normalized_entity_id = normalize_entity_label(
            entity_id,
            code="DOCUMENT_ENTITY_ID_REQUIRED",
            label="Entity id",
        )
        normalized_role = normalize_optional_text(link_role)
        resolved_type = coerce_document_type(document_type)
        principal = self._user_session.principal if self._user_session is not None else None
        uploader = uploaded_by_user_id or getattr(principal, "user_id", None)
        created: list[Document] = []
        try:
            for token in tokens:
                document = Document.create(
                    organization_id=organization.id,
                    document_code=_build_document_code(
                        module_code=normalized_module,
                        entity_type=normalized_entity_type,
                    ),
                    title=infer_title(token),
                    document_type=resolved_type,
                    storage_kind=infer_storage_kind(token),
                    storage_uri=token,
                    file_name=infer_file_name(token),
                    mime_type=infer_mime_type(token),
                    source_system=normalize_optional_text(source_system) or normalized_module,
                    uploaded_at=datetime.now(timezone.utc),
                    uploaded_by_user_id=uploader,
                )
                self._document_repo.add(document)
                self._session.flush()
                self._link_repo.add(
                    DocumentLink.create(
                        organization_id=organization.id,
                        document_id=document.id,
                        module_code=normalized_module,
                        entity_type=normalized_entity_type,
                        entity_id=normalized_entity_id,
                        link_role=normalized_role,
                    )
                )
                created.append(document)
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            raise
        except Exception:
            self._session.rollback()
            raise
        for document in created:
            record_audit(
                self,
                action="document.linked_attachment.create",
                entity_type="document",
                entity_id=document.id,
                details={
                    "module_code": normalized_module,
                    "entity_type": normalized_entity_type,
                    "entity_id": normalized_entity_id,
                    "link_role": normalized_role,
                    "storage_kind": document.storage_kind.value,
                    "storage_uri": document.storage_uri,
                },
            )
            domain_events.documents_changed.emit(document.id)
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
            normalize_module_code(module_code),
            normalize_entity_label(entity_type, code="DOCUMENT_ENTITY_TYPE_REQUIRED", label="Entity type"),
            normalize_entity_label(entity_id, code="DOCUMENT_ENTITY_ID_REQUIRED", label="Entity id"),
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
        document = self._document_repo.get(document_id)
        if document is None or document.organization_id != organization.id:
            raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")
        if not document.is_active:
            raise ValidationError("Document must be active before it can be linked.", code="DOCUMENT_INACTIVE")
        normalized_module = normalize_module_code(module_code)
        normalized_entity_type = normalize_entity_label(
            entity_type,
            code="DOCUMENT_ENTITY_TYPE_REQUIRED",
            label="Entity type",
        )
        normalized_entity_id = normalize_entity_label(
            entity_id,
            code="DOCUMENT_ENTITY_ID_REQUIRED",
            label="Entity id",
        )
        normalized_role = normalize_optional_text(link_role)
        existing = self._link_repo.find_existing(
            document_id=document.id,
            module_code=normalized_module,
            entity_type=normalized_entity_type,
            entity_id=normalized_entity_id,
            link_role=normalized_role,
        )
        if existing is not None:
            raise ValidationError("Document link already exists.", code="DOCUMENT_LINK_EXISTS")
        link = DocumentLink.create(
            organization_id=organization.id,
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
            raise ValidationError("Document link already exists.", code="DOCUMENT_LINK_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="document.link_existing",
            entity_type="document",
            entity_id=document.id,
            details={
                "module_code": normalized_module,
                "entity_type": normalized_entity_type,
                "entity_id": normalized_entity_id,
                "link_role": normalized_role,
            },
        )
        domain_events.documents_changed.emit(document.id)
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
        document = self._document_repo.get(document_id)
        if document is None or document.organization_id != organization.id:
            raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")
        normalized_module = normalize_module_code(module_code)
        normalized_entity_type = normalize_entity_label(
            entity_type,
            code="DOCUMENT_ENTITY_TYPE_REQUIRED",
            label="Entity type",
        )
        normalized_entity_id = normalize_entity_label(
            entity_id,
            code="DOCUMENT_ENTITY_ID_REQUIRED",
            label="Entity id",
        )
        normalized_role = normalize_optional_text(link_role)
        existing = self._link_repo.find_existing(
            document_id=document.id,
            module_code=normalized_module,
            entity_type=normalized_entity_type,
            entity_id=normalized_entity_id,
            link_role=normalized_role,
        )
        if existing is None:
            raise NotFoundError("Document link not found.", code="DOCUMENT_LINK_NOT_FOUND")
        try:
            self._link_repo.delete(existing.id)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="document.unlink_existing",
            entity_type="document",
            entity_id=document.id,
            details={
                "module_code": normalized_module,
                "entity_type": normalized_entity_type,
                "entity_id": normalized_entity_id,
                "link_role": normalized_role,
            },
        )
        domain_events.documents_changed.emit(document.id)

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization


__all__ = ["DocumentIntegrationService"]
