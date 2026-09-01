from __future__ import annotations

from src.core.platform.domain.master_data.documents.events import (
    DocumentCreated,
    DocumentProfileUpdated,
    DocumentStructureCreated,
    DocumentStructureProfileUpdated,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

DOCUMENT_CATEGORY = "document"
DOCUMENT_LIST_SCOPE_CODE = "document_list"
DOCUMENT_STRUCTURE_CATEGORY = "document_structure"
DOCUMENT_STRUCTURE_LIST_SCOPE_CODE = "document_structure_list"


def build_document_list_view_invalidation_handler(channel: ViewInvalidationChannel):
    last_notified_correlation_id: list[str | None] = [None]

    def handle_document_list_event(
        event: DocumentCreated | DocumentProfileUpdated,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id == last_notified_correlation_id[0]:
            return
        last_notified_correlation_id[0] = context.correlation_id
        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(event.tenant_id, event.organization_id),
                category=DOCUMENT_CATEGORY,
                scope_code=DOCUMENT_LIST_SCOPE_CODE,
                entity_type="document",
                entity_id=None,
            )
        )

    return handle_document_list_event


def build_document_structure_list_view_invalidation_handler(channel: ViewInvalidationChannel):
    last_notified_correlation_id: list[str | None] = [None]

    def handle_document_structure_list_event(
        event: DocumentStructureCreated | DocumentStructureProfileUpdated,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id == last_notified_correlation_id[0]:
            return
        last_notified_correlation_id[0] = context.correlation_id
        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(event.tenant_id, event.organization_id),
                category=DOCUMENT_STRUCTURE_CATEGORY,
                scope_code=DOCUMENT_STRUCTURE_LIST_SCOPE_CODE,
                entity_type="document_structure",
                entity_id=None,
            )
        )

    return handle_document_structure_list_event


__all__ = [
    "build_document_list_view_invalidation_handler",
    "build_document_structure_list_view_invalidation_handler",
    "DOCUMENT_CATEGORY",
    "DOCUMENT_LIST_SCOPE_CODE",
    "DOCUMENT_STRUCTURE_CATEGORY",
    "DOCUMENT_STRUCTURE_LIST_SCOPE_CODE",
]
