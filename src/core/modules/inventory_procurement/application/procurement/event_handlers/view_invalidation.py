from __future__ import annotations

from src.core.modules.inventory_procurement.domain.procurement.purchasing_events import (
    InventoryPurchaseOrderApproved,
    InventoryPurchaseOrderCancelled,
    InventoryPurchaseOrderClosed,
    InventoryPurchaseOrderCreated,
    InventoryPurchaseOrderLineAdded,
    InventoryPurchaseOrderProfileUpdated,
    InventoryPurchaseOrderReceivingAdvanced,
    InventoryPurchaseOrderRejected,
    InventoryPurchaseOrderSent,
    InventoryPurchaseOrderSubmitted,
)
from src.core.modules.inventory_procurement.domain.procurement.requisition_events import (
    InventoryRequisitionApproved,
    InventoryRequisitionCancelled,
    InventoryRequisitionCreated,
    InventoryRequisitionLineAdded,
    InventoryRequisitionProfileUpdated,
    InventoryRequisitionRejected,
    InventoryRequisitionSourcingAdvanced,
    InventoryRequisitionSubmitted,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

PROCUREMENT_CATEGORY = "procurement"
PURCHASE_ORDER_LIST_SCOPE_CODE = "purchase_order_list"
PURCHASE_ORDER_DETAIL_SCOPE_CODE = "purchase_order_detail"
REQUISITION_LIST_SCOPE_CODE = "requisition_list"
REQUISITION_DETAIL_SCOPE_CODE = "requisition_detail"
REQUISITION_PENDING_APPROVAL_SCOPE_CODE = "requisition_pending_approval"
PROCUREMENT_MODULE_CODE = "inventory_procurement"
PURCHASE_ORDER_ENTITY_TYPE = "purchase_order"
REQUISITION_ENTITY_TYPE = "purchase_requisition"

_PurchaseOrderEvent = (
    InventoryPurchaseOrderCreated
    | InventoryPurchaseOrderLineAdded
    | InventoryPurchaseOrderProfileUpdated
    | InventoryPurchaseOrderSubmitted
    | InventoryPurchaseOrderApproved
    | InventoryPurchaseOrderRejected
    | InventoryPurchaseOrderCancelled
    | InventoryPurchaseOrderSent
    | InventoryPurchaseOrderClosed
    | InventoryPurchaseOrderReceivingAdvanced
)

_OrgTarget = tuple[str, str, str]
_DetailTarget = tuple[str, str, str, str, str, str]


def _org_scope_target(scope_code: str, scope: OrganizationScope) -> _OrgTarget:
    return (scope_code, scope.tenant_id, scope.organization_id)


def _detail_scope_target(scope_code: str, scope: ResourceScope) -> _DetailTarget:
    return (
        scope_code,
        scope.tenant_id,
        scope.organization_id,
        scope.module_code,
        scope.entity_type,
        scope.entity_id,
    )


def build_purchase_order_view_invalidation_handler(channel: ViewInvalidationChannel):

    current_correlation_id: list[str | None] = [None]
    notified_org_targets: set[_OrgTarget] = set()
    notified_detail_targets: set[_DetailTarget] = set()

    def handle_purchase_order_event(
        event: _PurchaseOrderEvent,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_org_targets.clear()
            notified_detail_targets.clear()

        org_scope = OrganizationScope(event.tenant_id, event.organization_id)
        org_target = _org_scope_target(PURCHASE_ORDER_LIST_SCOPE_CODE, org_scope)
        if org_target not in notified_org_targets:
            notified_org_targets.add(org_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=org_scope,
                    category=PROCUREMENT_CATEGORY,
                    scope_code=PURCHASE_ORDER_LIST_SCOPE_CODE,
                    entity_type=PURCHASE_ORDER_ENTITY_TYPE,
                    entity_id=event.purchase_order_id,
                )
            )

        detail_scope = ResourceScope(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            module_code=PROCUREMENT_MODULE_CODE,
            entity_type=PURCHASE_ORDER_ENTITY_TYPE,
            entity_id=event.purchase_order_id,
        )
        detail_target = _detail_scope_target(PURCHASE_ORDER_DETAIL_SCOPE_CODE, detail_scope)
        if detail_target not in notified_detail_targets:
            notified_detail_targets.add(detail_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=detail_scope,
                    category=PROCUREMENT_CATEGORY,
                    scope_code=PURCHASE_ORDER_DETAIL_SCOPE_CODE,
                    entity_type=PURCHASE_ORDER_ENTITY_TYPE,
                    entity_id=event.purchase_order_id,
                )
            )

    return handle_purchase_order_event


_RequisitionEvent = (
    InventoryRequisitionCreated
    | InventoryRequisitionLineAdded
    | InventoryRequisitionProfileUpdated
    | InventoryRequisitionSubmitted
    | InventoryRequisitionApproved
    | InventoryRequisitionRejected
    | InventoryRequisitionCancelled
    | InventoryRequisitionSourcingAdvanced
)


def _requisition_event_notifies_list(event: _RequisitionEvent) -> bool:
    return not isinstance(event, InventoryRequisitionLineAdded)


def _requisition_event_notifies_detail(event: _RequisitionEvent) -> bool:
    return not isinstance(event, InventoryRequisitionCreated)


def _requisition_event_notifies_pending_approval(event: _RequisitionEvent) -> bool:
    return isinstance(
        event,
        (
            InventoryRequisitionSubmitted,
            InventoryRequisitionApproved,
            InventoryRequisitionRejected,
            InventoryRequisitionCancelled,
        ),
    )


def build_requisition_view_invalidation_handler(channel: ViewInvalidationChannel):

    current_correlation_id: list[str | None] = [None]
    notified_org_targets: set[_OrgTarget] = set()
    notified_detail_targets: set[_DetailTarget] = set()
    notified_pending_approval_targets: set[_OrgTarget] = set()

    def handle_requisition_event(
        event: _RequisitionEvent,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_org_targets.clear()
            notified_detail_targets.clear()
            notified_pending_approval_targets.clear()

        org_scope = OrganizationScope(event.tenant_id, event.organization_id)

        if _requisition_event_notifies_list(event):
            org_target = _org_scope_target(REQUISITION_LIST_SCOPE_CODE, org_scope)
            if org_target not in notified_org_targets:
                notified_org_targets.add(org_target)
                channel.notify(
                    ViewInvalidationHint(
                        scope=org_scope,
                        category=PROCUREMENT_CATEGORY,
                        scope_code=REQUISITION_LIST_SCOPE_CODE,
                        entity_type=REQUISITION_ENTITY_TYPE,
                        entity_id=event.requisition_id,
                    )
                )

        if _requisition_event_notifies_detail(event):
            detail_scope = ResourceScope(
                tenant_id=event.tenant_id,
                organization_id=event.organization_id,
                module_code=PROCUREMENT_MODULE_CODE,
                entity_type=REQUISITION_ENTITY_TYPE,
                entity_id=event.requisition_id,
            )
            detail_target = _detail_scope_target(REQUISITION_DETAIL_SCOPE_CODE, detail_scope)
            if detail_target not in notified_detail_targets:
                notified_detail_targets.add(detail_target)
                channel.notify(
                    ViewInvalidationHint(
                        scope=detail_scope,
                        category=PROCUREMENT_CATEGORY,
                        scope_code=REQUISITION_DETAIL_SCOPE_CODE,
                        entity_type=REQUISITION_ENTITY_TYPE,
                        entity_id=event.requisition_id,
                    )
                )

        if _requisition_event_notifies_pending_approval(event):
            pending_target = _org_scope_target(REQUISITION_PENDING_APPROVAL_SCOPE_CODE, org_scope)
            if pending_target not in notified_pending_approval_targets:
                notified_pending_approval_targets.add(pending_target)
                channel.notify(
                    ViewInvalidationHint(
                        scope=org_scope,
                        category=PROCUREMENT_CATEGORY,
                        scope_code=REQUISITION_PENDING_APPROVAL_SCOPE_CODE,
                        entity_type=REQUISITION_ENTITY_TYPE,
                        entity_id=event.requisition_id,
                    )
                )

    return handle_requisition_event


__all__ = [
    "build_purchase_order_view_invalidation_handler",
    "build_requisition_view_invalidation_handler",
    "PROCUREMENT_CATEGORY",
    "PURCHASE_ORDER_LIST_SCOPE_CODE",
    "PURCHASE_ORDER_DETAIL_SCOPE_CODE",
    "REQUISITION_LIST_SCOPE_CODE",
    "REQUISITION_DETAIL_SCOPE_CODE",
    "REQUISITION_PENDING_APPROVAL_SCOPE_CODE",
    "PROCUREMENT_MODULE_CODE",
    "PURCHASE_ORDER_ENTITY_TYPE",
    "REQUISITION_ENTITY_TYPE",
]
