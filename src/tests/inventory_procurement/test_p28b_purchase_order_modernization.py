from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from src.core.modules.inventory_procurement.application.procurement.event_handlers.view_invalidation import (
    PROCUREMENT_CATEGORY,
    REQUISITION_DETAIL_SCOPE_CODE,
    REQUISITION_LIST_SCOPE_CODE,
    build_requisition_view_invalidation_handler,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseRequisitionLineStatus,
)
from src.core.modules.inventory_procurement.domain.procurement.requisition_events import (
    InventoryRequisitionSourcingAdvanced,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.procurement import (
    SqlAlchemyPurchaseRequisitionLineRepository,
)
from src.core.platform.common.exceptions import ConcurrencyError
from src.core.platform.domain.master_data.party import PartyType
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.events.view_invalidation import OrganizationScope, ResourceScope
from src.tests.ui_runtime_helpers import login_as


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def _spy_hints(services):
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(_AnyOrgFilter(), lambda hint: hints.append(hint))
    return hints


def _requisition_hints(hints):
    return [
        h
        for h in hints
        if h.category == PROCUREMENT_CATEGORY
        and h.scope_code in (REQUISITION_LIST_SCOPE_CODE, REQUISITION_DETAIL_SCOPE_CODE)
    ]


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

    def __init__(self):
        self.link_calls: list[dict] = []
        self.unlink_calls: list[dict] = []

    def link_existing_document(self, **kwargs):
        self.link_calls.append(kwargs)
        return object()

    def unlink_existing_document(self, **kwargs):
        self.unlink_calls.append(kwargs)


def test_document_link_unlink_do_not_touch_purchase_order(services):
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


# ---------------------------------------------------------------------------
# P28B-FIX: InventoryRequisitionSourcingAdvanced -> requisition_list/requisition_detail
# ViewInvalidation (handler-level mapping/dedupe, unit-level, no DB)
# ---------------------------------------------------------------------------


def _sourcing_event(requisition_id, purchase_order_id="po-1", resulting_status="PARTIALLY_SOURCED"):
    return InventoryRequisitionSourcingAdvanced(
        tenant_id="t1",
        organization_id="o1",
        requisition_id=requisition_id,
        purchase_order_id=purchase_order_id,
        resulting_status=resulting_status,
        occurred_at=datetime.now(timezone.utc),
    )


def test_requisition_sourcing_event_maps_to_list_and_detail_targets():
    channel = _fake_channel()
    handler = build_requisition_view_invalidation_handler(channel)

    handler(_sourcing_event("req-a"), DomainEventContext(correlation_id="tx"))

    assert len(channel.notified) == 2
    list_hint, detail_hint = channel.notified
    assert list_hint.scope_code == REQUISITION_LIST_SCOPE_CODE
    assert isinstance(list_hint.scope, OrganizationScope)
    assert detail_hint.scope_code == REQUISITION_DETAIL_SCOPE_CODE
    assert isinstance(detail_hint.scope, ResourceScope)
    assert detail_hint.scope.entity_type == "purchase_requisition"
    assert detail_hint.scope.entity_id == "req-a"
    assert detail_hint.entity_id == "req-a"


def test_requisition_sourcing_multiple_lines_of_same_requisition_dedupe_to_one_pair_of_hints():
    channel = _fake_channel()
    handler = build_requisition_view_invalidation_handler(channel)

    handler(_sourcing_event("req-a", resulting_status="PARTIALLY_SOURCED"), DomainEventContext(correlation_id="tx"))
    handler(_sourcing_event("req-a", resulting_status="FULLY_SOURCED"), DomainEventContext(correlation_id="tx"))

    assert len(channel.notified) == 2, "same requisition, same transaction: one list hint + one detail hint"


def test_requisition_sourcing_two_requisitions_one_list_hint_two_detail_hints():
    """P28B-FIX §3: one PO approval touching Requisition A and Requisition B must produce ONE
    organization-list hint (not per-requisition_id) plus one exact detail hint per requisition."""
    channel = _fake_channel()
    handler = build_requisition_view_invalidation_handler(channel)

    handler(_sourcing_event("req-a"), DomainEventContext(correlation_id="tx"))
    handler(_sourcing_event("req-b"), DomainEventContext(correlation_id="tx"))

    list_hints = [h for h in channel.notified if h.scope_code == REQUISITION_LIST_SCOPE_CODE]
    detail_hints = [h for h in channel.notified if h.scope_code == REQUISITION_DETAIL_SCOPE_CODE]
    assert len(list_hints) == 1, "org-list dedupe key must not include requisition_id"
    assert len(detail_hints) == 2
    assert {h.scope.entity_id for h in detail_hints} == {"req-a", "req-b"}


def test_requisition_sourcing_new_transaction_is_not_deduped_with_previous():
    channel = _fake_channel()
    handler = build_requisition_view_invalidation_handler(channel)

    handler(_sourcing_event("req-a"), DomainEventContext(correlation_id="tx-1"))
    handler(_sourcing_event("req-a"), DomainEventContext(correlation_id="tx-2"))

    assert len(channel.notified) == 4, "a new correlation_id must never coalesce with a prior transaction"


def test_requisition_sourcing_different_organization_is_a_separate_target():
    channel = _fake_channel()
    handler = build_requisition_view_invalidation_handler(channel)

    handler(_sourcing_event("req-a"), DomainEventContext(correlation_id="tx"))
    other_org_event = InventoryRequisitionSourcingAdvanced(
        tenant_id="t1",
        organization_id="o2",
        requisition_id="req-a",
        purchase_order_id="po-1",
        resulting_status="PARTIALLY_SOURCED",
        occurred_at=datetime.now(timezone.utc),
    )
    handler(other_org_event, DomainEventContext(correlation_id="tx"))

    assert len(channel.notified) == 4, "a different organization is never coalesced away, even same requisition_id"


# ---------------------------------------------------------------------------
# P28B-FIX: production wiring -- PO approval -> real Requisition sourcing DomainEvent ->
# real ViewInvalidation channel (not just the handler in isolation)
# ---------------------------------------------------------------------------


def test_po_approval_sourcing_requisition_produces_requisition_list_and_detail_hints_end_to_end(
    services,
):
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p28bfix-buyer-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    auth.register_user(f"p28bfix-appr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p28bfix-buyer-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]
    purchasing = services["inventory_purchasing_service"]
    approvals = services["approval_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="P28B-FIX end-to-end",
        needed_by_date=date(2026, 5, 1),
    )
    requisition_line = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=5,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=100.0,
    )
    requisition = procurement.submit_requisition(requisition.id)

    login_as(services, f"p28bfix-appr-{suffix}", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved requisition")

    login_as(services, f"p28bfix-buyer-{suffix}", "StrongPass123")
    po = purchasing.create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
        source_requisition_id=requisition.id,
    )
    purchasing.add_purchase_order_line(
        po.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=5,
        unit_price=100.0,
        source_requisition_line_id=requisition_line.id,
    )
    po = purchasing.submit_purchase_order(po.id)

    hints = _spy_hints(services)

    login_as(services, f"p28bfix-appr-{suffix}", "StrongPass123")
    approvals.approve_and_apply(po.approval_request_id, note="Approved PO, sources requisition")

    req_hints = _requisition_hints(hints)
    assert len(req_hints) == 2
    assert {h.scope_code for h in req_hints} == {REQUISITION_LIST_SCOPE_CODE, REQUISITION_DETAIL_SCOPE_CODE}
    detail = next(h for h in req_hints if h.scope_code == REQUISITION_DETAIL_SCOPE_CODE)
    assert detail.scope.entity_id == requisition.id

    assert not hasattr(domain_events, "inventory_requisitions_changed"), (
        "P29 deleted this field entirely once Requisition's own remaining 7 producers converged "
        "too -- at P28B time it was still present (only the PO-triggered emission was removed); "
        "this assertion was updated by P29, superseding P28B's own version of this test"
    )


def test_concurrency_losing_po_approval_produces_zero_requisition_invalidation(
    services, monkeypatch
):
    """P28B-FIX §7 + P28B SS9/SS10: a PO approval that loses the optimistic-concurrency race on
    `PurchaseRequisitionLine` must roll back entirely and reach the ViewInvalidation channel with
    NOTHING -- not a partial hint, not a stale-state hint."""
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p28bfix-race-buyer-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    auth.register_user(f"p28bfix-race-appr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p28bfix-race-buyer-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]
    purchasing = services["inventory_purchasing_service"]
    approvals = services["approval_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="P28B-FIX concurrency race",
        needed_by_date=date(2026, 5, 1),
    )
    requisition_line = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=10,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=100.0,
    )
    requisition = procurement.submit_requisition(requisition.id)

    login_as(services, f"p28bfix-race-appr-{suffix}", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved requisition")

    login_as(services, f"p28bfix-race-buyer-{suffix}", "StrongPass123")
    po = purchasing.create_purchase_order(
        site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR",
        source_requisition_id=requisition.id,
    )
    purchasing.add_purchase_order_line(
        po.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=4,
        unit_price=100.0,
        source_requisition_line_id=requisition_line.id,
    )
    po = purchasing.submit_purchase_order(po.id)

    # Simulate this approval racing against a concurrent writer that already advanced the row's
    # version by the time this transaction tries to persist its own update -- the conditional
    # UPDATE must affect zero rows and raise ConcurrencyError, exactly as it would for a genuine
    # concurrent commit (test_requisition_line_sourcing_rejects_concurrent_stale_update proves the
    # repository mechanism itself; this proves the ApprovalService-level consequence: rollback,
    # zero postcommit events).
    original_update = SqlAlchemyPurchaseRequisitionLineRepository.update

    def _stale_update(self, line):
        stale = replace(line, version=line.version + 99)  # force a version mismatch
        return original_update(self, stale)

    monkeypatch.setattr(SqlAlchemyPurchaseRequisitionLineRepository, "update", _stale_update)

    hints = _spy_hints(services)

    login_as(services, f"p28bfix-race-appr-{suffix}", "StrongPass123")
    with pytest.raises(ConcurrencyError):
        approvals.approve_and_apply(po.approval_request_id, note="Loses the concurrency race")

    assert _requisition_hints(hints) == [], "a rolled-back approval must publish zero ViewInvalidation hints"

    unchanged_line = purchasing._requisition_line_repo.get(requisition_line.id)
    assert unchanged_line.quantity_sourced in (0, 0.0, None), "the losing transaction's mutation must not persist"

    login_as(services, f"p28bfix-race-buyer-{suffix}", "StrongPass123")
    unchanged_po = purchasing.get_purchase_order(po.id)
    assert unchanged_po.status.value == "SUBMITTED", "the PO's own approval must roll back together with the sourcing mutation"


# ---------------------------------------------------------------------------
# P28B-FIX: UI consumer wiring -- Procurement reacts, Dashboard deliberately does not
# ---------------------------------------------------------------------------


def test_procurement_workspace_requisition_sourcing_stale_triggers_full_refresh(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.procurementWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    catalog._procurement_requisition_view_invalidation_adapter.requisitionListStale.emit("req-1")
    assert refresh_calls == ["refresh"]

    catalog._procurement_requisition_view_invalidation_adapter.requisitionDetailStale.emit("req-1")
    assert refresh_calls == ["refresh", "refresh"]


def test_dashboard_workspace_requisition_pending_approval_stale_triggers_full_refresh(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.dashboardWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    catalog._dashboard_requisition_view_invalidation_adapter.requisitionPendingApprovalStale.emit("req-1")
    assert refresh_calls == ["refresh"]

    # The broad list/detail signals must NOT be wired to Dashboard's refresh at all.
    catalog._dashboard_requisition_view_invalidation_adapter.requisitionListStale.emit("req-1")
    catalog._dashboard_requisition_view_invalidation_adapter.requisitionDetailStale.emit("req-1")
    assert refresh_calls == ["refresh"], "Dashboard must not react to requisition_list/detail directly"
