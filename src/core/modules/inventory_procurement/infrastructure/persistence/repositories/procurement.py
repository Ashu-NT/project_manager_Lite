from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.contracts.repositories.procurement import (
    PurchaseOrderLineRepository,
    PurchaseOrderRepository,
    PurchaseRequisitionLineRepository,
    PurchaseRequisitionRepository,
    ReceiptHeaderRepository,
    ReceiptLineRepository,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseOrder,
    PurchaseOrderLine,
    ReceiptHeader,
    ReceiptLine,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.mappers.procurement import (
    purchase_order_from_orm,
    purchase_order_line_from_orm,
    purchase_order_line_to_orm,
    purchase_order_to_orm,
    purchase_requisition_from_orm,
    purchase_requisition_line_from_orm,
    purchase_requisition_line_to_orm,
    purchase_requisition_to_orm,
    receipt_header_from_orm,
    receipt_header_to_orm,
    receipt_line_from_orm,
    receipt_line_to_orm,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.orm.procurement import (
    PurchaseOrderLineORM,
    PurchaseOrderORM,
    PurchaseRequisitionLineORM,
    PurchaseRequisitionORM,
    ReceiptHeaderORM,
    ReceiptLineORM,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories._tenant_scope import (
    InventoryTenantScopedRepositorySupport,
)
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyPurchaseRequisitionRepository(
    PurchaseRequisitionRepository, InventoryTenantScopedRepositorySupport
):
    _repository_label = "Purchase requisition repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, requisition) -> None:
        ctx = self._context(operation_label="add purchase requisition")
        orm = purchase_requisition_to_orm(requisition)
        self._stamp_scope(ctx, orm)
        self.session.add(orm)

    def update(self, requisition) -> None:
        self._require_in_scope(
            PurchaseRequisitionORM,
            requisition.id,
            operation_label="update purchase requisition",
            not_found_message="Purchase requisition not found.",
        )
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
        obj = self._get_in_scope(
            PurchaseRequisitionORM,
            requisition_id,
            operation_label="get purchase requisition",
        )
        return purchase_requisition_from_orm(obj) if obj else None

    def get_by_number(self, organization_id: str, requisition_number: str):
        ctx = self._context(operation_label="get purchase requisition by number")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(PurchaseRequisitionORM).where(
            PurchaseRequisitionORM.organization_id == organization_id,
            PurchaseRequisitionORM.requisition_number == requisition_number,
        )
        stmt = self._apply_scope(stmt, PurchaseRequisitionORM, ctx)
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
        ctx = self._context(operation_label="list purchase requisitions")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(PurchaseRequisitionORM).where(PurchaseRequisitionORM.organization_id == organization_id)
        stmt = self._apply_scope(stmt, PurchaseRequisitionORM, ctx)
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
        obj.quantity_sourced = line.quantity_sourced
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


class SqlAlchemyPurchaseOrderRepository(
    PurchaseOrderRepository, InventoryTenantScopedRepositorySupport
):
    _repository_label = "Purchase order repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, purchase_order: PurchaseOrder) -> None:
        ctx = self._context(operation_label="add purchase order")
        orm = purchase_order_to_orm(purchase_order)
        self._stamp_scope(ctx, orm)
        self.session.add(orm)

    def update(self, purchase_order: PurchaseOrder) -> None:
        self._require_in_scope(
            PurchaseOrderORM,
            purchase_order.id,
            operation_label="update purchase order",
            not_found_message="Purchase order not found.",
        )
        purchase_order.version = update_with_version_check(
            self.session,
            PurchaseOrderORM,
            purchase_order.id,
            getattr(purchase_order, "version", 1),
            {
                "po_number": purchase_order.po_number,
                "site_id": purchase_order.site_id,
                "supplier_party_id": purchase_order.supplier_party_id,
                "status": purchase_order.status,
                "order_date": purchase_order.order_date,
                "expected_delivery_date": purchase_order.expected_delivery_date,
                "currency_code": purchase_order.currency_code or None,
                "approval_request_id": purchase_order.approval_request_id,
                "source_requisition_id": purchase_order.source_requisition_id,
                "supplier_reference": purchase_order.supplier_reference or None,
                "submitted_at": purchase_order.submitted_at,
                "approved_at": purchase_order.approved_at,
                "sent_at": purchase_order.sent_at,
                "closed_at": purchase_order.closed_at,
                "cancelled_at": purchase_order.cancelled_at,
                "notes": purchase_order.notes or None,
                "created_at": purchase_order.created_at,
                "updated_at": purchase_order.updated_at,
            },
            not_found_message="Purchase order not found.",
            stale_message="Purchase order was updated by another user.",
        )

    def get(self, purchase_order_id: str) -> PurchaseOrder | None:
        obj = self._get_in_scope(
            PurchaseOrderORM,
            purchase_order_id,
            operation_label="get purchase order",
        )
        return purchase_order_from_orm(obj) if obj else None

    def get_by_number(self, organization_id: str, po_number: str) -> PurchaseOrder | None:
        ctx = self._context(operation_label="get purchase order by number")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(PurchaseOrderORM).where(
            PurchaseOrderORM.organization_id == organization_id,
            PurchaseOrderORM.po_number == po_number,
        )
        stmt = self._apply_scope(stmt, PurchaseOrderORM, ctx)
        obj = self.session.execute(stmt).scalars().first()
        return purchase_order_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        status: str | None = None,
        site_id: str | None = None,
        supplier_party_id: str | None = None,
        limit: int = 200,
    ) -> list[PurchaseOrder]:
        ctx = self._context(operation_label="list purchase orders")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(PurchaseOrderORM).where(PurchaseOrderORM.organization_id == organization_id)
        stmt = self._apply_scope(stmt, PurchaseOrderORM, ctx)
        if status is not None:
            stmt = stmt.where(PurchaseOrderORM.status == status)
        if site_id is not None:
            stmt = stmt.where(PurchaseOrderORM.site_id == site_id)
        if supplier_party_id is not None:
            stmt = stmt.where(PurchaseOrderORM.supplier_party_id == supplier_party_id)
        rows = self.session.execute(
            stmt.order_by(PurchaseOrderORM.created_at.desc()).limit(max(1, int(limit or 200)))
        ).scalars().all()
        return [purchase_order_from_orm(row) for row in rows]


class SqlAlchemyPurchaseOrderLineRepository(PurchaseOrderLineRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, line: PurchaseOrderLine) -> None:
        self.session.add(purchase_order_line_to_orm(line))

    def update(self, line: PurchaseOrderLine) -> None:
        obj = self.session.get(PurchaseOrderLineORM, line.id)
        if obj is None:
            raise ValueError("Purchase order line not found.")
        obj.line_number = line.line_number
        obj.stock_item_id = line.stock_item_id
        obj.destination_storeroom_id = line.destination_storeroom_id
        obj.description = line.description or None
        obj.quantity_ordered = line.quantity_ordered
        obj.quantity_received = line.quantity_received
        obj.quantity_rejected = line.quantity_rejected
        obj.uom = line.uom
        obj.unit_price = line.unit_price
        obj.expected_delivery_date = line.expected_delivery_date
        obj.source_requisition_line_id = line.source_requisition_line_id
        obj.status = line.status
        obj.notes = line.notes or None

    def get(self, line_id: str) -> PurchaseOrderLine | None:
        obj = self.session.get(PurchaseOrderLineORM, line_id)
        return purchase_order_line_from_orm(obj) if obj else None

    def list_for_purchase_order(self, purchase_order_id: str) -> list[PurchaseOrderLine]:
        stmt = select(PurchaseOrderLineORM).where(PurchaseOrderLineORM.purchase_order_id == purchase_order_id)
        rows = self.session.execute(stmt.order_by(PurchaseOrderLineORM.line_number.asc())).scalars().all()
        return [purchase_order_line_from_orm(row) for row in rows]

    def list_for_requisition_line(self, requisition_line_id: str) -> list[PurchaseOrderLine]:
        stmt = select(PurchaseOrderLineORM).where(PurchaseOrderLineORM.source_requisition_line_id == requisition_line_id)
        rows = self.session.execute(stmt.order_by(PurchaseOrderLineORM.line_number.asc())).scalars().all()
        return [purchase_order_line_from_orm(row) for row in rows]


class SqlAlchemyReceiptHeaderRepository(
    ReceiptHeaderRepository, InventoryTenantScopedRepositorySupport
):
    _repository_label = "Receipt header repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, receipt: ReceiptHeader) -> None:
        ctx = self._context(operation_label="add receipt header")
        orm = receipt_header_to_orm(receipt)
        self._stamp_scope(ctx, orm)
        self.session.add(orm)

    def get(self, receipt_id: str) -> ReceiptHeader | None:
        obj = self._get_in_scope(
            ReceiptHeaderORM,
            receipt_id,
            operation_label="get receipt header",
        )
        return receipt_header_from_orm(obj) if obj else None

    def get_by_number(self, organization_id: str, receipt_number: str) -> ReceiptHeader | None:
        ctx = self._context(operation_label="get receipt header by number")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(ReceiptHeaderORM).where(
            ReceiptHeaderORM.organization_id == organization_id,
            ReceiptHeaderORM.receipt_number == receipt_number,
        )
        stmt = self._apply_scope(stmt, ReceiptHeaderORM, ctx)
        obj = self.session.execute(stmt).scalars().first()
        return receipt_header_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        purchase_order_id: str | None = None,
        limit: int = 200,
    ) -> list[ReceiptHeader]:
        ctx = self._context(operation_label="list receipt headers")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(ReceiptHeaderORM).where(ReceiptHeaderORM.organization_id == organization_id)
        stmt = self._apply_scope(stmt, ReceiptHeaderORM, ctx)
        if purchase_order_id is not None:
            stmt = stmt.where(ReceiptHeaderORM.purchase_order_id == purchase_order_id)
        rows = self.session.execute(
            stmt.order_by(ReceiptHeaderORM.receipt_date.desc()).limit(max(1, int(limit or 200)))
        ).scalars().all()
        return [receipt_header_from_orm(row) for row in rows]


class SqlAlchemyReceiptLineRepository(ReceiptLineRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, line: ReceiptLine) -> None:
        self.session.add(receipt_line_to_orm(line))

    def get(self, line_id: str) -> ReceiptLine | None:
        obj = self.session.get(ReceiptLineORM, line_id)
        return receipt_line_from_orm(obj) if obj else None

    def list_for_receipt(self, receipt_id: str) -> list[ReceiptLine]:
        stmt = select(ReceiptLineORM).where(ReceiptLineORM.receipt_header_id == receipt_id)
        rows = self.session.execute(stmt.order_by(ReceiptLineORM.line_number.asc())).scalars().all()
        return [receipt_line_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyPurchaseOrderLineRepository",
    "SqlAlchemyPurchaseOrderRepository",
    "SqlAlchemyPurchaseRequisitionLineRepository",
    "SqlAlchemyPurchaseRequisitionRepository",
    "SqlAlchemyReceiptHeaderRepository",
    "SqlAlchemyReceiptLineRepository",
]
