from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.contracts.repositories.catalog import (
    InventoryItemCategoryRepository,
    StockItemRepository,
)
from src.core.modules.inventory_procurement.domain.catalog.item import (
    InventoryItemCategory,
    StockItem,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.mappers.catalog import (
    inventory_item_category_from_orm,
    inventory_item_category_to_orm,
    stock_item_from_orm,
    stock_item_to_orm,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.orm.catalog import (
    InventoryItemCategoryORM,
    StockItemORM,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories._tenant_scope import (
    InventoryTenantScopedRepositorySupport,
)
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyInventoryItemCategoryRepository(
    InventoryItemCategoryRepository, InventoryTenantScopedRepositorySupport
):
    _repository_label = "Inventory item category repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, category: InventoryItemCategory) -> None:
        ctx = self._context(operation_label="add inventory item category")
        orm = inventory_item_category_to_orm(category)
        self._stamp_scope(ctx, orm)
        self.session.add(orm)

    def update(self, category: InventoryItemCategory) -> None:
        self._require_in_scope(
            InventoryItemCategoryORM,
            category.id,
            operation_label="update inventory item category",
            not_found_message="Inventory item category not found.",
        )
        category.version = update_with_version_check(
            self.session,
            InventoryItemCategoryORM,
            category.id,
            getattr(category, "version", 1),
            {
                "category_code": category.category_code,
                "name": category.name,
                "description": category.description or None,
                "category_type": category.category_type,
                "is_equipment": category.is_equipment,
                "supports_project_usage": category.supports_project_usage,
                "supports_maintenance_usage": category.supports_maintenance_usage,
                "is_active": category.is_active,
                "created_at": category.created_at,
                "updated_at": category.updated_at,
            },
            not_found_message="Inventory item category not found.",
            stale_message="Inventory item category was updated by another user.",
        )

    def get(self, category_id: str) -> InventoryItemCategory | None:
        obj = self._get_in_scope(
            InventoryItemCategoryORM,
            category_id,
            operation_label="get inventory item category",
        )
        return inventory_item_category_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, category_code: str) -> InventoryItemCategory | None:
        ctx = self._context(operation_label="get inventory item category by code")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(InventoryItemCategoryORM).where(
            InventoryItemCategoryORM.organization_id == organization_id,
            InventoryItemCategoryORM.category_code == category_code,
        )
        stmt = self._apply_scope(stmt, InventoryItemCategoryORM, ctx)
        obj = self.session.execute(stmt).scalars().first()
        return inventory_item_category_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        category_type: str | None = None,
    ) -> list[InventoryItemCategory]:
        ctx = self._context(operation_label="list inventory item categories")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(InventoryItemCategoryORM).where(InventoryItemCategoryORM.organization_id == organization_id)
        stmt = self._apply_scope(stmt, InventoryItemCategoryORM, ctx)
        if active_only is not None:
            stmt = stmt.where(InventoryItemCategoryORM.is_active == bool(active_only))
        if category_type is not None:
            stmt = stmt.where(InventoryItemCategoryORM.category_type == category_type)
        rows = self.session.execute(
            stmt.order_by(InventoryItemCategoryORM.name.asc(), InventoryItemCategoryORM.category_code.asc())
        ).scalars().all()
        return [inventory_item_category_from_orm(row) for row in rows]


class SqlAlchemyStockItemRepository(StockItemRepository, InventoryTenantScopedRepositorySupport):
    _repository_label = "Inventory item repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, item: StockItem) -> None:
        ctx = self._context(operation_label="add inventory item")
        orm = stock_item_to_orm(item)
        self._stamp_scope(ctx, orm)
        self.session.add(orm)

    def update(self, item: StockItem) -> None:
        self._require_in_scope(
            StockItemORM,
            item.id,
            operation_label="update inventory item",
            not_found_message="Inventory item not found.",
        )
        item.version = update_with_version_check(
            self.session,
            StockItemORM,
            item.id,
            getattr(item, "version", 1),
            {
                "item_code": item.item_code,
                "name": item.name,
                "description": item.description or None,
                "item_type": item.item_type or None,
                "status": item.status,
                "stock_uom": item.stock_uom,
                "order_uom": item.order_uom,
                "issue_uom": item.issue_uom,
                "order_uom_ratio": item.order_uom_ratio,
                "issue_uom_ratio": item.issue_uom_ratio,
                "category_code": item.category_code or None,
                "commodity_code": item.commodity_code or None,
                "is_stocked": item.is_stocked,
                "is_purchase_allowed": item.is_purchase_allowed,
                "is_active": item.is_active,
                "default_reorder_policy": item.default_reorder_policy or None,
                "min_qty": item.min_qty,
                "max_qty": item.max_qty,
                "reorder_point": item.reorder_point,
                "reorder_qty": item.reorder_qty,
                "lead_time_days": item.lead_time_days,
                "is_lot_tracked": item.is_lot_tracked,
                "is_serial_tracked": item.is_serial_tracked,
                "shelf_life_days": item.shelf_life_days,
                "preferred_party_id": item.preferred_party_id,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "notes": item.notes or None,
            },
            not_found_message="Inventory item not found.",
            stale_message="Inventory item was updated by another user.",
        )

    def get(self, item_id: str) -> StockItem | None:
        obj = self._get_in_scope(
            StockItemORM,
            item_id,
            operation_label="get inventory item",
        )
        return stock_item_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, item_code: str) -> StockItem | None:
        ctx = self._context(operation_label="get inventory item by code")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(StockItemORM).where(
            StockItemORM.organization_id == organization_id,
            StockItemORM.item_code == item_code,
        )
        stmt = self._apply_scope(stmt, StockItemORM, ctx)
        obj = self.session.execute(stmt).scalars().first()
        return stock_item_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[StockItem]:
        ctx = self._context(operation_label="list inventory items")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(StockItemORM).where(StockItemORM.organization_id == organization_id)
        stmt = self._apply_scope(stmt, StockItemORM, ctx)
        if active_only is not None:
            stmt = stmt.where(StockItemORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(StockItemORM.name.asc())).scalars().all()
        return [stock_item_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyInventoryItemCategoryRepository",
    "SqlAlchemyStockItemRepository",
]
