from __future__ import annotations

from sqlalchemy.orm import Session

from . import item_commands, item_document_service, item_queries
from src.core.modules.inventory_procurement.contracts.repositories.catalog import (
    InventoryItemCategoryRepository,
    StockItemRepository,
)
from src.core.modules.inventory_procurement.domain.catalog.item import StockItem
from src.core.platform.documents import Document, DocumentIntegrationService, DocumentLink
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.party import PartyService
from src.core.platform.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)


class ItemMasterService:
    def __init__(
        self,
        session: Session,
        item_repo: StockItemRepository,
        *,
        category_repo: InventoryItemCategoryRepository | None = None,
        organization_repo: OrganizationRepository,
        party_service: PartyService,
        document_integration_service: DocumentIntegrationService,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        audit_service=None,
    ) -> None:
        self._session = session
        self._item_repo = item_repo
        self._category_repo = category_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = require_tenant_context_service(
            tenant_context_service,
            consumer_label="ItemMasterService",
        )
        self._party_service = party_service
        self._document_integration_service = document_integration_service
        self._user_session = user_session
        self._audit_service = audit_service
        self._catalog_operation_label = "inventory items"

    def list_items(self, *, active_only: bool | None = None) -> list[StockItem]:
        return item_queries.list_items(self, active_only=active_only)

    def search_items(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
        category_code: str | None = None,
        equipment_only: bool | None = None,
        project_usage_only: bool | None = None,
        maintenance_usage_only: bool | None = None,
    ) -> list[StockItem]:
        return item_queries.search_items(
            self,
            search_text=search_text,
            active_only=active_only,
            category_code=category_code,
            equipment_only=equipment_only,
            project_usage_only=project_usage_only,
            maintenance_usage_only=maintenance_usage_only,
        )

    def get_item(self, item_id: str) -> StockItem:
        return item_queries.get_item(self, item_id)

    def get_item_for_internal_use(self, item_id: str) -> StockItem:
        return item_queries.get_item_for_internal_use(self, item_id)

    def find_item_by_code(self, item_code: str) -> StockItem | None:
        return item_queries.find_item_by_code(self, item_code)

    def create_item(
        self,
        *,
        item_code: str,
        name: str,
        description: str = "",
        item_type: str = "",
        status: str | None = None,
        stock_uom: str,
        order_uom: str | None = None,
        issue_uom: str | None = None,
        order_uom_ratio: float | None = None,
        issue_uom_ratio: float | None = None,
        category_code: str = "",
        commodity_code: str = "",
        is_stocked: bool = True,
        is_purchase_allowed: bool = True,
        default_reorder_policy: str = "",
        min_qty: float = 0.0,
        max_qty: float = 0.0,
        reorder_point: float = 0.0,
        reorder_qty: float = 0.0,
        lead_time_days: int | None = None,
        is_lot_tracked: bool = False,
        is_serial_tracked: bool = False,
        shelf_life_days: int | None = None,
        preferred_party_id: str | None = None,
        notes: str = "",
    ) -> StockItem:
        return item_commands.create_item(
            self,
            item_code=item_code,
            name=name,
            description=description,
            item_type=item_type,
            status=status,
            stock_uom=stock_uom,
            order_uom=order_uom,
            issue_uom=issue_uom,
            order_uom_ratio=order_uom_ratio,
            issue_uom_ratio=issue_uom_ratio,
            category_code=category_code,
            commodity_code=commodity_code,
            is_stocked=is_stocked,
            is_purchase_allowed=is_purchase_allowed,
            default_reorder_policy=default_reorder_policy,
            min_qty=min_qty,
            max_qty=max_qty,
            reorder_point=reorder_point,
            reorder_qty=reorder_qty,
            lead_time_days=lead_time_days,
            is_lot_tracked=is_lot_tracked,
            is_serial_tracked=is_serial_tracked,
            shelf_life_days=shelf_life_days,
            preferred_party_id=preferred_party_id,
            notes=notes,
        )

    def update_item(
        self,
        item_id: str,
        *,
        item_code: str | None = None,
        name: str | None = None,
        description: str | None = None,
        item_type: str | None = None,
        status: str | None = None,
        is_stocked: bool | None = None,
        is_purchase_allowed: bool | None = None,
        stock_uom: str | None = None,
        order_uom: str | None = None,
        issue_uom: str | None = None,
        order_uom_ratio: float | None = None,
        issue_uom_ratio: float | None = None,
        category_code: str | None = None,
        commodity_code: str | None = None,
        default_reorder_policy: str | None = None,
        min_qty: float | None = None,
        max_qty: float | None = None,
        reorder_point: float | None = None,
        reorder_qty: float | None = None,
        lead_time_days: int | None = None,
        is_lot_tracked: bool | None = None,
        is_serial_tracked: bool | None = None,
        shelf_life_days: int | None = None,
        preferred_party_id: str | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> StockItem:
        return item_commands.update_item(
            self,
            item_id,
            item_code=item_code,
            name=name,
            description=description,
            item_type=item_type,
            status=status,
            is_stocked=is_stocked,
            is_purchase_allowed=is_purchase_allowed,
            stock_uom=stock_uom,
            order_uom=order_uom,
            issue_uom=issue_uom,
            order_uom_ratio=order_uom_ratio,
            issue_uom_ratio=issue_uom_ratio,
            category_code=category_code,
            commodity_code=commodity_code,
            default_reorder_policy=default_reorder_policy,
            min_qty=min_qty,
            max_qty=max_qty,
            reorder_point=reorder_point,
            reorder_qty=reorder_qty,
            lead_time_days=lead_time_days,
            is_lot_tracked=is_lot_tracked,
            is_serial_tracked=is_serial_tracked,
            shelf_life_days=shelf_life_days,
            preferred_party_id=preferred_party_id,
            is_active=is_active,
            notes=notes,
            expected_version=expected_version,
        )

    def list_linked_documents(
        self,
        item_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Document]:
        return item_document_service.list_linked_documents(
            self,
            item_id,
            active_only=active_only,
        )

    def list_available_documents(
        self,
        *,
        active_only: bool | None = True,
    ) -> list[Document]:
        return item_document_service.list_available_documents(
            self,
            active_only=active_only,
        )

    def link_document(
        self,
        item_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> DocumentLink:
        return item_document_service.link_document(
            self,
            item_id,
            document_id=document_id,
            link_role=link_role,
        )

    def unlink_document(
        self,
        item_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> None:
        item_document_service.unlink_document(
            self,
            item_id,
            document_id=document_id,
            link_role=link_role,
        )


__all__ = ["ItemMasterService"]
