from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast

from sqlalchemy.exc import IntegrityError

import src.core.platform.application.master_data.documents.mappers.document as response_mapper
from src.core.platform.application.master_data.documents.document_access import (
    DOCUMENT_MANAGE_PERMISSION,
    is_document_visible,
)
from src.core.platform.application.master_data.documents.document_context import (
    active_organization,
    require_document_in_context,
    resolve_structure_for_context,
)
from src.core.platform.application.master_data.documents.dto.commands.documents import (
    DocumentCreateCommand,
    DocumentUpdateCommand,
)
from src.core.platform.application.master_data.documents.dto.commands.links import (
    DocumentLinkCreateCommand,
)
from src.core.platform.application.master_data.documents.dto.responses.document import (
    DocumentDto,
    DocumentLinkDto,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.port.master_data.documents.document_access_policy import (
    DocumentAccessPolicy,
)
from src.core.platform.contract.repositories.master_data.documents.contracts import (
    DocumentLinkRepository,
)
from src.core.platform.domain.master_data.documents import (
    Document,
    DocumentLink,
    DocumentStorageKind,
    DocumentType,
)
from src.core.platform.domain.master_data.documents.classification import (
    parse_document_classification,
)
from src.core.platform.domain.master_data.documents.events import (
    DocumentCreated,
    DocumentProfileUpdated,
    DocumentReferenceLinked,
    DocumentReferenceUnlinked,
)
from src.core.platform.domain.master_data.documents.support import (
    default_file_name as _default_file_name,
)
from src.core.platform.domain.master_data.documents.support import (
    infer_mime_type as _infer_mime_type,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry

if TYPE_CHECKING:
    from src.core.platform.domain.master_data.org import Organization



def _event_tenant_id(organization: Organization) -> str:
    # Active-context organizations are tenant-scoped; the value is passed to
    # the domain events unchanged.
    return cast(str, organization.tenant_id)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.uow.master_data.document_unit_of_work import (
    DocumentUnitOfWorkFactory,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock


def _new_context(*, causation_id: str | None = None) -> DomainEventContext:
    return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


class DocumentCommandHandler:
    """Document and document-link writes in the active organization, each in one
    Document UoW with audit, activity and domain events."""

    def __init__(
        self,
        *,
        uow_factory: DocumentUnitOfWorkFactory,
        clock: Clock,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
        access_policy: DocumentAccessPolicy,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._access_policy = access_policy

    def create_document(self, command: DocumentCreateCommand) -> DocumentDto:
        require_permission(self._user_session, DOCUMENT_MANAGE_PERMISSION, operation_label="create document")
        organization = active_organization(self._tenant_context_service)
        tenant_id = _event_tenant_id(organization)
        principal = self._user_session.principal if self._user_session is not None else None
        with self._uow_factory.create(context=_new_context()) as uow:
            structure = resolve_structure_for_context(
                command.document_structure_id, organization=organization, structure_repo=uow.structures
            )
            document = Document.create(
                organization_id=organization.id,
                document_code=command.document_code,
                title=command.title,
                document_type=command.document_type,
                document_structure_id=structure.id if structure is not None else None,
                storage_kind=command.storage_kind,
                storage_uri=command.storage_uri,
                file_name=command.file_name,
                mime_type=command.mime_type,
                source_system=command.source_system,
                uploaded_at=command.uploaded_at,
                uploaded_by_user_id=command.uploaded_by_user_id or (principal.user_id if principal is not None else None),
                effective_date=command.effective_date,
                review_date=command.review_date,
                confidentiality_level=parse_document_classification(command.confidentiality_level).value,
                business_version_label=command.business_version_label,
                is_current=command.is_current,
                notes=command.notes,
                is_active=command.is_active,
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
                    organization_id=organization.id,
                    category="MASTER_DATA",
                    severity="low",
                    after_data={"document_code": document.document_code, "title": document.title},
                    metadata={"action": "document.create"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="document.create",
                    entity_type="document",
                    entity_id=document.id,
                    module="platform",
                    organization_id=organization.id,
                    message=f"Document added — {document.title}",
                    icon="documents",
                    commit=False,
                )
                uow.record_event(
                    DocumentCreated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        document_id=document.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError("Document code already exists in the active organization.", code="DOCUMENT_CODE_EXISTS") from exc
        return response_mapper.serialize_document(document)

    def update_document(self, command: DocumentUpdateCommand) -> DocumentDto:
        require_permission(self._user_session, DOCUMENT_MANAGE_PERMISSION, operation_label="update document")
        organization = active_organization(self._tenant_context_service)
        tenant_id = _event_tenant_id(organization)
        with self._uow_factory.create(context=_new_context()) as uow:
            document = uow.documents.get(command.document_id)
            if document is None or document.organization_id != organization.id:
                raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")
            self._require_visible(document, uow.links)
            if command.expected_version is not None and document.version != command.expected_version:
                raise ConcurrencyError("Document changed since you opened it. Refresh and try again.", code="STALE_WRITE")
            next_structure_id = document.document_structure_id
            if command.document_structure_id is not None:
                structure = resolve_structure_for_context(
                    command.document_structure_id, organization=organization, structure_repo=uow.structures
                )
                next_structure_id = structure.id if structure is not None else None
            updated = replace(
                document,
                document_code=document.document_code if command.document_code is None else command.document_code,
                title=document.title if command.title is None else command.title,
                # Raw document type / storage kind inputs are coerced by the fields'
                # "before" validators.
                document_type=cast(
                    DocumentType,
                    command.document_type if command.document_type is not None else document.document_type,
                ),
                document_structure_id=next_structure_id,
                storage_kind=cast(
                    DocumentStorageKind,
                    document.storage_kind if command.storage_kind is None else command.storage_kind,
                ),
                storage_uri=command.storage_uri if command.storage_uri is not None else document.storage_uri,
                file_name=document.file_name if command.file_name is None else command.file_name,
                mime_type=document.mime_type if command.mime_type is None else command.mime_type,
                source_system=document.source_system if command.source_system is None else command.source_system,
                uploaded_at=document.uploaded_at if command.uploaded_at is None else command.uploaded_at,
                uploaded_by_user_id=(
                    document.uploaded_by_user_id
                    if command.uploaded_by_user_id is None
                    else command.uploaded_by_user_id
                ),
                effective_date=document.effective_date if command.effective_date is None else command.effective_date,
                review_date=document.review_date if command.review_date is None else command.review_date,
                confidentiality_level=(
                    document.confidentiality_level
                    if command.confidentiality_level is None
                    else parse_document_classification(command.confidentiality_level).value
                ),
                business_version_label=(
                    command.business_version_label if command.business_version_label is not None else document.business_version_label
                ),
                is_current=document.is_current if command.is_current is None else command.is_current,
                notes=document.notes if command.notes is None else command.notes,
                is_active=document.is_active if command.is_active is None else command.is_active,
            )
            if command.file_name is not None:
                updated.file_name = _default_file_name(updated.storage_uri, command.file_name)
            if (
                command.mime_type is not None or command.storage_uri is not None or command.file_name is not None
            ) and not updated.mime_type:
                updated.mime_type = _infer_mime_type(updated.file_name or updated.storage_uri)
            other_fields_changed = (
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
            )
            active_state_changed = updated.is_active != document.is_active
            profile_changed = other_fields_changed or active_state_changed
            if not profile_changed:
                return response_mapper.serialize_document(document)
            if command.document_code is not None:
                existing = uow.documents.get_by_code(organization.id, updated.document_code)
                if existing is not None and existing.id != document.id:
                    raise ValidationError("Document code already exists in the active organization.", code="DOCUMENT_CODE_EXISTS")
            try:
                uow.documents.update(updated)
                # A pure active-state transition (no other field changed) gets its
                # own distinct action so the curated Organization Activity feed can
                # tell "removed" (deactivated) apart from an ordinary profile edit.
                if active_state_changed and not other_fields_changed:
                    document_audit_action = "document.activate" if updated.is_active else "document.deactivate"
                else:
                    document_audit_action = "document.update"
                # Ordinary master-data lifecycle -- business timeline (Activity)
                # only, for every update including active-state transitions, no
                # compliance/security significance.
                record_activity(
                    uow,
                    action=document_audit_action,
                    entity_type="document",
                    entity_id=updated.id,
                    module="platform",
                    organization_id=organization.id,
                    message=(
                        f"Document removed — {updated.title}"
                        if document_audit_action == "document.deactivate"
                        else f"Document restored — {updated.title}"
                        if document_audit_action == "document.activate"
                        else f"Document updated — {updated.title}"
                    ),
                    icon="documents",
                    type="warning" if document_audit_action == "document.deactivate" else "info",
                    commit=False,
                )
                uow.record_event(
                    DocumentProfileUpdated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        document_id=updated.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError("Document code already exists in the active organization.", code="DOCUMENT_CODE_EXISTS") from exc
        return response_mapper.serialize_document(updated)

    def add_link(self, command: DocumentLinkCreateCommand) -> DocumentLinkDto:
        require_permission(self._user_session, DOCUMENT_MANAGE_PERMISSION, operation_label="link document")
        organization = active_organization(self._tenant_context_service)
        tenant_id = _event_tenant_id(organization)
        with self._uow_factory.create(context=_new_context()) as uow:
            document = require_document_in_context(command.document_id, organization=organization, document_repo=uow.documents)
            self._require_visible(document, uow.links)
            link = DocumentLink.create(
                organization_id=document.organization_id,
                document_id=document.id,
                module_code=command.module_code,
                entity_type=command.entity_type,
                entity_id=command.entity_id,
                link_role=command.link_role,
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
                    organization_id=organization.id,
                    category="MASTER_DATA",
                    severity="low",
                    after_data={
                        "module_code": link.module_code,
                        "entity_type": link.entity_type,
                        "entity_id": link.entity_id,
                    },
                    metadata={"action": "document.link"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="document.link",
                    entity_type="document",
                    entity_id=document.id,
                    module="platform",
                    organization_id=organization.id,
                    message=f"Document linked — {document.title} to {link.entity_type}",
                    icon="documents",
                    details={
                        "module_code": link.module_code,
                        "entity_type": link.entity_type,
                        "entity_id": link.entity_id,
                        "link_role": link.link_role,
                    },
                    commit=False,
                )
                uow.record_event(
                    DocumentReferenceLinked(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        document_id=document.id,
                        module_code=link.module_code,
                        entity_type=link.entity_type,
                        entity_id=link.entity_id,
                        link_role=link.link_role,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError("This document link already exists.", code="DOCUMENT_LINK_EXISTS") from exc
        return response_mapper.serialize_document_link(link)

    def remove_link(self, link_id: str) -> None:
        require_permission(self._user_session, DOCUMENT_MANAGE_PERMISSION, operation_label="unlink document")
        organization = active_organization(self._tenant_context_service)
        tenant_id = _event_tenant_id(organization)
        with self._uow_factory.create(context=_new_context()) as uow:
            link = uow.links.get(link_id)
            if link is None:
                raise NotFoundError("Document link not found.", code="DOCUMENT_LINK_NOT_FOUND")
            document = require_document_in_context(link.document_id, organization=organization, document_repo=uow.documents)
            self._require_visible(document, uow.links)
            uow.links.delete(link.id)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="document",
                entity_id=document.id,
                module="platform",
                organization_id=organization.id,
                category="MASTER_DATA",
                severity="low",
                before_data={
                    "module_code": link.module_code,
                    "entity_type": link.entity_type,
                    "entity_id": link.entity_id,
                },
                metadata={"action": "document.unlink"},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action="document.unlink",
                entity_type="document",
                entity_id=document.id,
                module="platform",
                organization_id=organization.id,
                message=f"Document unlinked — {document.title} from {link.entity_type}",
                icon="documents",
                details={
                    "module_code": link.module_code,
                    "entity_type": link.entity_type,
                    "entity_id": link.entity_id,
                    "link_role": link.link_role,
                },
                commit=False,
            )
            uow.record_event(
                DocumentReferenceUnlinked(
                    tenant_id=tenant_id,
                    organization_id=organization.id,
                    document_id=document.id,
                    module_code=link.module_code,
                    entity_type=link.entity_type,
                    entity_id=link.entity_id,
                    link_role=link.link_role,
                    occurred_at=self._clock.now(),
                )
            )
            uow.commit()

    def _require_visible(self, document: Document, link_repo: DocumentLinkRepository) -> None:
        """Managing a document never extends to documents the actor cannot see; a hidden
        document is reported exactly like a missing one."""
        if not is_document_visible(document, self._access_policy.visibility(), link_repo):
            raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")


__all__ = ["DocumentCommandHandler"]
