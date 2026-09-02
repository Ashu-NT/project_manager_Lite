from __future__ import annotations

from src.core.platform.domain.master_data.documents.events import (
    DocumentCreated,
    DocumentProfileUpdated,
    DocumentReferenceLinked,
    DocumentReferenceUnlinked,
    DocumentStructureCreated,
    DocumentStructureProfileUpdated,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

DOCUMENT_CATEGORY = "document"
DOCUMENT_LIST_SCOPE_CODE = "document_list"
DOCUMENT_STRUCTURE_CATEGORY = "document_structure"
DOCUMENT_STRUCTURE_LIST_SCOPE_CODE = "document_structure_list"
DOCUMENT_LINKS_SCOPE_CODE = "document_links"
DOCUMENT_LINK_OWNER_ENTITY_TYPE = "document"
DOCUMENT_LINK_OWNER_MODULE_CODE = "platform"


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


def build_document_links_view_invalidation_handler(channel: ViewInvalidationChannel):
    """One `document_links` hint per distinct link *target* touched in a transaction, in each
    of two shapes, each targeted via a `ResourceScope` (P16D-FIX) rather than a bare
    `OrganizationScope` + an ad hoc field on the hint itself:

    - forward (module_code, entity_type, entity_id): "this business entity's linked documents
      changed" -- for Catalog/Reservations/Procurement's own linked-document projections.
    - reverse ("platform", "document", document_id): "this document's own link set changed" --
      for Admin's per-document link panel. Module code is `"platform"` because Document is a
      Platform-owned resource, not owned by any business module -- the same convention already
      used by `record_audit_entry(..., module="platform", ...)` elsewhere in this codebase.

    Deduplicated independently per shape, keyed by (transaction correlation_id, target scope
    identity) -- not correlation_id alone, since one transaction (e.g.
    `register_entity_attachments`) can legitimately touch multiple distinct documents while
    targeting one shared business entity. Both dedup sets are transaction-scoped: cleared the
    moment a new correlation_id arrives, so neither ever grows across unrelated transactions."""

    current_correlation_id: list[str | None] = [None]
    notified_entity_targets: set[tuple[str, str, str, str, str]] = set()
    notified_document_targets: set[tuple[str, str, str]] = set()

    def handle_document_links_event(
        event: DocumentReferenceLinked | DocumentReferenceUnlinked,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_entity_targets.clear()
            notified_document_targets.clear()

        entity_target = (
            event.tenant_id,
            event.organization_id,
            event.module_code,
            event.entity_type,
            event.entity_id,
        )
        if entity_target not in notified_entity_targets:
            notified_entity_targets.add(entity_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=ResourceScope(
                        tenant_id=event.tenant_id,
                        organization_id=event.organization_id,
                        module_code=event.module_code,
                        entity_type=event.entity_type,
                        entity_id=event.entity_id,
                    ),
                    category=DOCUMENT_CATEGORY,
                    scope_code=DOCUMENT_LINKS_SCOPE_CODE,
                    entity_type=event.entity_type,
                    entity_id=event.entity_id,
                )
            )

        document_target = (event.tenant_id, event.organization_id, event.document_id)
        if document_target not in notified_document_targets:
            notified_document_targets.add(document_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=ResourceScope(
                        tenant_id=event.tenant_id,
                        organization_id=event.organization_id,
                        module_code=DOCUMENT_LINK_OWNER_MODULE_CODE,
                        entity_type=DOCUMENT_LINK_OWNER_ENTITY_TYPE,
                        entity_id=event.document_id,
                    ),
                    category=DOCUMENT_CATEGORY,
                    scope_code=DOCUMENT_LINKS_SCOPE_CODE,
                    entity_type=DOCUMENT_LINK_OWNER_ENTITY_TYPE,
                    entity_id=event.document_id,
                )
            )

    return handle_document_links_event


__all__ = [
    "build_document_list_view_invalidation_handler",
    "build_document_structure_list_view_invalidation_handler",
    "build_document_links_view_invalidation_handler",
    "DOCUMENT_CATEGORY",
    "DOCUMENT_LIST_SCOPE_CODE",
    "DOCUMENT_STRUCTURE_CATEGORY",
    "DOCUMENT_STRUCTURE_LIST_SCOPE_CODE",
    "DOCUMENT_LINKS_SCOPE_CODE",
    "DOCUMENT_LINK_OWNER_ENTITY_TYPE",
    "DOCUMENT_LINK_OWNER_MODULE_CODE",
]
