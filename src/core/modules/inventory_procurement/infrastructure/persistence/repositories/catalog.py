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
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyInventoryItemCategoryRepository(InventoryItemCategoryRepository):
    def __init__(self, session: Session, *, tenant_id_provider=None):
        self.session = session
        self._tenant_id_provider = tenant_id_provider or (lambda: None)

    def add(self, category: InventoryItemCategory) -> None:
        orm = inventory_item_category_to_orm(category)
        if orm.tenant_id is None:
            orm.tenant_id = self._tenant_id_provider()
        self.session.add(orm)

    def update(self, category: InventoryItemCategory) -> None:
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
        obj = self.session.get(InventoryItemCategoryORM, category_id)
        if obj is None:
            return None
        _tid = self._tenant_id_provider()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return inventory_item_category_from_orm(obj)

    def get_by_code(self, organization_id: str, category_code: str) -> InventoryItemCategory | None:
        _tid = self._tenant_id_provider()
        stmt = select(InventoryItemCategoryORM).where(
            InventoryItemCategoryORM.organization_id == organization_id,
            InventoryItemCategoryORM.category_code == category_code,
        )
        if _tid is not None:
            stmt = stmt.where(InventoryItemCategoryORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalars().first()
        return inventory_item_category_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        category_type: str | None = None,
    ) -> list[InventoryItemCategory]:
        _tid = self._tenant_id_provider()
        stmt = select(InventoryItemCategoryORM).where(InventoryItemCategoryORM.organization_id == organization_id)
        if _tid is not None:
            stmt = stmt.where(InventoryItemCategoryORM.tenant_id == _tid)
        if active_only is not None:
            stmt = stmt.where(InventoryItemCategoryORM.is_active == bool(active_only))
        if category_type is not None:
            stmt = stmt.where(InventoryItemCategoryORM.category_type == category_type)
        rows = self.session.execute(
            stmt.order_by(InventoryItemCategoryORM.name.asc(), InventoryItemCategoryORM.category_code.asc())
        ).scalars().all()
        return [inventory_item_category_from_orm(row) for row in rows]


class SqlAlchemyStockItemRepository(StockItemRepository):
    def __init__(self, session: Session, *, tenant_id_provider=None):
        self.session = session
        self._tenant_id_provider = tenant_id_provider or (lambda: None)

    def add(self, item: StockItem) -> None:
        orm = stock_item_to_orm(item)
        if orm.tenant_id is None:
            orm.tenant_id = self._tenant_id_provider()
        self.session.add(orm)

    def update(self, item: StockItem) -> None:
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
        obj = self.session.get(StockItemORM, item_id)
        if obj is None:
            return None
        _tid = self._tenant_id_provider()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return stock_item_from_orm(obj)

    def get_by_code(self, organization_id: str, item_code: str) -> StockItem | None:
        _tid = self._tenant_id_provider()
        stmt = select(StockItemORM).where(
            StockItemORM.organization_id == organization_id,
            StockItemORM.item_code == item_code,
        )
        if _tid is not None:
            stmt = stmt.where(StockItemORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalars().first()
        return stock_item_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[StockItem]:
        _tid = self._tenant_id_provider()
        stmt = select(StockItemORM).where(StockItemORM.organization_id == organization_id)
        if _tid is not None:
            stmt = stmt.where(StockItemORM.tenant_id == _tid)
        if active_only is not None:
            stmt = stmt.where(StockItemORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(StockItemORM.name.asc())).scalars().all()
        return [stock_item_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyInventoryItemCategoryRepository",
    "SqlAlchemyStockItemRepository",
]
