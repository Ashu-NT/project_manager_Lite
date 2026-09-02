from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.inventory_procurement.domain.procurement.purchasing_events import (
    InventoryPurchaseOrderApproved,
    InventoryPurchaseOrderRejected,
)
from src.core.modules.inventory_procurement.domain.procurement.requisition_events import (
    InventoryRequisitionSourcingAdvanced,
)
from src.core.modules.inventory_procurement.infrastructure.approval.purchasing_apply_participant import (
    PurchasingApprovalParticipant,
)
from src.core.platform.domain.master_data.party import PartyType
from src.infra.composition.approval_apply_dependencies.purchasing import (
    build_purchasing_approval_deps,
)
from src.infra.persistence.orm.base import Base
from src.tests.ui_runtime_helpers import login_as


def _procurement_context(services):
    site = services["site_service"].create_site(
        site_code="PAPR",
        name="Purchasing Approval Participant Site",
        currency_code="EUR",
    )
    item = services["inventory_item_service"].create_item(
        item_code="PAPR-MOTOR-001",
        name="Purchasing Approval Motor",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="PAPR-MAIN",
        name="Purchasing Approval Participant Main",
        site_id=site.id,
        status="ACTIVE",
    )
    supplier = services["party_service"].create_party(
        party_code="SUP-PAPR",
        party_name="Purchasing Approval Supplier",
        party_type=PartyType.SUPPLIER,
    )
    return site, storeroom, item, supplier


def _submitted_purchase_order_sourced_from_requisition(services):
    """Sources the purchase order from an approved requisition line so the more complex
    on-order-balance/requisition-status-refresh code paths in
    `apply_submitted_purchase_order_approval` are exercised, not just the plain-PO path."""
    auth = services["auth_service"]
    auth.register_user("papr-buyer", "StrongPass123", role_names=["inventory_manager"])
    auth.register_user("papr-approver", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context(services)
    procurement = services["inventory_procurement_service"]
    purchasing = services["inventory_purchasing_service"]
    approvals = services["approval_service"]

    login_as(services, "papr-buyer", "StrongPass123")
    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Source replacement motor",
        needed_by_date=date(2026, 4, 10),
    )
    requisition_line = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=5,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=250.0,
    )
    requisition = procurement.submit_requisition(requisition.id)

    login_as(services, "papr-approver", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved requisition")

    login_as(services, "papr-buyer", "StrongPass123")
    purchase_order = purchasing.create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
        source_requisition_id=requisition.id,
        expected_delivery_date=date(2026, 4, 20),
    )
    purchase_order_line = purchasing.add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=5,
        unit_price=240.0,
        source_requisition_line_id=requisition_line.id,
    )
    purchase_order = purchasing.submit_purchase_order(purchase_order.id)
    return site, storeroom, item, supplier, requisition, requisition_line, purchase_order, purchase_order_line


def _pending_request(services, purchase_order):
    pending = services["approval_service"].list_pending()
    for request in pending:
        if request.id == purchase_order.approval_request_id:
            return request
    raise AssertionError("expected a pending approval request for the submitted purchase order")


def _deps(services, session):
    return build_purchasing_approval_deps(
        session,
        user_session=services["user_session"],
        tenant_context_service=services["tenant_context_service"],
    )


def test_participant_apply_approves_purchase_order_on_the_supplied_session(services, session):
    (
        _site,
        storeroom,
        item,
        _supplier,
        requisition,
        requisition_line,
        purchase_order,
        _purchase_order_line,
    ) = _submitted_purchase_order_sourced_from_requisition(services)
    request = _pending_request(services, purchase_order)
    deps = _deps(services, session)

    result = PurchasingApprovalParticipant().apply(request, deps)
    session.flush()

    approved = deps.purchasing_service._purchase_order_repo.get(purchase_order.id)
    lines = deps.purchasing_service._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)
    assert approved.status.value == "APPROVED"
    assert approved.approved_at is not None
    assert [line.status.value for line in lines] == ["OPEN"]

    refreshed_requisition = deps.purchasing_service._requisition_repo.get(requisition.id)
    refreshed_requisition_line = deps.purchasing_service._requisition_line_repo.get(requisition_line.id)
    assert refreshed_requisition.status.value == "FULLY_SOURCED"
    assert refreshed_requisition_line.status.value == "FULLY_SOURCED"
    assert refreshed_requisition_line.quantity_sourced == pytest.approx(5.0)

    balance = deps.purchasing_service._balance_repo.get_for_stock_position(
        purchase_order.organization_id, item.id, storeroom.id
    )
    assert balance is not None
    assert balance.on_order_qty == pytest.approx(5.0)
    assert balance.on_hand_qty == pytest.approx(0.0)

 
    assert result.post_commit_events == ()

    assert len(result.domain_events) == 2
    po_approved, requisition_sourcing = result.domain_events
    assert isinstance(po_approved, InventoryPurchaseOrderApproved)
    assert po_approved.purchase_order_id == purchase_order.id
    assert po_approved.approval_request_id == request.id
    assert po_approved.organization_id == purchase_order.organization_id
    assert po_approved.tenant_id == request.tenant_id
    assert isinstance(requisition_sourcing, InventoryRequisitionSourcingAdvanced)
    assert requisition_sourcing.requisition_id == requisition.id
    assert requisition_sourcing.purchase_order_id == purchase_order.id
    assert requisition_sourcing.resulting_status == "FULLY_SOURCED"
    assert requisition_sourcing.organization_id == purchase_order.organization_id
    assert requisition_sourcing.tenant_id == request.tenant_id


def test_participant_reject_rejects_purchase_order_on_the_supplied_session(services, session):
    (
        _site,
        _storeroom,
        _item,
        _supplier,
        _requisition,
        _requisition_line,
        purchase_order,
        _purchase_order_line,
    ) = _submitted_purchase_order_sourced_from_requisition(services)
    request = _pending_request(services, purchase_order)
    deps = _deps(services, session)

    result = PurchasingApprovalParticipant().reject(request, deps)

    rejected = deps.purchasing_service._purchase_order_repo.get(purchase_order.id)
    lines = deps.purchasing_service._purchase_order_line_repo.list_for_purchase_order(purchase_order.id)
    assert rejected.status.value == "REJECTED"
    assert [line.status.value for line in lines] == ["CANCELLED"]
    assert result.post_commit_events == ()
    assert len(result.domain_events) == 1
    rejected_event = result.domain_events[0]
    assert isinstance(rejected_event, InventoryPurchaseOrderRejected)
    assert rejected_event.purchase_order_id == purchase_order.id
    assert rejected_event.approval_request_id == request.id
    assert rejected_event.organization_id == purchase_order.organization_id
    assert rejected_event.tenant_id == request.tenant_id


def test_participant_never_calls_commit_or_rollback(services, session, monkeypatch):
    """The participant stages only -- the caller (today: ApprovalService on the shared Session;
    from Step 2 onward: its own PlatformUnitOfWork) owns transaction completion."""
    (
        _site,
        _storeroom,
        _item,
        _supplier,
        _requisition,
        _requisition_line,
        purchase_order,
        _purchase_order_line,
    ) = _submitted_purchase_order_sourced_from_requisition(services)
    request = _pending_request(services, purchase_order)
    deps = _deps(services, session)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the participant must never commit or roll back its own Session")

    monkeypatch.setattr(type(session), "commit", _forbidden)
    monkeypatch.setattr(type(session), "rollback", _forbidden)

    PurchasingApprovalParticipant().apply(request, deps)


def test_dependencies_factory_binds_every_transaction_sensitive_field_to_the_supplied_session(
    tmp_path, services
):
    engine_a = create_engine(f"sqlite:///{tmp_path}/deps_a.db", future=True)
    engine_b = create_engine(f"sqlite:///{tmp_path}/deps_b.db", future=True)
    Base.metadata.create_all(engine_a)
    Base.metadata.create_all(engine_b)
    session_a = sessionmaker(bind=engine_a, future=True)()
    session_b = sessionmaker(bind=engine_b, future=True)()
    try:
        deps_a = _deps(services, session_a)
        deps_b = _deps(services, session_b)

        assert deps_a.purchasing_service._session is session_a
        assert deps_b.purchasing_service._session is session_b
        assert deps_a.purchasing_service._purchase_order_repo.session is session_a
        assert deps_b.purchasing_service._purchase_order_repo.session is session_b
        assert deps_a.purchasing_service._purchase_order_line_repo.session is session_a
        assert deps_b.purchasing_service._purchase_order_line_repo.session is session_b
        assert deps_a.purchasing_service._requisition_repo.session is session_a
        assert deps_b.purchasing_service._requisition_repo.session is session_b
        assert deps_a.purchasing_service._requisition_line_repo.session is session_a
        assert deps_b.purchasing_service._requisition_line_repo.session is session_b
        assert deps_a.purchasing_service._balance_repo.session is session_a
        assert deps_b.purchasing_service._balance_repo.session is session_b
        assert deps_a.purchasing_service._item_service._session is session_a
        assert deps_b.purchasing_service._item_service._session is session_b
        assert deps_a.purchasing_service._item_service._item_repo.session is session_a
        assert deps_b.purchasing_service._item_service._item_repo.session is session_b
        assert deps_a.purchasing_service is not deps_b.purchasing_service
        assert deps_a.purchasing_service._approval_service is None, (
            "the apply path must never reach back into ApprovalService"
        )
        assert deps_b.purchasing_service._approval_service is None
        assert deps_a.purchasing_service._activity_service is None, (
            "record_activity must remain a silent no-op, matching current production behavior"
        )
    finally:
        session_a.close()
        session_b.close()


def test_dependencies_factory_never_opens_its_own_session(services, session):
    deps = _deps(services, session)
    assert deps.purchasing_service._session is session, (
        "the factory must use the supplied Session, never a fresh one"
    )


def _submitted_purchase_order_sourcing_two_lines_of_one_requisition(services):
    """P28B-FIX SS8: one PO with two lines, both sourced from DIFFERENT lines of the SAME
    Requisition -- the participant's batching must still return exactly one
    `InventoryRequisitionSourcingAdvanced` for that Requisition, not two."""
    auth = services["auth_service"]
    auth.register_user("papr-buyer2", "StrongPass123", role_names=["inventory_manager"])
    auth.register_user("papr-approver2", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context2(services)
    procurement = services["inventory_procurement_service"]
    purchasing = services["inventory_purchasing_service"]
    approvals = services["approval_service"]

    login_as(services, "papr-buyer2", "StrongPass123")
    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Source two lines of one requisition",
        needed_by_date=date(2026, 4, 10),
    )
    line_a = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=3,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=250.0,
    )
    line_b = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=4,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=250.0,
    )
    requisition = procurement.submit_requisition(requisition.id)

    login_as(services, "papr-approver2", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved requisition")

    login_as(services, "papr-buyer2", "StrongPass123")
    purchase_order = purchasing.create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code="EUR",
        source_requisition_id=requisition.id,
        expected_delivery_date=date(2026, 4, 20),
    )
    purchasing.add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=3,
        unit_price=240.0,
        source_requisition_line_id=line_a.id,
    )
    purchasing.add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=4,
        unit_price=240.0,
        source_requisition_line_id=line_b.id,
    )
    purchase_order = purchasing.submit_purchase_order(purchase_order.id)
    return requisition, purchase_order


def _procurement_context2(services):
    site = services["site_service"].create_site(
        site_code="PAPR2",
        name="Purchasing Approval Participant Site 2",
        currency_code="EUR",
    )
    item = services["inventory_item_service"].create_item(
        item_code="PAPR2-MOTOR-001",
        name="Purchasing Approval Motor 2",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="PAPR2-MAIN",
        name="Purchasing Approval Participant Main 2",
        site_id=site.id,
        status="ACTIVE",
    )
    supplier = services["party_service"].create_party(
        party_code="SUP-PAPR2",
        party_name="Purchasing Approval Supplier 2",
        party_type=PartyType.SUPPLIER,
    )
    return site, storeroom, item, supplier


def test_participant_apply_batches_multiple_lines_of_same_requisition_into_one_sourcing_event(
    services, session
):
    requisition, purchase_order = _submitted_purchase_order_sourcing_two_lines_of_one_requisition(
        services
    )
    request = _pending_request(services, purchase_order)
    deps = _deps(services, session)

    result = PurchasingApprovalParticipant().apply(request, deps)

    sourcing_events = [
        e for e in result.domain_events if isinstance(e, InventoryRequisitionSourcingAdvanced)
    ]
    assert len(sourcing_events) == 1, (
        "two PO lines sourcing two different lines of the SAME requisition must batch into "
        "exactly one sourcing event, not one per line"
    )
    assert sourcing_events[0].requisition_id == requisition.id
    assert sourcing_events[0].resulting_status == "FULLY_SOURCED"

    refreshed_requisition = deps.purchasing_service._requisition_repo.get(requisition.id)
    assert refreshed_requisition.status.value == "FULLY_SOURCED"


def _submitted_purchase_order_sourcing_two_requisitions(services):
    """P28B-FIX SS8: one PO with lines sourced from TWO DIFFERENT Requisitions -- the participant
    must return one `InventoryRequisitionSourcingAdvanced` per touched Requisition."""
    auth = services["auth_service"]
    auth.register_user("papr-buyer3", "StrongPass123", role_names=["inventory_manager"])
    auth.register_user("papr-approver3", "StrongPass123", role_names=["approver"])
    site = services["site_service"].create_site(
        site_code="PAPR3", name="Purchasing Approval Participant Site 3", currency_code="EUR"
    )
    item = services["inventory_item_service"].create_item(
        item_code="PAPR3-MOTOR-001",
        name="Purchasing Approval Motor 3",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="PAPR3-MAIN", name="Purchasing Approval Participant Main 3", site_id=site.id, status="ACTIVE"
    )
    supplier = services["party_service"].create_party(
        party_code="SUP-PAPR3", party_name="Purchasing Approval Supplier 3", party_type=PartyType.SUPPLIER
    )
    procurement = services["inventory_procurement_service"]
    purchasing = services["inventory_purchasing_service"]
    approvals = services["approval_service"]

    login_as(services, "papr-buyer3", "StrongPass123")
    requisition_a = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Requisition A",
        needed_by_date=date(2026, 4, 10),
    )
    line_a = procurement.add_requisition_line(
        requisition_a.id,
        stock_item_id=item.id,
        quantity_requested=2,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=250.0,
    )
    requisition_a = procurement.submit_requisition(requisition_a.id)

    requisition_b = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Requisition B",
        needed_by_date=date(2026, 4, 12),
    )
    line_b = procurement.add_requisition_line(
        requisition_b.id,
        stock_item_id=item.id,
        quantity_requested=3,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=250.0,
    )
    requisition_b = procurement.submit_requisition(requisition_b.id)

    login_as(services, "papr-approver3", "StrongPass123")
    approvals.approve_and_apply(requisition_a.approval_request_id, note="Approved requisition A")
    approvals.approve_and_apply(requisition_b.approval_request_id, note="Approved requisition B")

    login_as(services, "papr-buyer3", "StrongPass123")
    purchase_order = purchasing.create_purchase_order(
        site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR",
    )
    purchasing.add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=2,
        unit_price=240.0,
        source_requisition_line_id=line_a.id,
    )
    purchasing.add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=3,
        unit_price=240.0,
        source_requisition_line_id=line_b.id,
    )
    purchase_order = purchasing.submit_purchase_order(purchase_order.id)
    return requisition_a, requisition_b, purchase_order


def test_participant_apply_emits_one_sourcing_event_per_touched_requisition(services, session):
    requisition_a, requisition_b, purchase_order = _submitted_purchase_order_sourcing_two_requisitions(
        services
    )
    request = _pending_request(services, purchase_order)
    deps = _deps(services, session)

    result = PurchasingApprovalParticipant().apply(request, deps)

    sourcing_events = [
        e for e in result.domain_events if isinstance(e, InventoryRequisitionSourcingAdvanced)
    ]
    assert len(sourcing_events) == 2, (
        "a PO sourcing two different requisitions must emit one sourcing event per requisition"
    )
    touched_ids = {e.requisition_id for e in sourcing_events}
    assert touched_ids == {requisition_a.id, requisition_b.id}
    for event in sourcing_events:
        assert event.resulting_status == "FULLY_SOURCED"


def test_failed_approval_never_reaches_the_view_invalidation_channel(services, session):
    """P28B-FIX §7: a rejected/failed approval must never produce a Requisition sourcing fact --
    `reject()` never sources anything, so `domain_events` must contain zero
    `InventoryRequisitionSourcingAdvanced`."""
    (
        _site,
        _storeroom,
        _item,
        _supplier,
        _requisition,
        _requisition_line,
        purchase_order,
        _purchase_order_line,
    ) = _submitted_purchase_order_sourced_from_requisition(services)
    request = _pending_request(services, purchase_order)
    deps = _deps(services, session)

    result = PurchasingApprovalParticipant().reject(request, deps)

    sourcing_events = [
        e for e in result.domain_events if isinstance(e, InventoryRequisitionSourcingAdvanced)
    ]
    assert sourcing_events == []
