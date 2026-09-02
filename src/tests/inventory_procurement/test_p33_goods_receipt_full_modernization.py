

from __future__ import annotations

import dataclasses
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from src.application.runtime import build_desktop_api_registry
from src.core.modules.inventory_procurement.application.procurement.event_handlers.view_invalidation import (
    PROCUREMENT_CATEGORY,
    RECEIPT_LIST_SCOPE_CODE,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.procurement import (
    SqlAlchemyPurchaseOrderLineRepository,
)
from src.core.platform.domain.master_data.party import PartyType
from src.core.shared.events.domain_events import DomainEvents, domain_events
from src.ui_qml.modules.inventory_procurement.context import (
    InventoryProcurementWorkspaceCatalog,
)
from src.tests.ui_runtime_helpers import login_as


def _procurement_context(services, suffix):
    site = services["site_service"].create_site(
        site_code=f"P33-{suffix}", name=f"P33 Site {suffix}", currency_code="EUR"
    )
    item = services["inventory_item_service"].create_item(
        item_code=f"P33-ITEM-{suffix}",
        name=f"P33 Item {suffix}",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=f"P33-ST-{suffix}", name=f"P33 Storeroom {suffix}", site_id=site.id, status="ACTIVE"
    )
    supplier = services["party_service"].create_party(
        party_code=f"SUP-P33-{suffix}", party_name=f"P33 Supplier {suffix}", party_type=PartyType.SUPPLIER
    )
    return site, storeroom, item, supplier


def _pm_catalog(services) -> InventoryProcurementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)


def _spy_hints(services):
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(_AnyOrgFilter(), lambda hint: hints.append(hint))
    return hints


def _receipt_hints(hints):
    return [h for h in hints if h.category == PROCUREMENT_CATEGORY and h.scope_code == RECEIPT_LIST_SCOPE_CODE]


def _approved_po_ready_for_receipt(services, *, manager_username, approver_username, suffix, quantity_ordered=10):
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, manager_username, "StrongPass123")
    purchasing = services["inventory_purchasing_service"]
    po = purchasing.create_purchase_order(site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR")
    line = purchasing.add_purchase_order_line(
        po.id, stock_item_id=item.id, destination_storeroom_id=storeroom.id,
        quantity_ordered=quantity_ordered, unit_price=10.0,
    )
    po = purchasing.submit_purchase_order(po.id)
    login_as(services, approver_username, "StrongPass123")
    services["approval_service"].approve_and_apply(po.approval_request_id, note="Approved")
    login_as(services, manager_username, "StrongPass123")
    return site, storeroom, item, supplier, po, line


def test_legacy_receipt_signal_field_is_deleted():
    assert not hasattr(domain_events, "inventory_receipts_changed")


def test_zero_inventory_legacy_signal_fields_remain():
    """P33 §39/§43: after Receipt's own deletion, Inventory/Procurement has ZERO remaining legacy
    Signal fields -- the entire capability's legacy surface (Item/Category, Storeroom/Location,
    Reorder Policy, Purchase Order, Requisition, Reservation, Stock Balance, Cycle Count, Receipt)
    is retired."""
    names = {f.name for f in dataclasses.fields(DomainEvents)}
    inventory_names = {n for n in names if n.startswith("inventory_")}
    assert inventory_names == set(), inventory_names


# ---------------------------------------------------------------------------
# One receipt -> exactly one InventoryReceiptPosted (ViewInvalidation-observable)
# ---------------------------------------------------------------------------


def test_post_receipt_produces_exactly_one_receipt_hint_plus_po_and_balance_hints(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p33-rcv-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p33-appr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier, po, line = _approved_po_ready_for_receipt(
        services, manager_username=f"p33-rcv-{suffix}", approver_username=f"p33-appr-{suffix}", suffix=suffix,
    )
    purchasing = services["inventory_purchasing_service"]

    hints = _spy_hints(services)
    receipt = purchasing.post_receipt(
        po.id, receipt_lines=[{"purchase_order_line_id": line.id, "quantity_accepted": 5, "quantity_rejected": 0}],
    )

    receipt_hints = _receipt_hints(hints)
    assert len(receipt_hints) == 1, "one receipt posting must produce exactly one receipt_list hint"
    assert receipt_hints[0].entity_id == receipt.id

    po_hints = [h for h in hints if h.category == PROCUREMENT_CATEGORY and h.scope_code == "purchase_order_list"]
    assert po_hints, "PO receiving consequence (InventoryPurchaseOrderReceivingAdvanced) must still fire"
    balance_hints = [h for h in hints if h.category == "inventory_balance"]
    assert balance_hints, "Balance facts (StockOnHandQuantityChanged/StockOnOrderQuantityChanged) must still fire"

    resulting_po = purchasing.get_purchase_order(po.id)
    assert resulting_po.status.value == "PARTIALLY_RECEIVED"


def test_partial_receipt_exact_deltas(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p33-part-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p33-partappr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier, po, line = _approved_po_ready_for_receipt(
        services, manager_username=f"p33-part-{suffix}", approver_username=f"p33-partappr-{suffix}",
        suffix=suffix, quantity_ordered=10,
    )
    purchasing = services["inventory_purchasing_service"]
    balance_before = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    on_order_before = float(balance_before.on_order_qty) if balance_before else 0.0

    purchasing.post_receipt(
        po.id, receipt_lines=[{"purchase_order_line_id": line.id, "quantity_accepted": 4, "quantity_rejected": 0}],
    )

    resulting_po = purchasing.get_purchase_order(po.id)
    assert resulting_po.status.value == "PARTIALLY_RECEIVED"
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.on_hand_qty == 4.0
    assert balance.on_order_qty == on_order_before - 4.0
    transactions = services["inventory_stock_service"].list_transactions(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert any(t.reference_type == "inventory_receipt" and t.quantity == 4.0 for t in transactions)


def test_full_receipt_completes_remaining_quantity(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p33-full-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p33-fullappr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier, po, line = _approved_po_ready_for_receipt(
        services, manager_username=f"p33-full-{suffix}", approver_username=f"p33-fullappr-{suffix}",
        suffix=suffix, quantity_ordered=10,
    )
    purchasing = services["inventory_purchasing_service"]
    purchasing.post_receipt(
        po.id, receipt_lines=[{"purchase_order_line_id": line.id, "quantity_accepted": 4, "quantity_rejected": 0}],
    )

    hints = _spy_hints(services)
    purchasing.post_receipt(
        po.id, receipt_lines=[{"purchase_order_line_id": line.id, "quantity_accepted": 6, "quantity_rejected": 0}],
    )
    receipt_hints = _receipt_hints(hints)
    assert len(receipt_hints) == 1, "the second, completing receipt must also produce exactly one receipt hint"

    resulting_po = purchasing.get_purchase_order(po.id)
    assert resulting_po.status.value == "FULLY_RECEIVED"
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance.on_hand_qty == 10.0
    assert balance.on_order_qty == 0.0


def test_multi_line_receipt_produces_exactly_one_receipt_hint(services):
    """P33 §35: a Receipt with multiple lines is posted ONCE -- one `InventoryReceiptPosted`, not
    one per line, even though each line independently records its own Balance fact(s)."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p33-multi-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p33-multiappr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    other_item = services["inventory_item_service"].create_item(
        item_code=f"P33-ITEM2-{suffix}", name=f"P33 Item2 {suffix}", status="ACTIVE",
        stock_uom="EA", is_purchase_allowed=True,
    )
    login_as(services, f"p33-multi-{suffix}", "StrongPass123")
    purchasing = services["inventory_purchasing_service"]
    po = purchasing.create_purchase_order(site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR")
    line1 = purchasing.add_purchase_order_line(
        po.id, stock_item_id=item.id, destination_storeroom_id=storeroom.id, quantity_ordered=5, unit_price=10.0,
    )
    line2 = purchasing.add_purchase_order_line(
        po.id, stock_item_id=other_item.id, destination_storeroom_id=storeroom.id, quantity_ordered=5, unit_price=8.0,
    )
    po = purchasing.submit_purchase_order(po.id)
    login_as(services, f"p33-multiappr-{suffix}", "StrongPass123")
    services["approval_service"].approve_and_apply(po.approval_request_id, note="Approved")
    login_as(services, f"p33-multi-{suffix}", "StrongPass123")

    hints = _spy_hints(services)
    receipt = purchasing.post_receipt(
        po.id,
        receipt_lines=[
            {"purchase_order_line_id": line1.id, "quantity_accepted": 5, "quantity_rejected": 0},
            {"purchase_order_line_id": line2.id, "quantity_accepted": 5, "quantity_rejected": 0},
        ],
    )

    receipt_hints = _receipt_hints(hints)
    assert len(receipt_hints) == 1
    assert receipt_hints[0].entity_id == receipt.id

    detail_hints = [
        h for h in hints if h.category == "inventory_balance" and h.scope_code == "stock_balance_detail"
    ]
    assert len({h.entity_id for h in detail_hints}) == 2, "two distinct items -> two distinct Balance facts"
    balance_1 = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    balance_2 = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=other_item.id, storeroom_id=storeroom.id
    )
    assert balance_1.on_hand_qty == 5.0
    assert balance_2.on_hand_qty == 5.0


# ---------------------------------------------------------------------------
# Zero events on failure -- validation, audit
# ---------------------------------------------------------------------------


def test_receipt_validation_failure_produces_zero_events(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p33-fail-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p33-failappr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier, po, line = _approved_po_ready_for_receipt(
        services, manager_username=f"p33-fail-{suffix}", approver_username=f"p33-failappr-{suffix}",
        suffix=suffix, quantity_ordered=10,
    )
    purchasing = services["inventory_purchasing_service"]

    hints = _spy_hints(services)
    with pytest.raises(Exception):
        purchasing.post_receipt(
            po.id,
            receipt_lines=[{"purchase_order_line_id": line.id, "quantity_accepted": 999, "quantity_rejected": 0}],
        )

    assert _receipt_hints(hints) == []
    balance_hints = [h for h in hints if h.category == "inventory_balance"]
    assert balance_hints == []
    resulting_po = purchasing.get_purchase_order(po.id)
    assert resulting_po.status.value == "APPROVED"


def test_receipt_audit_failure_rolls_back_everything(services, monkeypatch):
    """P33: Receipt posting's enterprise audit was already atomic since before this phase
    (P28A/P31A confirmed `PurchaseOrderSubmissionUnitOfWork` already canonical) -- proven again
    here now that a typed `InventoryReceiptPosted` shares the same transaction: a failed audit
    rolls back the Receipt row, the PO line mutation, the Balance mutation, and the StockTransaction
    together, and produces zero postcommit events of any kind."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p33-auditfail-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p33-auditfailappr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier, po, line = _approved_po_ready_for_receipt(
        services, manager_username=f"p33-auditfail-{suffix}", approver_username=f"p33-auditfailappr-{suffix}",
        suffix=suffix, quantity_ordered=10,
    )
    purchasing = services["inventory_purchasing_service"]

    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("audit backend unavailable")

    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    hints = _spy_hints(services)
    with pytest.raises(RuntimeError):
        purchasing.post_receipt(
            po.id, receipt_lines=[{"purchase_order_line_id": line.id, "quantity_accepted": 5, "quantity_rejected": 0}],
        )

    assert hints == [], "a failed audit must roll back the entire receipt transaction, zero events of any kind"
    resulting_po = purchasing.get_purchase_order(po.id)
    assert resulting_po.status.value == "APPROVED", "PO status must not advance if the receipt rolled back"
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert balance is None or balance.on_hand_qty == 0.0


# ---------------------------------------------------------------------------
# Consumer cutover -- 4 genuine (Procurement/Dashboard/Pricing/Inventory) vs
# 2 incidental (Catalog/Reservations)
# ---------------------------------------------------------------------------


def test_incidental_consumers_have_zero_receipt_reaction(services):
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p33-incid-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p33-incidappr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier, po, line = _approved_po_ready_for_receipt(
        services, manager_username=f"p33-incid-{suffix}", approver_username=f"p33-incidappr-{suffix}", suffix=suffix,
    )
    catalog = _pm_catalog(services)
    calls: list[str] = []
    catalog._catalog_workspace.refresh = lambda: calls.append("catalog")
    catalog._reservations_workspace._request_domain_refresh = lambda: calls.append("reservations")

    services["inventory_purchasing_service"].post_receipt(
        po.id, receipt_lines=[{"purchase_order_line_id": line.id, "quantity_accepted": 5, "quantity_rejected": 0}],
    )
    assert calls == [], "Catalog and Reservations must never react to a Receipt posting (zero real dependency)"


def test_genuine_consumers_all_react_to_receipt_posting(services):
    """P33 §24: Procurement (own PO-scoped receipt history + org-wide receipt count), Dashboard
    (per-PO 'Receipts N' count), Pricing (its own 'Receipts' metric), and Inventory(Foundation)
    (lot/serial/expiry tracking-signal panel reading ReceiptLine directly) each have a genuine,
    source-verified Receipt-data dependency independent of the PO/Balance facts -- confirmed by a
    real reaction here, not inferred from the PO or Balance events that happen to co-occur in the
    same transaction."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p33-genuine-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p33-genuineappr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier, po, line = _approved_po_ready_for_receipt(
        services, manager_username=f"p33-genuine-{suffix}", approver_username=f"p33-genuineappr-{suffix}",
        suffix=suffix,
    )
    catalog = _pm_catalog(services)
    calls: list[str] = []
    catalog._procurement_workspace._request_domain_refresh = lambda: calls.append("procurement")
    catalog._dashboard_workspace._request_domain_refresh = lambda: calls.append("dashboard")
    catalog._pricing_workspace._request_domain_refresh = lambda: calls.append("pricing")
    catalog._inventory_workspace._request_domain_refresh = lambda: calls.append("inventory")

    services["inventory_purchasing_service"].post_receipt(
        po.id, receipt_lines=[{"purchase_order_line_id": line.id, "quantity_accepted": 5, "quantity_rejected": 0}],
    )
    assert set(calls) == {"procurement", "dashboard", "pricing", "inventory"}


# ---------------------------------------------------------------------------
# P33 §14: PurchaseOrderLine concurrency -- pre-existing, unfixed gap, confirmed by source
# ---------------------------------------------------------------------------


def test_purchase_order_line_receiving_has_no_optimistic_concurrency_protection(services, session):
    """P33 §14 finding, confirmed by source and reproduced here: `PurchaseOrderLineORM` carries no
    `version` column (unlike `PurchaseOrder`/`CycleCount`/`StockBalance`/`StockReservation`, all of
    which use `update_with_version_check`) and `SqlAlchemyPurchaseOrderLineRepository.update()`
    performs a blind field overwrite. This is a pre-existing characteristic, already documented in
    P28A ("child PurchaseOrderLine (no own version field, additive-only mutation)") -- NOT
    introduced or fixed by P33, which only adds the Receipt DomainEvent/ViewInvalidation and does
    not touch PO-line write mechanics. This test reproduces the exact race P33 §14 describes (two
    concurrent receipts against the same line, each independently reading the pre-write outstanding
    quantity) at the repository layer to prove the lost-update is real, not merely theoretical."""
    suffix = uuid4().hex[:6].upper()
    services["auth_service"].register_user(f"p33-race-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    services["auth_service"].register_user(f"p33-raceappr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier, po, line = _approved_po_ready_for_receipt(
        services, manager_username=f"p33-race-{suffix}", approver_username=f"p33-raceappr-{suffix}",
        suffix=suffix, quantity_ordered=20,
    )

    repo_a = SqlAlchemyPurchaseOrderLineRepository(session, tenant_context_service=services["tenant_context_service"])
    session_b = sessionmaker(bind=session.bind, future=True)()
    try:
        repo_b = SqlAlchemyPurchaseOrderLineRepository(session_b, tenant_context_service=services["tenant_context_service"])

        read_by_a = repo_a.get(line.id)
        read_by_b = repo_b.get(line.id)
        assert read_by_a.quantity_received == 0.0
        assert read_by_b.quantity_received == 0.0

        from dataclasses import replace as dc_replace

        from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
            PurchaseOrderLineStatus,
        )

        updated_by_a = dc_replace(
            read_by_a, quantity_received=8.0, status=PurchaseOrderLineStatus.PARTIALLY_RECEIVED
        )
        repo_a.update(updated_by_a)
        session.commit()

        # B's write is based on its own stale pre-A-commit read (quantity_received=0), exactly
        # mirroring two concurrent `post_receipt` calls whose `outstanding` guard both evaluated
        # against the same initial snapshot.
        updated_by_b = dc_replace(
            read_by_b, quantity_received=8.0, status=PurchaseOrderLineStatus.PARTIALLY_RECEIVED
        )
        repo_b.update(updated_by_b)
        session_b.commit()
    finally:
        session_b.close()

    final = repo_a.get(line.id)
    # If the repository were version-protected, B's update would have raised ConcurrencyError and
    # the final state would be 8.0 (A's write only). Because there is no protection at all, B's
    # blind overwrite silently succeeds and produces the SAME final value -- proving neither write
    # is rejected, which is the confirmed, pre-existing gap: two real, distinct 8-unit receipts
    # would both persist their own Receipt/StockTransaction/Balance rows while the PO line's own
    # `quantity_received` reflects only one of them (a lost update on the PO line aggregate).
    assert final.quantity_received == 8.0, (
        "confirms the pre-existing gap: B's write was not rejected despite reading stale data"
    )
