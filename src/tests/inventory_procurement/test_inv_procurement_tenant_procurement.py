from __future__ import annotations

import pytest

from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseOrderLine,
    PurchaseRequisitionLine,
    ReceiptLine,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.procurement import (
    SqlAlchemyPurchaseOrderLineRepository,
    SqlAlchemyPurchaseOrderRepository,
    SqlAlchemyPurchaseRequisitionLineRepository,
    SqlAlchemyPurchaseRequisitionRepository,
    SqlAlchemyReceiptHeaderRepository,
    SqlAlchemyReceiptLineRepository,
)
from src.core.platform.common.exceptions import NotFoundError
from src.tests.inventory_procurement._procurement_seed_helpers import _seed_procurement_scope_rows


def _inventory_repo(repo_factory, services):
    return repo_factory(
        services["session"],
        tenant_context_service=services["tenant_context_service"],
    )


def test_procurement_repositories_hide_cross_organization_rows(services) -> None:
    seeded = _seed_procurement_scope_rows(services)

    requisition_repo = _inventory_repo(SqlAlchemyPurchaseRequisitionRepository, services)
    requisition_line_repo = _inventory_repo(SqlAlchemyPurchaseRequisitionLineRepository, services)
    purchase_order_repo = _inventory_repo(SqlAlchemyPurchaseOrderRepository, services)
    purchase_order_line_repo = _inventory_repo(SqlAlchemyPurchaseOrderLineRepository, services)
    receipt_repo = _inventory_repo(SqlAlchemyReceiptHeaderRepository, services)
    receipt_line_repo = _inventory_repo(SqlAlchemyReceiptLineRepository, services)

    assert requisition_repo.get(seeded["other_requisition_id"]) is None
    assert requisition_line_repo.get(seeded["other_requisition_line_id"]) is None
    assert purchase_order_repo.get(seeded["other_purchase_order_id"]) is None
    assert purchase_order_line_repo.get(seeded["other_purchase_order_line_id"]) is None
    assert receipt_repo.get(seeded["other_receipt_id"]) is None
    assert receipt_line_repo.get(seeded["other_receipt_line_id"]) is None

    assert (
        requisition_repo.get_by_number(
            seeded["other_org_id"],
            seeded["current_requisition_number"],
        )
        is None
    )
    assert (
        purchase_order_repo.get_by_number(
            seeded["other_org_id"],
            seeded["current_purchase_order_number"],
        )
        is None
    )
    assert (
        receipt_repo.get_by_number(
            seeded["other_org_id"],
            seeded["current_receipt_number"],
        )
        is None
    )

    current_requisition_ids = {
        row.id
        for row in requisition_repo.list_for_organization(seeded["current_org_id"], limit=200)
    }
    current_requisition_line_ids = {
        row.id
        for row in requisition_line_repo.list_for_requisition(seeded["current_requisition_id"])
    }
    current_purchase_order_ids = {
        row.id
        for row in purchase_order_repo.list_for_organization(seeded["current_org_id"], limit=200)
    }
    current_purchase_order_line_ids = {
        row.id
        for row in purchase_order_line_repo.list_for_purchase_order(seeded["current_purchase_order_id"])
    }
    current_receipt_ids = {
        row.id
        for row in receipt_repo.list_for_organization(seeded["current_org_id"], limit=200)
    }
    current_receipt_line_ids = {
        row.id
        for row in receipt_line_repo.list_for_receipt(seeded["current_receipt_id"])
    }
    sourced_purchase_order_line_ids = {
        row.id
        for row in purchase_order_line_repo.list_for_requisition_line(seeded["current_requisition_line_id"])
    }

    assert requisition_repo.list_for_organization(seeded["other_org_id"], limit=200) == []
    assert requisition_line_repo.list_for_requisition(seeded["other_requisition_id"]) == []
    assert purchase_order_repo.list_for_organization(seeded["other_org_id"], limit=200) == []
    assert purchase_order_line_repo.list_for_purchase_order(seeded["other_purchase_order_id"]) == []
    assert (
        purchase_order_line_repo.list_for_requisition_line(seeded["other_requisition_line_id"]) == []
    )
    assert receipt_repo.list_for_organization(seeded["other_org_id"], limit=200) == []
    assert receipt_line_repo.list_for_receipt(seeded["other_receipt_id"]) == []

    assert seeded["current_requisition_id"] in current_requisition_ids
    assert seeded["other_requisition_id"] not in current_requisition_ids
    assert seeded["current_requisition_line_id"] in current_requisition_line_ids
    assert seeded["other_requisition_line_id"] not in current_requisition_line_ids
    assert seeded["current_purchase_order_id"] in current_purchase_order_ids
    assert seeded["other_purchase_order_id"] not in current_purchase_order_ids
    assert seeded["current_purchase_order_line_id"] in current_purchase_order_line_ids
    assert seeded["other_purchase_order_line_id"] not in current_purchase_order_line_ids
    assert seeded["current_receipt_id"] in current_receipt_ids
    assert seeded["other_receipt_id"] not in current_receipt_ids
    assert seeded["current_receipt_line_id"] in current_receipt_line_ids
    assert seeded["other_receipt_line_id"] not in current_receipt_line_ids
    assert seeded["current_purchase_order_line_id"] in sourced_purchase_order_line_ids
    assert seeded["other_purchase_order_line_id"] not in sourced_purchase_order_line_ids


def test_procurement_line_repositories_reject_foreign_parent_scope(services) -> None:
    seeded = _seed_procurement_scope_rows(services)

    requisition_line_repo = _inventory_repo(SqlAlchemyPurchaseRequisitionLineRepository, services)
    purchase_order_line_repo = _inventory_repo(SqlAlchemyPurchaseOrderLineRepository, services)
    receipt_line_repo = _inventory_repo(SqlAlchemyReceiptLineRepository, services)

    with pytest.raises(NotFoundError, match="Purchase requisition not found"):
        requisition_line_repo.add(
            PurchaseRequisitionLine.create(
                purchase_requisition_id=seeded["other_requisition_id"],
                line_number=2,
                stock_item_id=seeded["current_item_id"],
                quantity_requested=1.0,
                uom="EA",
            )
        )

    with pytest.raises(ValueError, match="Purchase requisition line not found"):
        purchase_order_line_repo.add(
            PurchaseOrderLine.create(
                purchase_order_id=seeded["current_purchase_order_id"],
                line_number=2,
                stock_item_id=seeded["current_item_id"],
                destination_storeroom_id=seeded["current_storeroom_id"],
                quantity_ordered=1.0,
                uom="EA",
                source_requisition_line_id=seeded["other_requisition_line_id"],
            )
        )

    with pytest.raises(ValueError, match="Purchase order line not found"):
        receipt_line_repo.add(
            ReceiptLine.create(
                receipt_header_id=seeded["current_receipt_id"],
                purchase_order_line_id=seeded["other_purchase_order_line_id"],
                line_number=2,
                stock_item_id=seeded["current_item_id"],
                storeroom_id=seeded["current_storeroom_id"],
                quantity_accepted=1.0,
                uom="EA",
            )
        )
