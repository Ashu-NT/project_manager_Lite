from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from src.core.shared.audit import record_audit_entry
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.shared.events.domain_events import domain_events
from src.core.platform.domain.master_data.documents import (
    Document,
    DocumentClassification,
    DocumentLink,
    DocumentStorageKind,
    DocumentStructure,
    DocumentType,
)
from src.core.platform.domain.master_data.documents.events import (
    DocumentCreated,
    DocumentProfileUpdated,
    DocumentStructureCreated,
    DocumentStructureProfileUpdated,
)
from src.core.platform.domain.master_data.documents.support import (
    default_file_name as _default_file_name,
    infer_mime_type as _infer_mime_type,
)

from .document_context import active_organization, require_document_in_context, resolve_structure_for_context

if TYPE_CHECKING:
    from .document_service import DocumentService


def create_document_structure(
    service: DocumentService,
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
    require_permission(service._user_session, "settings.manage", operation_label="create document structure")
    organization = active_organization(service)
    tenant_id = organization.tenant_id
    with service._uow_factory.create(context=service._new_context()) as uow:
        parent = resolve_structure_for_context(
            parent_structure_id, organization=organization, structure_repo=uow.structures
        )
        structure = DocumentStructure.create(
            organization_id=organization.id,
            structure_code=structure_code,
            name=name,
            description=description,
            parent_structure_id=parent.id if parent is not None else None,
            object_scope=object_scope,
            default_document_type=default_document_type,
            sort_order=sort_order,
            is_active=is_active,
            notes=notes,
        )
        if uow.structures.get_by_code(organization.id, structure.structure_code) is not None:
            raise ValidationError(
                "Document structure code already exists in the active organization.",
                code="DOCUMENT_STRUCTURE_CODE_EXISTS",
            )
        try:
            uow.structures.add(structure)
            record_audit_entry(
                uow,
                operation="create",
                entity_type="document_structure",
                entity_id=structure.id,
                module="platform",
                severity="low",
                metadata={
                    "action": "document_structure.create",
                    "organization_id": organization.id,
                    "structure_code": structure.structure_code,
                    "object_scope": structure.object_scope,
                    "default_document_type": structure.default_document_type.value,
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                DocumentStructureCreated(
                    tenant_id=tenant_id,
                    organization_id=organization.id,
                    structure_id=structure.id,
                    occurred_at=service._clock.now(),
                )
            )
            uow.commit()
        except IntegrityError as exc:
            raise ValidationError(
                "Document structure code already exists in the active organization.",
                code="DOCUMENT_STRUCTURE_CODE_EXISTS",
            ) from exc
    return structure


def update_document_structure(
    service: DocumentService,
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
    require_permission(service._user_session, "settings.manage", operation_label="update document structure")
    organization = active_organization(service)
    tenant_id = organization.tenant_id
    with service._uow_factory.create(context=service._new_context()) as uow:
        structure = uow.structures.get(structure_id)
        if structure is None or structure.organization_id != organization.id:
            raise NotFoundError(
                "Document structure not found in the active organization.",
                code="DOCUMENT_STRUCTURE_NOT_FOUND",
            )
        if expected_version is not None and structure.version != expected_version:
            raise ConcurrencyError(
                "Document structure changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        next_parent_structure_id = structure.parent_structure_id
        if parent_structure_id is not None:
            parent = resolve_structure_for_context(
                parent_structure_id, organization=organization, structure_repo=uow.structures
            )
            if parent is not None and parent.id == structure.id:
                raise ValidationError(
                    "A document structure cannot be its own parent.", code="DOCUMENT_STRUCTURE_PARENT_INVALID"
                )
            next_parent_structure_id = parent.id if parent is not None else None
        updated = replace(
            structure,
            structure_code=structure.structure_code if structure_code is None else structure_code,
            name=structure.name if name is None else name,
            description=structure.description if description is None else description,
            parent_structure_id=next_parent_structure_id,
            object_scope=structure.object_scope if object_scope is None else object_scope,
            default_document_type=(
                structure.default_document_type
                if default_document_type is None
                else default_document_type
            ),
            sort_order=structure.sort_order if sort_order is None else sort_order,
            is_active=structure.is_active if is_active is None else is_active,
            notes=structure.notes if notes is None else notes,
        )
        # intentional pre-release behavior correction -- update_document_structure
        # previously had no no-op guard at all and always wrote/audited/emitted.
        profile_changed = (
            updated.structure_code != structure.structure_code
            or updated.name != structure.name
            or updated.description != structure.description
            or updated.parent_structure_id != structure.parent_structure_id
            or updated.object_scope != structure.object_scope
            or updated.default_document_type != structure.default_document_type
            or updated.sort_order != structure.sort_order
            or updated.is_active != structure.is_active
            or updated.notes != structure.notes
        )
        if not profile_changed:
            return structure
        if structure_code is not None:
            existing = uow.structures.get_by_code(organization.id, updated.structure_code)
            if existing is not None and existing.id != structure.id:
                raise ValidationError(
                    "Document structure code already exists in the active organization.",
                    code="DOCUMENT_STRUCTURE_CODE_EXISTS",
                )
        try:
            uow.structures.update(updated)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="document_structure",
                entity_id=updated.id,
                module="platform",
                severity="low",
                metadata={
                    "action": "document_structure.update",
                    "organization_id": organization.id,
                    "structure_code": updated.structure_code,
                    "object_scope": updated.object_scope,
                    "default_document_type": updated.default_document_type.value,
                    "is_active": str(updated.is_active),
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                DocumentStructureProfileUpdated(
                    tenant_id=tenant_id,
                    organization_id=organization.id,
                    structure_id=updated.id,
                    occurred_at=service._clock.now(),
                )
            )
            uow.commit()
        except IntegrityError as exc:
            raise ValidationError(
                "Document structure code already exists in the active organization.",
                code="DOCUMENT_STRUCTURE_CODE_EXISTS",
            ) from exc
    return updated


def create_document(
    service: DocumentService,
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
    require_permission(service._user_session, "settings.manage", operation_label="create document")
    organization = active_organization(service)
    tenant_id = organization.tenant_id
    principal = service._user_session.principal if service._user_session is not None else None
    with service._uow_factory.create(context=service._new_context()) as uow:
        structure = resolve_structure_for_context(
            document_structure_id, organization=organization, structure_repo=uow.structures
        )
        document = Document.create(
            organization_id=organization.id,
            document_code=document_code,
            title=title,
            document_type=document_type if document_type is not None else classification,
            document_structure_id=structure.id if structure is not None else None,
            storage_kind=storage_kind,
            storage_uri=storage_uri if storage_uri is not None else storage_ref,
            file_name=file_name,
            mime_type=mime_type,
            source_system=source_system,
            uploaded_at=uploaded_at,
            uploaded_by_user_id=uploaded_by_user_id or (principal.user_id if principal is not None else None),
            effective_date=effective_date,
            review_date=review_date,
            confidentiality_level=confidentiality_level,
            business_version_label=business_version_label,
            revision=revision,
            is_current=is_current,
            notes=notes,
            is_active=is_active,
        )
        if uow.documents.get_by_code(organization.id, document.document_code) is not None:
            raise ValidationError("Document code already exists in the active organization.", code="DOCUMENT_CODE_EXISTS")
        if not document.file_name:
            document.file_name = _default_file_name(document.storage_uri, None)
        if not document.mime_type:
            document.mime_type = _infer_mime_type(document.file_name or document.storage_uri)
        try:
            uow.documents.add(document)
            record_audit_entry(
                uow,
                operation="create",
                entity_type="document",
                entity_id=document.id,
                module="platform",
                severity="low",
                metadata={
                    "action": "document.create",
                    "organization_id": organization.id,
                    "document_code": document.document_code,
                    "title": document.title,
                    "document_type": document.document_type.value,
                    "document_structure_id": document.document_structure_id,
                    "storage_kind": document.storage_kind.value,
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                DocumentCreated(
                    tenant_id=tenant_id,
                    organization_id=organization.id,
                    document_id=document.id,
                    occurred_at=service._clock.now(),
                )
            )
            uow.commit()
        except IntegrityError as exc:
            raise ValidationError("Document code already exists in the active organization.", code="DOCUMENT_CODE_EXISTS") from exc
    return document


def update_document(
    service: DocumentService,
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
    require_permission(service._user_session, "settings.manage", operation_label="update document")
    organization = active_organization(service)
    tenant_id = organization.tenant_id
    with service._uow_factory.create(context=service._new_context()) as uow:
        document = uow.documents.get(document_id)
        if document is None or document.organization_id != organization.id:
            raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")
        if expected_version is not None and document.version != expected_version:
            raise ConcurrencyError("Document changed since you opened it. Refresh and try again.", code="STALE_WRITE")
        next_structure_id = document.document_structure_id
        if document_structure_id is not None:
            structure = resolve_structure_for_context(
                document_structure_id, organization=organization, structure_repo=uow.structures
            )
            next_structure_id = structure.id if structure is not None else None
        updated = replace(
            document,
            document_code=document.document_code if document_code is None else document_code,
            title=document.title if title is None else title,
            document_type=(
                document.document_type
                if document_type is None and classification is None
                else (document_type if document_type is not None else classification)
            ),
            document_structure_id=next_structure_id,
            storage_kind=document.storage_kind if storage_kind is None else storage_kind,
            storage_uri=(
                document.storage_uri
                if storage_uri is None and storage_ref is None
                else (storage_uri if storage_uri is not None else storage_ref)
            ),
            file_name=document.file_name if file_name is None else file_name,
            mime_type=document.mime_type if mime_type is None else mime_type,
            source_system=document.source_system if source_system is None else source_system,
            uploaded_at=document.uploaded_at if uploaded_at is None else uploaded_at,
            uploaded_by_user_id=(
                document.uploaded_by_user_id
                if uploaded_by_user_id is None
                else uploaded_by_user_id
            ),
            effective_date=document.effective_date if effective_date is None else effective_date,
            review_date=document.review_date if review_date is None else review_date,
            confidentiality_level=(
                document.confidentiality_level
                if confidentiality_level is None
                else confidentiality_level
            ),
            business_version_label=(
                document.business_version_label
                if business_version_label is None and revision is None
                else (
                    business_version_label
                    if business_version_label is not None
                    else revision
                )
            ),
            is_current=document.is_current if is_current is None else is_current,
            notes=document.notes if notes is None else notes,
            is_active=document.is_active if is_active is None else is_active,
        )
        if file_name is not None:
            updated.file_name = _default_file_name(updated.storage_uri, file_name)
        if mime_type is not None:
            if not updated.mime_type:
                updated.mime_type = _infer_mime_type(updated.file_name or updated.storage_uri)
        elif storage_uri is not None or storage_ref is not None or file_name is not None:
            if not updated.mime_type:
                updated.mime_type = _infer_mime_type(updated.file_name or updated.storage_uri)
        # P16B: intentional pre-release behavior correction -- update_document previously had
        # no no-op guard at all and always wrote/audited/emitted.
        profile_changed = (
            updated.document_code != document.document_code
            or updated.title != document.title
            or updated.document_type != document.document_type
            or updated.document_structure_id != document.document_structure_id
            or updated.storage_kind != document.storage_kind
            or updated.storage_uri != document.storage_uri
            or updated.file_name != document.file_name
            or updated.mime_type != document.mime_type
            or updated.source_system != document.source_system
            or updated.uploaded_at != document.uploaded_at
            or updated.uploaded_by_user_id != document.uploaded_by_user_id
            or updated.effective_date != document.effective_date
            or updated.review_date != document.review_date
            or updated.confidentiality_level != document.confidentiality_level
            or updated.business_version_label != document.business_version_label
            or updated.is_current != document.is_current
            or updated.notes != document.notes
            or updated.is_active != document.is_active
        )
        if not profile_changed:
            return document
        if document_code is not None:
            existing = uow.documents.get_by_code(organization.id, updated.document_code)
            if existing is not None and existing.id != document.id:
                raise ValidationError("Document code already exists in the active organization.", code="DOCUMENT_CODE_EXISTS")
        try:
            uow.documents.update(updated)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="document",
                entity_id=updated.id,
                module="platform",
                severity="low",
                metadata={
                    "action": "document.update",
                    "organization_id": organization.id,
                    "document_code": updated.document_code,
                    "title": updated.title,
                    "document_type": updated.document_type.value,
                    "document_structure_id": updated.document_structure_id,
                    "storage_kind": updated.storage_kind.value,
                    "is_active": str(updated.is_active),
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                DocumentProfileUpdated(
                    tenant_id=tenant_id,
                    organization_id=organization.id,
                    document_id=updated.id,
                    occurred_at=service._clock.now(),
                )
            )
            uow.commit()
        except IntegrityError as exc:
            raise ValidationError("Document code already exists in the active organization.", code="DOCUMENT_CODE_EXISTS") from exc
    return updated


def add_link(
    service: DocumentService,
    *,
    document_id: str,
    module_code: str,
    entity_type: str,
    entity_id: str,
    link_role: str = "",
) -> DocumentLink:
    require_permission(service._user_session, "settings.manage", operation_label="link document")
    organization = active_organization(service)
    with service._uow_factory.create(context=service._new_context()) as uow:
        document = require_document_in_context(document_id, organization=organization, document_repo=uow.documents)
        link = DocumentLink.create(
            organization_id=document.organization_id,
            document_id=document.id,
            module_code=module_code,
            entity_type=entity_type,
            entity_id=entity_id,
            link_role=link_role,
        )
        existing = uow.links.find_existing(
            document_id=link.document_id,
            module_code=link.module_code,
            entity_type=link.entity_type,
            entity_id=link.entity_id,
            link_role=link.link_role,
        )
        if existing is not None:
            raise ValidationError("This document link already exists.", code="DOCUMENT_LINK_EXISTS")
        try:
            uow.links.add(link)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="document",
                entity_id=document.id,
                module="platform",
                severity="low",
                metadata={
                    "action": "document.link",
                    "module_code": link.module_code,
                    "entity_type": link.entity_type,
                    "entity_id": link.entity_id,
                    "link_role": link.link_role,
                },
                commit=False,
                fail_closed=True,
            )
            uow.commit()
        except IntegrityError as exc:
            raise ValidationError("This document link already exists.", code="DOCUMENT_LINK_EXISTS") from exc
    domain_events.documents_changed.emit(document.id)
    return link


def remove_link(service: DocumentService, link_id: str) -> None:
    require_permission(service._user_session, "settings.manage", operation_label="unlink document")
    organization = active_organization(service)
    with service._uow_factory.create(context=service._new_context()) as uow:
        link = uow.links.get(link_id)
        if link is None:
            raise NotFoundError("Document link not found.", code="DOCUMENT_LINK_NOT_FOUND")
        document = require_document_in_context(link.document_id, organization=organization, document_repo=uow.documents)
        uow.links.delete(link.id)
        record_audit_entry(
            uow,
            operation="delete",
            entity_type="document",
            entity_id=document.id,
            module="platform",
            severity="low",
            metadata={
                "action": "document.unlink",
                "module_code": link.module_code,
                "entity_type": link.entity_type,
                "entity_id": link.entity_id,
                "link_role": link.link_role,
            },
            commit=False,
            fail_closed=True,
        )
        uow.commit()
    domain_events.documents_changed.emit(document.id)


__all__ = [
    "add_link",
    "create_document",
    "create_document_structure",
    "remove_link",
    "update_document",
    "update_document_structure",
]
