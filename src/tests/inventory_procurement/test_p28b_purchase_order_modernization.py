"""P28B: Purchase Order full modernization -- typed events replace `inventory_purchase_orders_changed`
for every producer, PO's canonical UoW covers create/add-line/update/submit/cancel/send/close/
receiving, and `PurchaseRequisitionLine` gains real optimistic-concurrency protection for the
PO-approval -> Requisition-sourcing mutation (P28A's identified cross-transaction race).

`inventory_purchase_orders_changed` was DELETED from `DomainEvents` (not just left unemitted) --
these tests assert `not hasattr(domain_events, "inventory_purchase_orders_changed")` rather than
connecting a counter to it, since connecting to a deleted attribute is itself an `AttributeError`."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseRequisitionLineStatus,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.procurement import (
    SqlAlchemyPurchaseRequisitionLineRepository,
)
from src.core.platform.common.exceptions import ConcurrencyError
from src.core.platform.domain.master_data.party import PartyType
from src.core.shared.events.domain_events import domain_events
from src.tests.ui_runtime_helpers import login_as


def _procurement_context(services, suffix):
    site = services["site_service"].create_site(
        site_code=f"P28B-{suffix}", name=f"P28B Site {suffix}", currency_code="EUR"
    )
    item = services["inventory_item_service"].create_item(
        item_code=f"P28B-MOTOR-{suffix}",
        name=f"P28B Motor {suffix}",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=f"P28B-MAIN-{suffix}",
        name=f"P28B Main {suffix}",
        site_id=site.id,
        status="ACTIVE",
    )
    supplier = services["party_service"].create_party(
        party_code=f"SUP-P28B-{suffix}",
        party_name=f"P28B Supplier {suffix}",
        party_type=PartyType.SUPPLIER,
    )
    return site, storeroom, item, supplier


def test_legacy_purchase_order_signal_field_is_deleted():
    assert not hasattr(domain_events, "inventory_purchase_orders_changed")


def test_requisition_line_sourcing_rejects_concurrent_stale_update(services, session):
    """P28B SS9/SS10: two independent transactions ("Session A"/"Session B") both read the SAME
    `PurchaseRequisitionLine` before either writes -- exactly the cross-transaction race P28A
    found had no protection at all. Session A commits first; Session B's stale write must be
    rejected deterministically, and the final persisted state must reflect only A's increment
    (no lost update), never both."""
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p28b-buyer-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p28b-buyer-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="P28B concurrency race",
        needed_by_date=date(2026, 5, 1),
    )
    line = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=10,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=100.0,
    )
    assert line.version == 1

    session_b = sessionmaker(bind=session.bind, future=True)()
    try:
        repo_a = services["inventory_procurement_service"]._requisition_line_repo
        repo_b = SqlAlchemyPurchaseRequisitionLineRepository(
            session_b, tenant_context_service=services["tenant_context_service"]
        )

        line_read_by_a = repo_a.get(line.id)
        line_read_by_b = repo_b.get(line.id)
        assert line_read_by_a.version == 1
        assert line_read_by_b.version == 1

        # Transaction A applies its 4-unit sourcing delta and commits first.
        updated_by_a = replace(
            line_read_by_a,
            quantity_sourced=4.0,
            status=PurchaseRequisitionLineStatus.PARTIALLY_SOURCED,
        )
        repo_a.update(updated_by_a)
        session.commit()

        # Transaction B, still holding its now-stale version=1 read, applies its own 4-unit
        # delta computed against the SAME pre-A state -- must be rejected, not silently applied.
        updated_by_b = replace(
            line_read_by_b,
            quantity_sourced=float(line_read_by_b.quantity_sourced or 0.0) + 4.0,
            status=PurchaseRequisitionLineStatus.PARTIALLY_SOURCED,
        )
        with pytest.raises(ConcurrencyError):
            repo_b.update(updated_by_b)
        session_b.rollback()
    finally:
        session_b.close()

    final = repo_a.get(line.id)
    assert final.quantity_sourced == pytest.approx(4.0)
    assert final.version == 2
    assert final.status == PurchaseRequisitionLineStatus.PARTIALLY_SOURCED


def test_update_purchase_order_true_no_op_writes_nothing(services):
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p28b-noop-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, _storeroom, _item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p28b-noop-{suffix}", "StrongPass123")
    purchasing = services["inventory_purchasing_service"]

    po = purchasing.create_purchase_order(
        site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR"
    )
    assert po.version == 1

    result = purchasing.update_purchase_order(
        po.id,
        site_id=po.site_id,
        supplier_party_id=po.supplier_party_id,
        currency_code=po.currency_code,
        supplier_reference=po.supplier_reference,
        notes=po.notes,
    )

    assert result.version == 1, "no-op must not bump version"
    assert result.updated_at == po.updated_at, "no-op must not bump updated_at"

    reloaded = purchasing.get_purchase_order(po.id)
    assert reloaded.version == 1


class _FakeDocumentIntegrationService:
    """P28B discovered a genuine, PRE-EXISTING bug (confirmed via `git show HEAD` to predate this
    phase): `PurchasingService.link_document`/`unlink_document` call `DocumentIntegrationService.
    link_existing_document`/`unlink_existing_document` with a `module=...` kwarg neither method
    accepts (`TypeError`) -- these two methods have never worked in production. Out of scope for
    P28B (unrelated to event/signal modernization); reported, not fixed here. This fake isolates
    the ONE thing this test actually verifies -- that PO's own legacy signal is gone -- from that
    unrelated, pre-existing defect."""

    def __init__(self):
        self.link_calls: list[dict] = []
        self.unlink_calls: list[dict] = []

    def link_existing_document(self, **kwargs):
        self.link_calls.append(kwargs)
        return object()

    def unlink_existing_document(self, **kwargs):
        self.unlink_calls.append(kwargs)


def test_document_link_unlink_do_not_touch_purchase_order(services):
    """P28B SS2: linking/unlinking a document must not mutate PO's own persisted row and must
    have no PO signal to emit any more (the field is deleted) -- P16D's typed
    `DocumentReferenceLinked`/`Unlinked` remains the sole record of the fact."""
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p28b-doc-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, _storeroom, _item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p28b-doc-{suffix}", "StrongPass123")
    purchasing = services["inventory_purchasing_service"]

    po = purchasing.create_purchase_order(
        site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR"
    )

    fake_documents = _FakeDocumentIntegrationService()
    original_document_integration_service = purchasing._document_integration_service
    purchasing._document_integration_service = fake_documents
    try:
        purchasing.link_document(po.id, document_id="fake-document-id")
        purchasing.unlink_document(po.id, document_id="fake-document-id")
    finally:
        purchasing._document_integration_service = original_document_integration_service

    assert len(fake_documents.link_calls) == 1
    assert len(fake_documents.unlink_calls) == 1
    unchanged = purchasing.get_purchase_order(po.id)
    assert unchanged.version == po.version
    assert unchanged.updated_at == po.updated_at


def test_purchase_order_lifecycle_reaches_cancelled(services):
    """P28B SS30/SS33: create/add-line/update/cancel all converge onto typed events + the
    canonical UoW -- no legacy signal exists any more to assert zero on, so this proves the
    lifecycle itself still works end-to-end after the convergence."""
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p28b-life-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p28b-life-{suffix}", "StrongPass123")
    purchasing = services["inventory_purchasing_service"]

    po = purchasing.create_purchase_order(
        site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR"
    )
    purchasing.add_purchase_order_line(
        po.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=3,
        unit_price=50.0,
    )
    po = purchasing.update_purchase_order(po.id, notes="Updated by P28B test")
    po = purchasing.cancel_purchase_order(po.id, note="No longer needed")

    assert po.status.value == "CANCELLED"


def test_post_receipt_reaches_fully_received_with_receipt_signal_unchanged(services):
    """P28B SS11/SS12/SS28: `post_receipt` converges its PO-side consequence onto a typed
    `InventoryPurchaseOrderReceivingAdvanced`, while Receipt/Balance stay on their existing
    legacy Signals unchanged."""
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p28b-rcv-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    auth.register_user(f"p28b-appr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p28b-rcv-{suffix}", "StrongPass123")
    purchasing = services["inventory_purchasing_service"]
    approvals = services["approval_service"]

    po = purchasing.create_purchase_order(
        site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR"
    )
    line = purchasing.add_purchase_order_line(
        po.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=5,
        unit_price=20.0,
    )
    po = purchasing.submit_purchase_order(po.id)

    login_as(services, f"p28b-appr-{suffix}", "StrongPass123")
    approvals.approve_and_apply(po.approval_request_id, note="Approved for P28B receipt test")
    login_as(services, f"p28b-rcv-{suffix}", "StrongPass123")

    receipt_signal_calls: list[str] = []
    receipt_handler = lambda payload: receipt_signal_calls.append(payload)  # noqa: E731
    domain_events.inventory_receipts_changed.connect(receipt_handler)
    try:
        receipt = purchasing.post_receipt(
            po.id,
            receipt_lines=[
                {"purchase_order_line_id": line.id, "quantity_accepted": 5, "quantity_rejected": 0}
            ],
        )
    finally:
        domain_events.inventory_receipts_changed.disconnect(receipt_handler)

    assert receipt_signal_calls == [receipt.id], "Receipt's own legacy signal is untouched"

    resulting_po = purchasing.get_purchase_order(po.id)
    assert resulting_po.status.value == "FULLY_RECEIVED"
