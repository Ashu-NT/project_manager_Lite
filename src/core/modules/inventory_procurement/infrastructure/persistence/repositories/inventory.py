from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    StockBalanceRepository,
    StockReservationRepository,
    StockTransactionRepository,
    StoreroomRepository,
)
from src.core.modules.inventory_procurement.domain.inventory.stock import (
    StockBalance,
    StockReservation,
    StockTransaction,
    Storeroom,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.mappers.inventory import (
    stock_balance_from_orm,
    stock_balance_to_orm,
    stock_reservation_from_orm,
    stock_reservation_to_orm,
    stock_transaction_from_orm,
    stock_transaction_to_orm,
    storeroom_from_orm,
    storeroom_to_orm,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.orm.inventory import (
    StockBalanceORM,
    StockReservationORM,
    StockTransactionORM,
    StoreroomORM,
)
from src.infra.persistence.db.optimistic import update_with_version_check


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
                "requires_reservation_for_issue": storeroom.requires_reservation_for_issue,
                "requires_supplier_reference_for_receipt": storeroom.requires_supplier_reference_for_receipt,
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


class SqlAlchemyStockReservationRepository(StockReservationRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, reservation: StockReservation) -> None:
        self.session.add(stock_reservation_to_orm(reservation))

    def update(self, reservation: StockReservation) -> None:
        reservation.version = update_with_version_check(
            self.session,
            StockReservationORM,
            reservation.id,
            getattr(reservation, "version", 1),
            {
                "reservation_number": reservation.reservation_number,
                "stock_item_id": reservation.stock_item_id,
                "storeroom_id": reservation.storeroom_id,
                "reserved_qty": reservation.reserved_qty,
                "issued_qty": reservation.issued_qty,
                "remaining_qty": reservation.remaining_qty,
                "uom": reservation.uom,
                "status": reservation.status,
                "need_by_date": reservation.need_by_date,
                "source_reference_type": reservation.source_reference_type or None,
                "source_reference_id": reservation.source_reference_id or None,
                "requested_by_user_id": reservation.requested_by_user_id,
                "requested_by_username": reservation.requested_by_username or None,
                "created_at": reservation.created_at,
                "released_at": reservation.released_at,
                "cancelled_at": reservation.cancelled_at,
                "notes": reservation.notes or None,
            },
            not_found_message="Stock reservation not found.",
            stale_message="Stock reservation was updated by another user.",
        )

    def get(self, reservation_id: str) -> StockReservation | None:
        obj = self.session.get(StockReservationORM, reservation_id)
        return stock_reservation_from_orm(obj) if obj else None

    def get_by_number(self, organization_id: str, reservation_number: str) -> StockReservation | None:
        stmt = select(StockReservationORM).where(
            StockReservationORM.organization_id == organization_id,
            StockReservationORM.reservation_number == reservation_number,
        )
        obj = self.session.execute(stmt).scalars().first()
        return stock_reservation_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[StockReservation]:
        stmt = select(StockReservationORM).where(StockReservationORM.organization_id == organization_id)
        if stock_item_id is not None:
            stmt = stmt.where(StockReservationORM.stock_item_id == stock_item_id)
        if storeroom_id is not None:
            stmt = stmt.where(StockReservationORM.storeroom_id == storeroom_id)
        if status is not None:
            stmt = stmt.where(StockReservationORM.status == status)
        rows = self.session.execute(
            stmt.order_by(StockReservationORM.created_at.desc()).limit(max(1, int(limit or 200)))
        ).scalars().all()
        return [stock_reservation_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyStockBalanceRepository",
    "SqlAlchemyStockReservationRepository",
    "SqlAlchemyStockTransactionRepository",
    "SqlAlchemyStoreroomRepository",
]
