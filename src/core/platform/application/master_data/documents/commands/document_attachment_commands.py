from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.master_data.documents.document_access import (
    attachment_visibility,
    is_document_visible,
)
from src.core.platform.application.master_data.documents.document_context import (
    active_organization,
    resolve_structure_for_context,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.port.master_data.documents.document_access_policy import (
    DocumentAccessPolicy,
    DocumentVisibility,
)
from src.core.platform.contract.repositories.master_data.documents.contracts import (
    DocumentStructureRepository,
)
from src.core.platform.contract.uow.master_data.document_unit_of_work import (
    DocumentUnitOfWorkFactory,
)
from src.core.platform.domain.master_data.documents import (
    Document,
    DocumentLink,
    DocumentType,
)
from src.core.platform.domain.master_data.documents.classification import (
    DocumentClassification,
    parse_document_classification,
)
from src.core.platform.domain.master_data.documents.document_link import (
    normalize_document_entity_id,
    normalize_document_entity_type,
    normalize_document_link_role,
    normalize_document_module_code,
)
from src.core.platform.domain.master_data.documents.events import (
    DocumentCreated,
    DocumentReferenceLinked,
    DocumentReferenceUnlinked,
)
from src.core.platform.domain.master_data.documents.support import (
    coerce_document_type,
    infer_file_name,
    infer_mime_type,
    infer_storage_kind,
    infer_title,
    normalize_optional_text,
)
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock


def _event_tenant_id(organization: Organization) -> str:
    # Active-context organizations are tenant-scoped; the value is passed to
    # the domain events unchanged.
    return cast(str, organization.tenant_id)


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
    confidentiality_level: DocumentClassification | str | None = None,
) -> list[Document]:
    """`confidentiality_level` lets the module that owns the entity file its attachments
    as RESTRICTED in the same unit of work that links them, so they are never orphaned
    outside every grant."""

    tokens = [normalize_optional_text(item) for item in (attachments or []) if normalize_optional_text(item)]
    if not tokens:
        return []
    normalized_module = normalize_document_module_code(module_code)
    normalized_entity_type = normalize_document_entity_type(entity_type)
    normalized_entity_id = normalize_document_entity_id(entity_id)
    normalized_role = normalize_document_link_role(link_role)
    resolved_type = coerce_document_type(document_type)
    classification = parse_document_classification(confidentiality_level)
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
            confidentiality_level=classification.value,
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
            module=normalized_module,
            organization_id=organization.id,
            category="MASTER_DATA",
            severity="low",
            after_data={
                "entity_type": normalized_entity_type,
                "entity_id": normalized_entity_id,
                "link_role": normalized_role,
                "storage_kind": document.storage_kind.value,
            },
            metadata={"action": "document.linked_attachment.create"},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            uow,
            action="document.linked_attachment.create",
            entity_type="document",
            entity_id=document.id,
            module=normalized_module,
            organization_id=organization.id,
            parent_entity_id=normalized_entity_id,
            details={
                "entity_type": normalized_entity_type,
                "entity_id": normalized_entity_id,
                "link_role": normalized_role,
                "storage_kind": document.storage_kind.value,
            },
            commit=False,
        )
        uow.record_event(
            DocumentCreated(
                tenant_id=_event_tenant_id(organization),
                organization_id=organization.id,
                document_id=document.id,
                occurred_at=now,
            )
        )
        uow.record_event(
            DocumentReferenceLinked(
                tenant_id=_event_tenant_id(organization),
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
    visibility: DocumentVisibility,
    link_role: str = "reference",
) -> DocumentLink:
    """Transaction-neutral core of `link_existing_document`: never commits, rolls back, or
    publishes -- the caller's UoW owns the transaction. `visibility` is the actor's
    attachment visibility; a document they cannot see is reported as missing."""
    document = uow.documents.get(document_id)
    if (
        document is None
        or document.organization_id != organization.id
        or not is_document_visible(document, visibility, uow.links)
    ):
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
        module=normalized_module,
        organization_id=organization.id,
        category="MASTER_DATA",
        severity="low",
        after_data={
            "entity_type": normalized_entity_type,
            "entity_id": normalized_entity_id,
            "link_role": normalized_role,
        },
        metadata={"action": "document.link_existing"},
        commit=False,
        fail_closed=True,
    )
    record_activity(
        uow,
        action="document.link_existing",
        entity_type="document",
        entity_id=document.id,
        module=normalized_module,
        organization_id=organization.id,
        parent_entity_id=normalized_entity_id,
        details={
            "entity_type": normalized_entity_type,
            "entity_id": normalized_entity_id,
            "link_role": normalized_role,
        },
        commit=False,
    )
    uow.record_event(
        DocumentReferenceLinked(
            tenant_id=_event_tenant_id(organization),
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


def _new_context(*, causation_id: str | None = None) -> DomainEventContext:
    return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


class DocumentAttachmentCommandHandler:
    """Entity attachment writes on behalf of another module (e.g. PM tasks): register
    attachments and link or unlink existing documents, under the module's own permission."""

    def __init__(
        self,
        *,
        structure_repo: DocumentStructureRepository,
        uow_factory: DocumentUnitOfWorkFactory,
        clock: Clock,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
        access_policy: DocumentAccessPolicy,
    ) -> None:
        self._structure_repo = structure_repo
        self._uow_factory = uow_factory
        self._clock = clock
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._access_policy = access_policy

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
        confidentiality_level: DocumentClassification | str | None = None,
    ) -> list[Document]:
        require_permission(self._user_session, required_permission, operation_label=operation_label)
        tokens = [normalize_optional_text(item) for item in (attachments or []) if normalize_optional_text(item)]
        if not tokens:
            return []
        organization = active_organization(self._tenant_context_service)
        principal = self._user_session.principal if self._user_session is not None else None
        uploader = uploaded_by_user_id or getattr(principal, "user_id", None)
        with self._uow_factory.create(context=_new_context()) as uow:
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
                confidentiality_level=confidentiality_level,
            )
            uow.commit()
        return created

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
        organization = active_organization(self._tenant_context_service)
        with self._uow_factory.create(context=_new_context()) as uow:
            try:
                link = link_existing_document_in_uow(
                    uow=uow,
                    organization=organization,
                    module_code=module_code,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    document_id=document_id,
                    clock=self._clock,
                    visibility=attachment_visibility(self._access_policy.visibility()),
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
        organization = active_organization(self._tenant_context_service)
        with self._uow_factory.create(context=_new_context()) as uow:
            document = uow.documents.get(document_id)
            if (
                document is None
                or document.organization_id != organization.id
                or not is_document_visible(
                    document, attachment_visibility(self._access_policy.visibility()), uow.links
                )
            ):
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
            record_activity(
                uow,
                action="document.unlink_existing",
                entity_type="document",
                entity_id=document.id,
                module=normalized_module,
                organization_id=organization.id,
                parent_entity_id=normalized_entity_id,
                details={
                    "entity_type": normalized_entity_type,
                    "entity_id": normalized_entity_id,
                    "link_role": normalized_role,
                },
                commit=False,
            )
            uow.record_event(
                DocumentReferenceUnlinked(
                    tenant_id=_event_tenant_id(organization),
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


__all__ = ["DocumentAttachmentCommandHandler"]
