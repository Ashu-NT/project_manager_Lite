from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.modules.inventory_procurement.domain import StockBalance, StockItem, StockTransaction, Storeroom
from core.modules.inventory_procurement.interfaces import (
    PurchaseRequisitionLineRepository,
    PurchaseRequisitionRepository,
    StockBalanceRepository,
    StockItemRepository,
    StockTransactionRepository,
    StoreroomRepository,
)
from infra.modules.inventory_procurement.db.mapper import (
    purchase_requisition_from_orm,
    purchase_requisition_line_from_orm,
    purchase_requisition_line_to_orm,
    purchase_requisition_to_orm,
    stock_balance_from_orm,
    stock_balance_to_orm,
    stock_item_from_orm,
    stock_item_to_orm,
    stock_transaction_from_orm,
    stock_transaction_to_orm,
    storeroom_from_orm,
    storeroom_to_orm,
)
from infra.platform.db.models import StockBalanceORM, StockItemORM, StockTransactionORM, StoreroomORM
from infra.platform.db.models import PurchaseRequisitionLineORM, PurchaseRequisitionORM
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


class SqlAlchemyStockBalanceRepository(StockBalanceRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, balance: StockBalance) -> None:
        self.session.add(stock_balance_to_orm(balance))

    def update(self, balance: StockBalance) -> None:
        balance.version = update_with_version_check(
            self.session,
            StockBalanceORM,
            balance.id,
            getattr(balance, "version", 1),
            {
                "uom": balance.uom,
                "on_hand_qty": balance.on_hand_qty,
                "reserved_qty": balance.reserved_qty,
                "available_qty": balance.available_qty,
                "on_order_qty": balance.on_order_qty,
                "committed_qty": balance.committed_qty,
                "average_cost": balance.average_cost,
                "last_receipt_at": balance.last_receipt_at,
                "last_issue_at": balance.last_issue_at,
                "reorder_required": balance.reorder_required,
                "updated_at": balance.updated_at,
            },
            not_found_message="Stock balance not found.",
            stale_message="Stock balance was updated by another user.",
        )

    def get(self, balance_id: str) -> StockBalance | None:
        obj = self.session.get(StockBalanceORM, balance_id)
        return stock_balance_from_orm(obj) if obj else None

    def get_for_stock_position(
        self,
        organization_id: str,
        stock_item_id: str,
        storeroom_id: str,
    ) -> StockBalance | None:
        stmt = select(StockBalanceORM).where(
            StockBalanceORM.organization_id == organization_id,
            StockBalanceORM.stock_item_id == stock_item_id,
            StockBalanceORM.storeroom_id == storeroom_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return stock_balance_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
    ) -> list[StockBalance]:
        stmt = select(StockBalanceORM).where(StockBalanceORM.organization_id == organization_id)
        if stock_item_id is not None:
            stmt = stmt.where(StockBalanceORM.stock_item_id == stock_item_id)
        if storeroom_id is not None:
            stmt = stmt.where(StockBalanceORM.storeroom_id == storeroom_id)
        rows = self.session.execute(stmt.order_by(StockBalanceORM.updated_at.desc())).scalars().all()
        return [stock_balance_from_orm(row) for row in rows]


class SqlAlchemyStockTransactionRepository(StockTransactionRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, transaction: StockTransaction) -> None:
        self.session.add(stock_transaction_to_orm(transaction))

    def get(self, transaction_id: str) -> StockTransaction | None:
        obj = self.session.get(StockTransactionORM, transaction_id)
        return stock_transaction_from_orm(obj) if obj else None

    def get_by_number(self, organization_id: str, transaction_number: str) -> StockTransaction | None:
        stmt = select(StockTransactionORM).where(
            StockTransactionORM.organization_id == organization_id,
            StockTransactionORM.transaction_number == transaction_number,
        )
        obj = self.session.execute(stmt).scalars().first()
        return stock_transaction_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        limit: int = 200,
    ) -> list[StockTransaction]:
        stmt = select(StockTransactionORM).where(StockTransactionORM.organization_id == organization_id)
        if stock_item_id is not None:
            stmt = stmt.where(StockTransactionORM.stock_item_id == stock_item_id)
        if storeroom_id is not None:
            stmt = stmt.where(StockTransactionORM.storeroom_id == storeroom_id)
        rows = self.session.execute(
            stmt.order_by(StockTransactionORM.transaction_at.desc()).limit(max(1, int(limit or 200)))
        ).scalars().all()
        return [stock_transaction_from_orm(row) for row in rows]


class SqlAlchemyPurchaseRequisitionRepository(PurchaseRequisitionRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, requisition) -> None:
        self.session.add(purchase_requisition_to_orm(requisition))

    def update(self, requisition) -> None:
        requisition.version = update_with_version_check(
            self.session,
            PurchaseRequisitionORM,
            requisition.id,
            getattr(requisition, "version", 1),
            {
                "requisition_number": requisition.requisition_number,
                "requesting_site_id": requisition.requesting_site_id,
                "requesting_storeroom_id": requisition.requesting_storeroom_id,
                "requester_user_id": requisition.requester_user_id,
                "requester_username": requisition.requester_username or None,
                "status": requisition.status,
                "purpose": requisition.purpose or None,
                "needed_by_date": requisition.needed_by_date,
                "priority": requisition.priority or None,
                "approval_request_id": requisition.approval_request_id,
                "source_reference_type": requisition.source_reference_type or None,
                "source_reference_id": requisition.source_reference_id or None,
                "submitted_at": requisition.submitted_at,
                "approved_at": requisition.approved_at,
                "cancelled_at": requisition.cancelled_at,
                "notes": requisition.notes or None,
                "created_at": requisition.created_at,
                "updated_at": requisition.updated_at,
            },
            not_found_message="Purchase requisition not found.",
            stale_message="Purchase requisition was updated by another user.",
        )

    def get(self, requisition_id: str):
        obj = self.session.get(PurchaseRequisitionORM, requisition_id)
        return purchase_requisition_from_orm(obj) if obj else None

    def get_by_number(self, organization_id: str, requisition_number: str):
        stmt = select(PurchaseRequisitionORM).where(
            PurchaseRequisitionORM.organization_id == organization_id,
            PurchaseRequisitionORM.requisition_number == requisition_number,
        )
        obj = self.session.execute(stmt).scalars().first()
        return purchase_requisition_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        status: str | None = None,
        site_id: str | None = None,
        storeroom_id: str | None = None,
        limit: int = 200,
    ):
        stmt = select(PurchaseRequisitionORM).where(PurchaseRequisitionORM.organization_id == organization_id)
        if status is not None:
            stmt = stmt.where(PurchaseRequisitionORM.status == status)
        if site_id is not None:
            stmt = stmt.where(PurchaseRequisitionORM.requesting_site_id == site_id)
        if storeroom_id is not None:
            stmt = stmt.where(PurchaseRequisitionORM.requesting_storeroom_id == storeroom_id)
        rows = self.session.execute(
            stmt.order_by(PurchaseRequisitionORM.created_at.desc()).limit(max(1, int(limit or 200)))
        ).scalars().all()
        return [purchase_requisition_from_orm(row) for row in rows]


class SqlAlchemyPurchaseRequisitionLineRepository(PurchaseRequisitionLineRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, line) -> None:
        self.session.add(purchase_requisition_line_to_orm(line))

    def update(self, line) -> None:
        obj = self.session.get(PurchaseRequisitionLineORM, line.id)
        if obj is None:
            raise ValueError("Purchase requisition line not found.")
        obj.line_number = line.line_number
        obj.stock_item_id = line.stock_item_id
        obj.description = line.description or None
        obj.quantity_requested = line.quantity_requested
        obj.uom = line.uom
        obj.needed_by_date = line.needed_by_date
        obj.estimated_unit_cost = line.estimated_unit_cost
        obj.suggested_supplier_party_id = line.suggested_supplier_party_id
        obj.status = line.status
        obj.notes = line.notes or None

    def get(self, line_id: str):
        obj = self.session.get(PurchaseRequisitionLineORM, line_id)
        return purchase_requisition_line_from_orm(obj) if obj else None

    def list_for_requisition(self, requisition_id: str):
        stmt = select(PurchaseRequisitionLineORM).where(
            PurchaseRequisitionLineORM.purchase_requisition_id == requisition_id
        )
        rows = self.session.execute(stmt.order_by(PurchaseRequisitionLineORM.line_number.asc())).scalars().all()
        return [purchase_requisition_line_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyPurchaseRequisitionLineRepository",
    "SqlAlchemyPurchaseRequisitionRepository",
    "SqlAlchemyStockBalanceRepository",
    "SqlAlchemyStockItemRepository",
    "SqlAlchemyStockTransactionRepository",
    "SqlAlchemyStoreroomRepository",
]
