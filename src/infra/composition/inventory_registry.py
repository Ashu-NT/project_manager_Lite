from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.access import ScopedRolePolicy
from core.modules.inventory_procurement import (
    InventoryDataExchangeService,
    MaintenanceMaterialService,
    InventoryReferenceService,
    InventoryService,
    InventoryReportingService,
    ItemCategoryService,
    ItemMasterService,
    ProcurementService,
    PurchasingService,
    ReservationService,
    StockControlService,
)
from core.modules.inventory_procurement.access.policy import (
    STOREROOM_SCOPE_ROLE_CHOICES,
    normalize_storeroom_scope_role,
    resolve_storeroom_scope_permissions,
)
from infra.modules.inventory_procurement.db import (
    SqlAlchemyInventoryItemCategoryRepository,
    SqlAlchemyPurchaseOrderLineRepository,
    SqlAlchemyPurchaseOrderRepository,
    SqlAlchemyPurchaseRequisitionLineRepository,
    SqlAlchemyPurchaseRequisitionRepository,
    SqlAlchemyReceiptHeaderRepository,
    SqlAlchemyReceiptLineRepository,
    SqlAlchemyStockBalanceRepository,
    SqlAlchemyStockItemRepository,
    SqlAlchemyStockReservationRepository,
    SqlAlchemyStockTransactionRepository,
    SqlAlchemyStoreroomRepository,
)
from src.infra.composition.platform_registry import PlatformServiceBundle


@dataclass(frozen=True)
class InventoryProcurementServiceBundle:
    inventory_reference_service: InventoryReferenceService
    inventory_data_exchange_service: InventoryDataExchangeService
    inventory_reporting_service: InventoryReportingService
    inventory_item_category_service: ItemCategoryService
    inventory_item_service: ItemMasterService
    inventory_maintenance_material_service: MaintenanceMaterialService
    inventory_service: InventoryService
    inventory_stock_service: StockControlService
    inventory_reservation_service: ReservationService
    inventory_procurement_service: ProcurementService
    inventory_purchasing_service: PurchasingService


def build_inventory_procurement_service_bundle(
    platform_services: PlatformServiceBundle,
) -> InventoryProcurementServiceBundle:
    platform_services.access_service.register_scope_policy(
        ScopedRolePolicy(
            scope_type="storeroom",
            role_choices=STOREROOM_SCOPE_ROLE_CHOICES,
            normalize_role=normalize_storeroom_scope_role,
            resolve_permissions=resolve_storeroom_scope_permissions,
        )
    )
    balance_repo = SqlAlchemyStockBalanceRepository(platform_services.session)
    category_repo = SqlAlchemyInventoryItemCategoryRepository(platform_services.session)
    item_repo = SqlAlchemyStockItemRepository(platform_services.session)
    purchase_order_line_repo = SqlAlchemyPurchaseOrderLineRepository(platform_services.session)
    purchase_order_repo = SqlAlchemyPurchaseOrderRepository(platform_services.session)
    requisition_line_repo = SqlAlchemyPurchaseRequisitionLineRepository(platform_services.session)
    requisition_repo = SqlAlchemyPurchaseRequisitionRepository(platform_services.session)
    receipt_header_repo = SqlAlchemyReceiptHeaderRepository(platform_services.session)
    receipt_line_repo = SqlAlchemyReceiptLineRepository(platform_services.session)
    reservation_repo = SqlAlchemyStockReservationRepository(platform_services.session)
    transaction_repo = SqlAlchemyStockTransactionRepository(platform_services.session)
    storeroom_repo = SqlAlchemyStoreroomRepository(platform_services.session)
    inventory_item_category_service = ItemCategoryService(
        platform_services.session,
        category_repo,
        organization_repo=platform_services.organization_repo,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
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
        category_repo=category_repo,
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
    inventory_stock_service = StockControlService(
        platform_services.session,
        balance_repo,
        transaction_repo,
        organization_repo=platform_services.organization_repo,
        item_service=inventory_item_service,
        inventory_service=inventory_service,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    inventory_purchasing_service = PurchasingService(
        platform_services.session,
        purchase_order_repo,
        purchase_order_line_repo,
        receipt_header_repo,
        receipt_line_repo,
        requisition_repo=requisition_repo,
        requisition_line_repo=requisition_line_repo,
        balance_repo=balance_repo,
        organization_repo=platform_services.organization_repo,
        reference_service=InventoryReferenceService(
            site_service=platform_services.site_service,
            party_service=platform_services.party_service,
            user_session=platform_services.user_session,
        ),
        inventory_service=inventory_service,
        item_service=inventory_item_service,
        stock_service=inventory_stock_service,
        approval_service=platform_services.approval_service,
        user_session=platform_services.user_session,
        audit_service=platform_services.audit_service,
    )
    inventory_reservation_service = ReservationService(
        platform_services.session,
        reservation_repo,
        organization_repo=platform_services.organization_repo,
        item_service=inventory_item_service,
        inventory_service=inventory_service,
        stock_service=inventory_stock_service,
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
    platform_services.approval_service.register_apply_handler(
        "purchase_order.submit",
        inventory_purchasing_service.apply_submitted_purchase_order_approval,
    )
    platform_services.approval_service.register_reject_handler(
        "purchase_order.submit",
        inventory_purchasing_service.apply_submitted_purchase_order_rejection,
    )
    inventory_reference_service = InventoryReferenceService(
        site_service=platform_services.site_service,
        party_service=platform_services.party_service,
        user_session=platform_services.user_session,
    )
    inventory_data_exchange_service = InventoryDataExchangeService(
        item_service=inventory_item_service,
        inventory_service=inventory_service,
        procurement_service=inventory_procurement_service,
        purchasing_service=inventory_purchasing_service,
        approval_service=platform_services.approval_service,
        site_service=platform_services.site_service,
        party_service=platform_services.party_service,
        requisition_line_repo=requisition_line_repo,
        purchase_order_line_repo=purchase_order_line_repo,
        receipt_line_repo=receipt_line_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
        runtime_execution_service=platform_services.runtime_execution_service,
    )
    inventory_reporting_service = InventoryReportingService(
        reference_service=inventory_reference_service,
        item_service=inventory_item_service,
        inventory_service=inventory_service,
        stock_service=inventory_stock_service,
        procurement_service=inventory_procurement_service,
        purchasing_service=inventory_purchasing_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
        runtime_execution_service=platform_services.runtime_execution_service,
    )
    inventory_maintenance_material_service = MaintenanceMaterialService(
        item_service=inventory_item_service,
        item_category_service=inventory_item_category_service,
        inventory_service=inventory_service,
        stock_service=inventory_stock_service,
        reservation_service=inventory_reservation_service,
        procurement_service=inventory_procurement_service,
    )

    def _storeroom_exists(storeroom_id: str) -> bool:
        storeroom = storeroom_repo.get(storeroom_id)
        organization = platform_services.organization_repo.get_active()
        return bool(
            storeroom is not None
            and organization is not None
            and storeroom.organization_id == organization.id
        )

    platform_services.access_service.register_scope_exists_resolver("storeroom", _storeroom_exists)

    return InventoryProcurementServiceBundle(
        inventory_reference_service=inventory_reference_service,
        inventory_data_exchange_service=inventory_data_exchange_service,
        inventory_reporting_service=inventory_reporting_service,
        inventory_item_category_service=inventory_item_category_service,
        inventory_item_service=inventory_item_service,
        inventory_maintenance_material_service=inventory_maintenance_material_service,
        inventory_service=inventory_service,
        inventory_stock_service=inventory_stock_service,
        inventory_reservation_service=inventory_reservation_service,
        inventory_procurement_service=inventory_procurement_service,
        inventory_purchasing_service=inventory_purchasing_service,
    )


__all__ = ["InventoryProcurementServiceBundle", "build_inventory_procurement_service_bundle"]
