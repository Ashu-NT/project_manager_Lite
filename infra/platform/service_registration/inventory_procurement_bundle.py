from __future__ import annotations

from dataclasses import dataclass

from core.modules.inventory_procurement import InventoryReferenceService, InventoryService, ItemMasterService
from infra.modules.inventory_procurement.db import SqlAlchemyStockItemRepository, SqlAlchemyStoreroomRepository
from infra.platform.service_registration.platform_bundle import PlatformServiceBundle


@dataclass(frozen=True)
class InventoryProcurementServiceBundle:
    inventory_reference_service: InventoryReferenceService
    inventory_item_service: ItemMasterService
    inventory_service: InventoryService


def build_inventory_procurement_service_bundle(
    platform_services: PlatformServiceBundle,
) -> InventoryProcurementServiceBundle:
    item_repo = SqlAlchemyStockItemRepository(platform_services.session)
    storeroom_repo = SqlAlchemyStoreroomRepository(platform_services.session)
    return InventoryProcurementServiceBundle(
        inventory_reference_service=InventoryReferenceService(
            site_service=platform_services.site_service,
            party_service=platform_services.party_service,
            user_session=platform_services.user_session,
        ),
        inventory_item_service=ItemMasterService(
            platform_services.session,
            item_repo,
            organization_repo=platform_services.organization_repo,
            party_service=platform_services.party_service,
            document_integration_service=platform_services.document_integration_service,
            user_session=platform_services.user_session,
            audit_service=platform_services.audit_service,
        ),
        inventory_service=InventoryService(
            platform_services.session,
            storeroom_repo,
            organization_repo=platform_services.organization_repo,
            site_service=platform_services.site_service,
            party_service=platform_services.party_service,
            user_session=platform_services.user_session,
            audit_service=platform_services.audit_service,
        ),
    )


__all__ = ["InventoryProcurementServiceBundle", "build_inventory_procurement_service_bundle"]
