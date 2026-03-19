from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.modules.inventory_procurement.domain import StockItem, Storeroom
from core.modules.inventory_procurement.interfaces import StockItemRepository, StoreroomRepository
from infra.modules.inventory_procurement.db.mapper import (
    stock_item_from_orm,
    stock_item_to_orm,
    storeroom_from_orm,
    storeroom_to_orm,
)
from infra.platform.db.models import StockItemORM, StoreroomORM
from infra.platform.db.optimistic import update_with_version_check


class SqlAlchemyStockItemRepository(StockItemRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, item: StockItem) -> None:
        self.session.add(stock_item_to_orm(item))

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
        return stock_item_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, item_code: str) -> StockItem | None:
        stmt = select(StockItemORM).where(
            StockItemORM.organization_id == organization_id,
            StockItemORM.item_code == item_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return stock_item_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[StockItem]:
        stmt = select(StockItemORM).where(StockItemORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(StockItemORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(StockItemORM.name.asc())).scalars().all()
        return [stock_item_from_orm(row) for row in rows]


class SqlAlchemyStoreroomRepository(StoreroomRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, storeroom: Storeroom) -> None:
        self.session.add(storeroom_to_orm(storeroom))

    def update(self, storeroom: Storeroom) -> None:
        storeroom.version = update_with_version_check(
            self.session,
            StoreroomORM,
            storeroom.id,
            getattr(storeroom, "version", 1),
            {
                "storeroom_code": storeroom.storeroom_code,
                "name": storeroom.name,
                "description": storeroom.description or None,
                "site_id": storeroom.site_id,
                "status": storeroom.status,
                "storeroom_type": storeroom.storeroom_type or None,
                "is_active": storeroom.is_active,
                "is_internal_supplier": storeroom.is_internal_supplier,
                "allows_issue": storeroom.allows_issue,
                "allows_transfer": storeroom.allows_transfer,
                "allows_receiving": storeroom.allows_receiving,
                "default_currency_code": storeroom.default_currency_code or None,
                "manager_party_id": storeroom.manager_party_id,
                "created_at": storeroom.created_at,
                "updated_at": storeroom.updated_at,
                "notes": storeroom.notes or None,
            },
            not_found_message="Storeroom not found.",
            stale_message="Storeroom was updated by another user.",
        )

    def get(self, storeroom_id: str) -> Storeroom | None:
        obj = self.session.get(StoreroomORM, storeroom_id)
        return storeroom_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, storeroom_code: str) -> Storeroom | None:
        stmt = select(StoreroomORM).where(
            StoreroomORM.organization_id == organization_id,
            StoreroomORM.storeroom_code == storeroom_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return storeroom_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> list[Storeroom]:
        stmt = select(StoreroomORM).where(StoreroomORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(StoreroomORM.is_active == bool(active_only))
        if site_id is not None:
            stmt = stmt.where(StoreroomORM.site_id == site_id)
        rows = self.session.execute(stmt.order_by(StoreroomORM.name.asc())).scalars().all()
        return [storeroom_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyStockItemRepository", "SqlAlchemyStoreroomRepository"]
