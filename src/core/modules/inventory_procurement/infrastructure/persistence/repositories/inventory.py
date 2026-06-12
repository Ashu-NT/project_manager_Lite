from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    CycleCountRepository,
    ReorderPolicyRepository,
    StockBalanceRepository,
    StockReservationRepository,
    StockTransactionRepository,
    StorageLocationRepository,
    StoreroomRepository,
)
from src.core.modules.inventory_procurement.domain.inventory.foundation import (
    CycleCount,
    ReorderPolicy,
    StorageLocation,
)
from src.core.modules.inventory_procurement.domain.inventory.stock import (
    StockBalance,
    StockReservation,
    StockTransaction,
    Storeroom,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.mappers.inventory import (
    cycle_count_from_orm,
    cycle_count_to_orm,
    reorder_policy_from_orm,
    reorder_policy_to_orm,
    stock_balance_from_orm,
    stock_balance_to_orm,
    stock_reservation_from_orm,
    stock_reservation_to_orm,
    stock_transaction_from_orm,
    stock_transaction_to_orm,
    storage_location_from_orm,
    storage_location_to_orm,
    storeroom_from_orm,
    storeroom_to_orm,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.orm.inventory import (
    CycleCountORM,
    ReorderPolicyORM,
    StockBalanceORM,
    StockReservationORM,
    StockTransactionORM,
    StorageLocationORM,
    StoreroomORM,
)
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyStoreroomRepository(StoreroomRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def _get_active_tid(self) -> str | None:
        return self._tenant_context_service.get_active_tenant_id() if self._tenant_context_service else None

    def add(self, storeroom: Storeroom) -> None:
        orm = storeroom_to_orm(storeroom)
        if orm.tenant_id is None:
            orm.tenant_id = self._get_active_tid()
        self.session.add(orm)

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
        if obj is None:
            return None
        _tid = self._get_active_tid()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return storeroom_from_orm(obj)

    def get_by_code(self, organization_id: str, storeroom_code: str) -> Storeroom | None:
        _tid = self._get_active_tid()
        stmt = select(StoreroomORM).where(
            StoreroomORM.organization_id == organization_id,
            StoreroomORM.storeroom_code == storeroom_code,
        )
        if _tid is not None:
            stmt = stmt.where(StoreroomORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalars().first()
        return storeroom_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> list[Storeroom]:
        _tid = self._get_active_tid()
        stmt = select(StoreroomORM).where(StoreroomORM.organization_id == organization_id)
        if _tid is not None:
            stmt = stmt.where(StoreroomORM.tenant_id == _tid)
        if active_only is not None:
            stmt = stmt.where(StoreroomORM.is_active == bool(active_only))
        if site_id is not None:
            stmt = stmt.where(StoreroomORM.site_id == site_id)
        rows = self.session.execute(stmt.order_by(StoreroomORM.name.asc())).scalars().all()
        return [storeroom_from_orm(row) for row in rows]


class SqlAlchemyStockBalanceRepository(StockBalanceRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def _get_active_tid(self) -> str | None:
        return self._tenant_context_service.get_active_tenant_id() if self._tenant_context_service else None

    def add(self, balance: StockBalance) -> None:
        orm = stock_balance_to_orm(balance)
        if orm.tenant_id is None:
            orm.tenant_id = self._get_active_tid()
        self.session.add(orm)

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
        if obj is None:
            return None
        _tid = self._get_active_tid()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return stock_balance_from_orm(obj)

    def get_for_stock_position(
        self,
        organization_id: str,
        stock_item_id: str,
        storeroom_id: str,
    ) -> StockBalance | None:
        _tid = self._get_active_tid()
        stmt = select(StockBalanceORM).where(
            StockBalanceORM.organization_id == organization_id,
            StockBalanceORM.stock_item_id == stock_item_id,
            StockBalanceORM.storeroom_id == storeroom_id,
        )
        if _tid is not None:
            stmt = stmt.where(StockBalanceORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalars().first()
        return stock_balance_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
    ) -> list[StockBalance]:
        _tid = self._get_active_tid()
        stmt = select(StockBalanceORM).where(StockBalanceORM.organization_id == organization_id)
        if _tid is not None:
            stmt = stmt.where(StockBalanceORM.tenant_id == _tid)
        if stock_item_id is not None:
            stmt = stmt.where(StockBalanceORM.stock_item_id == stock_item_id)
        if storeroom_id is not None:
            stmt = stmt.where(StockBalanceORM.storeroom_id == storeroom_id)
        rows = self.session.execute(stmt.order_by(StockBalanceORM.updated_at.desc())).scalars().all()
        return [stock_balance_from_orm(row) for row in rows]


class SqlAlchemyStockTransactionRepository(StockTransactionRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def _get_active_tid(self) -> str | None:
        return self._tenant_context_service.get_active_tenant_id() if self._tenant_context_service else None

    def add(self, transaction: StockTransaction) -> None:
        orm = stock_transaction_to_orm(transaction)
        if orm.tenant_id is None:
            orm.tenant_id = self._get_active_tid()
        self.session.add(orm)

    def get(self, transaction_id: str) -> StockTransaction | None:
        obj = self.session.get(StockTransactionORM, transaction_id)
        if obj is None:
            return None
        _tid = self._get_active_tid()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return stock_transaction_from_orm(obj)

    def get_by_number(self, organization_id: str, transaction_number: str) -> StockTransaction | None:
        _tid = self._get_active_tid()
        stmt = select(StockTransactionORM).where(
            StockTransactionORM.organization_id == organization_id,
            StockTransactionORM.transaction_number == transaction_number,
        )
        if _tid is not None:
            stmt = stmt.where(StockTransactionORM.tenant_id == _tid)
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
        _tid = self._get_active_tid()
        stmt = select(StockTransactionORM).where(StockTransactionORM.organization_id == organization_id)
        if _tid is not None:
            stmt = stmt.where(StockTransactionORM.tenant_id == _tid)
        if stock_item_id is not None:
            stmt = stmt.where(StockTransactionORM.stock_item_id == stock_item_id)
        if storeroom_id is not None:
            stmt = stmt.where(StockTransactionORM.storeroom_id == storeroom_id)
        rows = self.session.execute(
            stmt.order_by(StockTransactionORM.transaction_at.desc()).limit(max(1, int(limit or 200)))
        ).scalars().all()
        return [stock_transaction_from_orm(row) for row in rows]


class SqlAlchemyStockReservationRepository(StockReservationRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def _get_active_tid(self) -> str | None:
        return self._tenant_context_service.get_active_tenant_id() if self._tenant_context_service else None

    def add(self, reservation: StockReservation) -> None:
        orm = stock_reservation_to_orm(reservation)
        if orm.tenant_id is None:
            orm.tenant_id = self._get_active_tid()
        self.session.add(orm)

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
        if obj is None:
            return None
        _tid = self._get_active_tid()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return stock_reservation_from_orm(obj)

    def get_by_number(self, organization_id: str, reservation_number: str) -> StockReservation | None:
        _tid = self._get_active_tid()
        stmt = select(StockReservationORM).where(
            StockReservationORM.organization_id == organization_id,
            StockReservationORM.reservation_number == reservation_number,
        )
        if _tid is not None:
            stmt = stmt.where(StockReservationORM.tenant_id == _tid)
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
        _tid = self._get_active_tid()
        stmt = select(StockReservationORM).where(StockReservationORM.organization_id == organization_id)
        if _tid is not None:
            stmt = stmt.where(StockReservationORM.tenant_id == _tid)
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


class SqlAlchemyStorageLocationRepository(StorageLocationRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, location: StorageLocation) -> None:
        self.session.add(storage_location_to_orm(location))

    def update(self, location: StorageLocation) -> None:
        location.version = update_with_version_check(
            self.session,
            StorageLocationORM,
            location.id,
            getattr(location, "version", 1),
            {
                "storeroom_id": location.storeroom_id,
                "location_code": location.location_code,
                "name": location.name,
                "parent_location_id": location.parent_location_id,
                "location_type": location.location_type,
                "is_active": location.is_active,
                "is_quarantine": location.is_quarantine,
                "allows_issue": location.allows_issue,
                "allows_putaway": location.allows_putaway,
                "notes": location.notes or None,
                "created_at": location.created_at,
                "updated_at": location.updated_at,
            },
            not_found_message="Storage location not found.",
            stale_message="Storage location was updated by another user.",
        )

    def get(self, location_id: str) -> StorageLocation | None:
        obj = self.session.get(StorageLocationORM, location_id)
        return storage_location_from_orm(obj) if obj else None

    def get_by_code(
        self,
        organization_id: str,
        storeroom_id: str,
        location_code: str,
    ) -> StorageLocation | None:
        stmt = select(StorageLocationORM).where(
            StorageLocationORM.organization_id == organization_id,
            StorageLocationORM.storeroom_id == storeroom_id,
            StorageLocationORM.location_code == location_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return storage_location_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        storeroom_id: str | None = None,
        parent_location_id: str | None = None,
        active_only: bool | None = None,
    ) -> list[StorageLocation]:
        stmt = select(StorageLocationORM).where(
            StorageLocationORM.organization_id == organization_id
        )
        if storeroom_id is not None:
            stmt = stmt.where(StorageLocationORM.storeroom_id == storeroom_id)
        if parent_location_id is not None:
            stmt = stmt.where(StorageLocationORM.parent_location_id == parent_location_id)
        if active_only is not None:
            stmt = stmt.where(StorageLocationORM.is_active == bool(active_only))
        rows = self.session.execute(
            stmt.order_by(
                StorageLocationORM.storeroom_id.asc(),
                StorageLocationORM.location_code.asc(),
            )
        ).scalars().all()
        return [storage_location_from_orm(row) for row in rows]


class SqlAlchemyReorderPolicyRepository(ReorderPolicyRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, policy: ReorderPolicy) -> None:
        self.session.add(reorder_policy_to_orm(policy))

    def update(self, policy: ReorderPolicy) -> None:
        policy.version = update_with_version_check(
            self.session,
            ReorderPolicyORM,
            policy.id,
            getattr(policy, "version", 1),
            {
                "stock_item_id": policy.stock_item_id,
                "storeroom_id": policy.storeroom_id,
                "location_id": policy.location_id,
                "policy_name": policy.policy_name or None,
                "is_active": policy.is_active,
                "min_qty": policy.min_qty,
                "max_qty": policy.max_qty,
                "reorder_point": policy.reorder_point,
                "reorder_qty": policy.reorder_qty,
                "economic_order_qty": policy.economic_order_qty,
                "lead_time_days": policy.lead_time_days,
                "review_period_days": policy.review_period_days,
                "preferred_supplier_party_id": policy.preferred_supplier_party_id,
                "created_at": policy.created_at,
                "updated_at": policy.updated_at,
            },
            not_found_message="Reorder policy not found.",
            stale_message="Reorder policy was updated by another user.",
        )

    def get(self, policy_id: str) -> ReorderPolicy | None:
        obj = self.session.get(ReorderPolicyORM, policy_id)
        return reorder_policy_from_orm(obj) if obj else None

    def get_for_scope(
        self,
        organization_id: str,
        stock_item_id: str,
        storeroom_id: str,
        location_id: str | None,
    ) -> ReorderPolicy | None:
        stmt = select(ReorderPolicyORM).where(
            ReorderPolicyORM.organization_id == organization_id,
            ReorderPolicyORM.stock_item_id == stock_item_id,
            ReorderPolicyORM.storeroom_id == storeroom_id,
        )
        if location_id is None:
            stmt = stmt.where(ReorderPolicyORM.location_id.is_(None))
        else:
            stmt = stmt.where(ReorderPolicyORM.location_id == location_id)
        obj = self.session.execute(stmt).scalars().first()
        return reorder_policy_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        location_id: str | None = None,
        active_only: bool | None = None,
    ) -> list[ReorderPolicy]:
        stmt = select(ReorderPolicyORM).where(
            ReorderPolicyORM.organization_id == organization_id
        )
        if stock_item_id is not None:
            stmt = stmt.where(ReorderPolicyORM.stock_item_id == stock_item_id)
        if storeroom_id is not None:
            stmt = stmt.where(ReorderPolicyORM.storeroom_id == storeroom_id)
        if location_id is not None:
            stmt = stmt.where(ReorderPolicyORM.location_id == location_id)
        if active_only is not None:
            stmt = stmt.where(ReorderPolicyORM.is_active == bool(active_only))
        rows = self.session.execute(
            stmt.order_by(
                ReorderPolicyORM.stock_item_id.asc(),
                ReorderPolicyORM.storeroom_id.asc(),
                ReorderPolicyORM.policy_name.asc(),
            )
        ).scalars().all()
        return [reorder_policy_from_orm(row) for row in rows]


class SqlAlchemyCycleCountRepository(CycleCountRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, cycle_count: CycleCount) -> None:
        self.session.add(cycle_count_to_orm(cycle_count))

    def update(self, cycle_count: CycleCount) -> None:
        cycle_count.version = update_with_version_check(
            self.session,
            CycleCountORM,
            cycle_count.id,
            getattr(cycle_count, "version", 1),
            {
                "cycle_count_number": cycle_count.cycle_count_number,
                "stock_item_id": cycle_count.stock_item_id,
                "storeroom_id": cycle_count.storeroom_id,
                "location_id": cycle_count.location_id,
                "scheduled_count_date": cycle_count.scheduled_count_date,
                "status": cycle_count.status,
                "expected_qty": cycle_count.expected_qty,
                "counted_qty": cycle_count.counted_qty,
                "variance_qty": cycle_count.variance_qty,
                "counted_by_user_id": cycle_count.counted_by_user_id,
                "counted_by_username": cycle_count.counted_by_username or None,
                "created_at": cycle_count.created_at,
                "completed_at": cycle_count.completed_at,
                "notes": cycle_count.notes or None,
            },
            not_found_message="Cycle count not found.",
            stale_message="Cycle count was updated by another user.",
        )

    def get(self, cycle_count_id: str) -> CycleCount | None:
        obj = self.session.get(CycleCountORM, cycle_count_id)
        return cycle_count_from_orm(obj) if obj else None

    def get_by_number(
        self,
        organization_id: str,
        cycle_count_number: str,
    ) -> CycleCount | None:
        stmt = select(CycleCountORM).where(
            CycleCountORM.organization_id == organization_id,
            CycleCountORM.cycle_count_number == cycle_count_number,
        )
        obj = self.session.execute(stmt).scalars().first()
        return cycle_count_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        location_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[CycleCount]:
        stmt = select(CycleCountORM).where(CycleCountORM.organization_id == organization_id)
        if stock_item_id is not None:
            stmt = stmt.where(CycleCountORM.stock_item_id == stock_item_id)
        if storeroom_id is not None:
            stmt = stmt.where(CycleCountORM.storeroom_id == storeroom_id)
        if location_id is not None:
            stmt = stmt.where(CycleCountORM.location_id == location_id)
        if status is not None:
            stmt = stmt.where(CycleCountORM.status == status)
        rows = self.session.execute(
            stmt.order_by(CycleCountORM.created_at.desc()).limit(max(1, int(limit or 200)))
        ).scalars().all()
        return [cycle_count_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyCycleCountRepository",
    "SqlAlchemyReorderPolicyRepository",
    "SqlAlchemyStockBalanceRepository",
    "SqlAlchemyStockReservationRepository",
    "SqlAlchemyStockTransactionRepository",
    "SqlAlchemyStorageLocationRepository",
    "SqlAlchemyStoreroomRepository",
]
