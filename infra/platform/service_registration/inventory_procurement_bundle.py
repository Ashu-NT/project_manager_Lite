from __future__ import annotations

from dataclasses import dataclass

from core.modules.inventory_procurement import (
    InventoryReferenceService,
    InventoryService,
    ItemMasterService,
    ProcurementService,
    StockControlService,
)
from infra.modules.inventory_procurement.db import (
    SqlAlchemyPurchaseRequisitionLineRepository,
    SqlAlchemyPurchaseRequisitionRepository,
    SqlAlchemyStockBalanceRepository,
    SqlAlchemyStockItemRepository,
    SqlAlchemyStockTransactionRepository,
    SqlAlchemyStoreroomRepository,
)
from infra.platform.service_registration.platform_bundle import PlatformServiceBundle


@dataclass(frozen=True)
class InventoryProcurementServiceBundle:
    inventory_reference_service: InventoryReferenceService
    inventory_item_service: ItemMasterService
    inventory_service: InventoryService
    inventory_stock_service: StockControlService
    inventory_procurement_service: ProcurementService


def build_inventory_procurement_service_bundle(
    platform_services: PlatformServiceBundle,
) -> InventoryProcurementServiceBundle:
    balance_repo = SqlAlchemyStockBalanceRepository(platform_services.session)
    item_repo = SqlAlchemyStockItemRepository(platform_services.session)
    requisition_line_repo = SqlAlchemyPurchaseRequisitionLineRepository(platform_services.session)
    requisition_repo = SqlAlchemyPurchaseRequisitionRepository(platform_services.session)
    transaction_repo = SqlAlchemyStockTransactionRepository(platform_services.session)
    storeroom_repo = SqlAlchemyStoreroomRepository(platform_services.session)
    inventory_service = InventoryService(
        platform_services.session,
        storeroom_repo,
        organization_repo=platform_services.organization_repo,
        site_service=platform_services.site_service,
        party_service=platform_services.party_service,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    inventory_item_service = ItemMasterService(
        platform_services.session,
        item_repo,
        organization_repo=platform_services.organization_repo,
        party_service=platform_services.party_service,
        document_integration_service=platform_services.document_integration_service,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    inventory_procurement_service = ProcurementService(
        platform_services.session,
        requisition_repo,
        requisition_line_repo,
        organization_repo=platform_services.organization_repo,
        inventory_service=inventory_service,
        item_service=inventory_item_service,
        party_service=platform_services.party_service,
        approval_service=platform_services.approval_service,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    platform_services.approval_service.register_apply_handler(
        "purchase_requisition.submit",
        inventory_procurement_service.apply_submitted_requisition_approval,
    )
    platform_services.approval_service.register_reject_handler(
        "purchase_requisition.submit",
        inventory_procurement_service.apply_submitted_requisition_rejection,
    )
    return InventoryProcurementServiceBundle(
        inventory_reference_service=InventoryReferenceService(
            site_service=platform_services.site_service,
            party_service=platform_services.party_service,
            user_session=platform_services.user_session,
        ),
        inventory_item_service=inventory_item_service,
        inventory_service=inventory_service,
        inventory_stock_service=StockControlService(
            platform_services.session,
            balance_repo,
            transaction_repo,
            organization_repo=platform_services.organization_repo,
            item_service=inventory_item_service,
            inventory_service=inventory_service,
            user_session=platform_services.user_session,
            audit_service=platform_services.audit_service,
        ),
        inventory_procurement_service=inventory_procurement_service,
    )


__all__ = ["InventoryProcurementServiceBundle", "build_inventory_procurement_service_bundle"]
