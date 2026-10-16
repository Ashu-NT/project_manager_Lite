from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast

from sqlalchemy.exc import IntegrityError

import src.core.platform.application.master_data.documents.mappers.document as response_mapper
from src.core.platform.application.master_data.documents.document_access import (
    DOCUMENT_STRUCTURE_MANAGE_PERMISSION,
)
from src.core.platform.application.master_data.documents.document_context import (
    active_organization,
    resolve_structure_for_context,
)
from src.core.platform.application.master_data.documents.dto.commands.structures import (
    DocumentStructureCreateCommand,
    DocumentStructureUpdateCommand,
)
from src.core.platform.application.master_data.documents.dto.responses.document import (
    DocumentStructureDto,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.domain.master_data.documents import (
    DocumentStructure,
    DocumentType,
)
from src.core.platform.domain.master_data.documents.events import (
    DocumentStructureCreated,
    DocumentStructureProfileUpdated,
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


class DocumentStructureCommandHandler:
    """Document structure (taxonomy) writes in the active organization."""

    def __init__(
        self,
        *,
        uow_factory: DocumentUnitOfWorkFactory,
        clock: Clock,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def create_document_structure(self, command: DocumentStructureCreateCommand) -> DocumentStructureDto:
        require_permission(self._user_session, DOCUMENT_STRUCTURE_MANAGE_PERMISSION, operation_label="create document structure")
        organization = active_organization(self._tenant_context_service)
        tenant_id = _event_tenant_id(organization)
        with self._uow_factory.create(context=_new_context()) as uow:
            parent = resolve_structure_for_context(
                command.parent_structure_id, organization=organization, structure_repo=uow.structures
            )
            structure = DocumentStructure.create(
                organization_id=organization.id,
                structure_code=command.structure_code,
                name=command.name,
                description=command.description,
                parent_structure_id=parent.id if parent is not None else None,
                object_scope=command.object_scope,
                default_document_type=command.default_document_type,
                sort_order=command.sort_order,
                is_active=command.is_active,
                notes=command.notes,
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
                    organization_id=organization.id,
                    category="MASTER_DATA",
                    severity="low",
                    after_data={"structure_code": structure.structure_code, "name": structure.name},
                    metadata={"action": "document_structure.create"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="document_structure.create",
                    entity_type="document_structure",
                    entity_id=structure.id,
                    module="platform",
                    organization_id=organization.id,
                    message=f"Document structure created — {structure.structure_code}",
                    icon="document",
                    commit=False,
                )
                uow.record_event(
                    DocumentStructureCreated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        structure_id=structure.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Document structure code already exists in the active organization.",
                    code="DOCUMENT_STRUCTURE_CODE_EXISTS",
                ) from exc
        return response_mapper.serialize_document_structure(structure)

    def update_document_structure(self, command: DocumentStructureUpdateCommand) -> DocumentStructureDto:
        require_permission(self._user_session, DOCUMENT_STRUCTURE_MANAGE_PERMISSION, operation_label="update document structure")
        organization = active_organization(self._tenant_context_service)
        tenant_id = _event_tenant_id(organization)
        with self._uow_factory.create(context=_new_context()) as uow:
            structure = uow.structures.get(command.structure_id)
            if structure is None or structure.organization_id != organization.id:
                raise NotFoundError(
                    "Document structure not found in the active organization.",
                    code="DOCUMENT_STRUCTURE_NOT_FOUND",
                )
            if command.expected_version is not None and structure.version != command.expected_version:
                raise ConcurrencyError(
                    "Document structure changed since you opened it. Refresh and try again.",
                    code="STALE_WRITE",
                )
            next_parent_structure_id = structure.parent_structure_id
            if command.parent_structure_id is not None:
                parent = resolve_structure_for_context(
                    command.parent_structure_id, organization=organization, structure_repo=uow.structures
                )
                if parent is not None and parent.id == structure.id:
                    raise ValidationError(
                        "A document structure cannot be its own parent.", code="DOCUMENT_STRUCTURE_PARENT_INVALID"
                    )
                next_parent_structure_id = parent.id if parent is not None else None
            updated = replace(
                structure,
                structure_code=structure.structure_code if command.structure_code is None else command.structure_code,
                name=structure.name if command.name is None else command.name,
                description=structure.description if command.description is None else command.description,
                parent_structure_id=next_parent_structure_id,
                object_scope=structure.object_scope if command.object_scope is None else command.object_scope,
                # Raw input is coerced/validated by the field's "before" validator.
                default_document_type=cast(
                    DocumentType,
                    structure.default_document_type
                    if command.default_document_type is None
                    else command.default_document_type,
                ),
                sort_order=structure.sort_order if command.sort_order is None else command.sort_order,
                is_active=structure.is_active if command.is_active is None else command.is_active,
                notes=structure.notes if command.notes is None else command.notes,
            )
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
                return response_mapper.serialize_document_structure(structure)
            if command.structure_code is not None:
                existing = uow.structures.get_by_code(organization.id, updated.structure_code)
                if existing is not None and existing.id != structure.id:
                    raise ValidationError(
                        "Document structure code already exists in the active organization.",
                        code="DOCUMENT_STRUCTURE_CODE_EXISTS",
                    )
            try:
                uow.structures.update(updated)
                record_activity(
                    uow,
                    action="document_structure.update",
                    entity_type="document_structure",
                    entity_id=updated.id,
                    module="platform",
                    organization_id=organization.id,
                    message=f"Document structure updated — {updated.structure_code}",
                    icon="document",
                    commit=False,
                )
                uow.record_event(
                    DocumentStructureProfileUpdated(
                        tenant_id=tenant_id,
                        organization_id=organization.id,
                        structure_id=updated.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Document structure code already exists in the active organization.",
                    code="DOCUMENT_STRUCTURE_CODE_EXISTS",
                ) from exc
        return response_mapper.serialize_document_structure(updated)


__all__ = ["DocumentStructureCommandHandler"]
