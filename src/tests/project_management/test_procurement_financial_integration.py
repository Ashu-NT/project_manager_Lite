from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.core.modules.inventory_procurement.domain import PurchaseOrderStatus
from src.core.modules.inventory_procurement.infrastructure.persistence.orm.integration_outbox import (
    ProcurementFinancialOutboxORM,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.orm.procurement import (
    ReceiptHeaderORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.commitment import (
    ProjectCommitmentLineORM,
    ProjectCommitmentMatchORM,
    ProjectCommitmentSourceRevisionORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.cost_entry import (
    ProjectCostEntryORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox import (
    ProjectFinanceInboxORM,
)
from src.core.modules.project_management.application.financials.invalidation import (
    FinanceInvalidationScope,
)
from src.core.modules.project_management.application.financials.commitments.commitment_events import (
    CommitmentLineChanged,
    CommitmentMatchChanged,
)
from src.core.shared.events.domain_events import domain_events
from src.core.platform.domain.master_data.party import PartyType
from src.core.platform.integration import InboxProcessingStatus, OutboxDeliveryStatus
from src.tests.ui_runtime_helpers import login_as


def _create_approved_project_purchase_order(
    services,
    *,
    close_financial_period: bool = False,
    project_linked: bool = True,
    link_via_task: bool = False,
):
    suffix = uuid4().hex[:7].upper()
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        f"Procurement Finance {suffix}",
        financial_currency_code=organization.base_currency,
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=f"MAT-{suffix}", name="Material receipt accrual"
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id,
        expected_version=profile.version,
        default_cost_code_id=cost_code.id,
    )
    financial_period = services["financial_period_service"].create_period(
        code=f"PROC-{suffix}",
        name="Procurement May 2026",
        fiscal_year=2026,
        period_number=5,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )
    if close_financial_period:
        services["financial_period_service"].close_period(
            financial_period.id, expected_version=financial_period.version
        )
    site = services["site_service"].create_site(
        site_code=f"PF-{suffix}",
        name=f"Procurement Finance Site {suffix}",
        currency_code=organization.base_currency,
    )
    item = services["inventory_item_service"].create_item(
        item_code=f"PUMP-{suffix}",
        name=f"Project Pump {suffix}",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=f"PF-MAIN-{suffix}",
        name=f"Project Stores {suffix}",
        site_id=site.id,
        status="ACTIVE",
    )
    supplier = services["party_service"].create_party(
        party_code=f"PF-SUP-{suffix}",
        party_name=f"Project Supplier {suffix}",
        party_type=PartyType.SUPPLIER,
    )
    buyer = f"pf-buyer-{suffix.lower()}"
    approver = f"pf-approver-{suffix.lower()}"
    services["auth_service"].register_user(
        buyer, "StrongPass123", role_names=["inventory_manager"]
    )
    services["auth_service"].register_user(
        approver, "StrongPass123", role_names=["approver"]
    )
    source_task = (
        services["task_service"].create_task(
            project.id,
            f"Procurement Task {suffix}",
            start_date=date(2026, 5, 1),
            duration_days=5,
        )
        if link_via_task
        else None
    )

    login_as(services, buyer, "StrongPass123")
    procurement = services["inventory_procurement_service"]
    purchasing = services["inventory_purchasing_service"]
    source_kwargs = ({
        "source_reference_type": "task" if source_task else "project",
        "source_reference_id": source_task.id if source_task else project.id,
        "source_module": "project_management",
        "source_entity_type": "task" if source_task else "project",
    } if project_linked else {})
    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Project material",
        needed_by_date=date(2026, 5, 15),
        **source_kwargs,
    )
    requisition_line = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=5,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=100,
    )
    requisition = procurement.submit_requisition(requisition.id)
    login_as(services, approver, "StrongPass123")
    services["approval_service"].approve_and_apply(
        requisition.approval_request_id, note="Approved project demand"
    )

    login_as(services, buyer, "StrongPass123")
    purchase_order = purchasing.create_purchase_order(
        site_id=site.id,
        supplier_party_id=supplier.id,
        currency_code=organization.base_currency,
        source_requisition_id=requisition.id,
        expected_delivery_date=date(2026, 5, 20),
    )
    purchase_order_line = purchasing.add_purchase_order_line(
        purchase_order.id,
        stock_item_id=item.id,
        destination_storeroom_id=storeroom.id,
        quantity_ordered=5,
        unit_price=100,
        source_requisition_line_id=requisition_line.id,
    )
    purchase_order = purchasing.submit_purchase_order(purchase_order.id)
    login_as(services, approver, "StrongPass123")
    services["approval_service"].approve_and_apply(
        purchase_order.approval_request_id, note="Approved project PO"
    )
    login_as(services, buyer, "StrongPass123")
    return project, item, storeroom, purchase_order, purchase_order_line


def test_sent_po_partial_receipt_and_cancellation_update_project_finance(services) -> None:
    project, item, storeroom, purchase_order, po_line = (
        _create_approved_project_purchase_order(services)
    )
    purchasing = services["inventory_purchasing_service"]
    commitment_scopes: list[object] = []
    actual_scopes: list[FinanceInvalidationScope] = []

    def capture_commitment(event: object, _context: object) -> None:
        commitment_scopes.append(event)

    def capture_actual(scope: FinanceInvalidationScope) -> None:
        actual_scopes.append(scope)

    post_commit_bus = services["procurement_financial_dispatcher"]._post_commit_bus
    line_subscription = post_commit_bus.subscribe(
        CommitmentLineChanged, capture_commitment
    )
    match_subscription = post_commit_bus.subscribe(
        CommitmentMatchChanged, capture_commitment
    )
    domain_events.cost_entries_changed.connect(capture_actual)
    try:
        sent = purchasing.send_purchase_order(purchase_order.id)

        session = services["session"]
        commitment = session.execute(select(ProjectCommitmentLineORM)).scalar_one()
        assert commitment.project_id == project.id
        assert commitment.state == "sent"
        assert commitment.amount == Decimal("500.0000")
        assert commitment.matched_amount == Decimal("0.0000")

        purchasing.post_receipt(
            sent.id,
            receipt_date=datetime(2026, 5, 10, 12, tzinfo=timezone.utc),
            receipt_lines=[{
                "purchase_order_line_id": po_line.id,
                "quantity_accepted": 2,
                "unit_cost": 100,
            }],
        )
        session.expire_all()
        commitment = session.execute(select(ProjectCommitmentLineORM)).scalar_one()
        actual = session.execute(select(ProjectCostEntryORM)).scalar_one()
        match = session.execute(select(ProjectCommitmentMatchORM)).scalar_one()
        assert commitment.state == "partially_received"
        assert commitment.matched_amount == Decimal("200.0000")
        assert actual.status == "posted"
        assert actual.amount == Decimal("200.0000")
        assert match.amount == Decimal("200.0000")

        refreshed = purchasing.get_purchase_order(sent.id)
        cancelled = purchasing.cancel_purchase_order(
            refreshed.id,
            expected_version=refreshed.version,
            note="Supplier cannot deliver remaining project quantity",
        )
    finally:
        line_subscription.dispose()
        match_subscription.dispose()
        domain_events.cost_entries_changed.disconnect(capture_actual)
    session.expire_all()
    commitment = session.execute(select(ProjectCommitmentLineORM)).scalar_one()
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    assert cancelled.status is PurchaseOrderStatus.CANCELLED
    assert commitment.state == "cancelled"
    assert commitment.amount - commitment.matched_amount == Decimal("300.0000")
    assert balance is not None
    assert balance.on_order_qty == pytest.approx(0.0)

    outbox = session.execute(select(ProcurementFinancialOutboxORM)).scalars().all()
    inbox = session.execute(select(ProjectFinanceInboxORM)).scalars().all()
    assert len(outbox) == 4
    assert len(inbox) == 4
    assert all(row.status == OutboxDeliveryStatus.PUBLISHED.value for row in outbox)
    assert all(row.status == InboxProcessingStatus.PROCESSED.value for row in inbox)
    assert session.execute(select(ProjectCommitmentSourceRevisionORM)).scalars().all()
    assert services["procurement_financial_dispatcher"].dispatch_pending(limit=50) == 0
    # Send, receipt-state update, receipt matching, and cancellation are four
    # distinct committed Procurement projections affecting commitment reads.
    assert len(commitment_scopes) == 4
    assert len(actual_scopes) == 1
    assert all(scope.project_id == project.id for scope in commitment_scopes)
    assert actual_scopes[0].project_id == project.id


def test_purchase_order_send_rolls_back_when_outbox_write_fails(
    services, monkeypatch
) -> None:
    _, _, _, purchase_order, _ = _create_approved_project_purchase_order(services)
    outbox_service = services["procurement_financial_outbox_service"]

    def _fail(_envelope):
        raise RuntimeError("procurement outbox unavailable")

    monkeypatch.setattr(outbox_service, "enqueue", _fail)
    with pytest.raises(RuntimeError, match="procurement outbox unavailable"):
        services["inventory_purchasing_service"].send_purchase_order(purchase_order.id)

    persisted = services["inventory_purchasing_service"].get_purchase_order(
        purchase_order.id
    )
    assert persisted.status is PurchaseOrderStatus.APPROVED
    assert services["session"].execute(
        select(ProcurementFinancialOutboxORM)
    ).scalars().all() == []
    assert services["session"].execute(
        select(ProjectCommitmentLineORM)
    ).scalars().all() == []


def test_full_receipt_and_close_preserve_zero_remaining_exposure(services) -> None:
    project, _, _, purchase_order, po_line = _create_approved_project_purchase_order(
        services
    )
    purchasing = services["inventory_purchasing_service"]
    sent = purchasing.send_purchase_order(purchase_order.id)
    purchasing.post_receipt(
        sent.id,
        receipt_date=datetime(2026, 5, 12, 9, tzinfo=timezone.utc),
        receipt_lines=[{
            "purchase_order_line_id": po_line.id,
            "quantity_accepted": 5,
            "unit_cost": 110,
        }],
    )
    refreshed = purchasing.get_purchase_order(sent.id)
    closed = purchasing.close_purchase_order(refreshed.id)

    session = services["session"]
    session.expire_all()
    commitment = session.execute(select(ProjectCommitmentLineORM)).scalar_one()
    actual = session.execute(select(ProjectCostEntryORM)).scalar_one()
    assert closed.status is PurchaseOrderStatus.CLOSED
    assert commitment.project_id == project.id
    assert commitment.state == "closed"
    assert commitment.matched_amount == commitment.amount == Decimal("500.0000")
    assert actual.amount == Decimal("550.0000")
    match = session.execute(select(ProjectCommitmentMatchORM)).scalar_one()
    assert match.amount == Decimal("500.0000")
    assert len(session.execute(
        select(ProjectCommitmentSourceRevisionORM)
    ).scalars().all()) == 3


def test_closed_period_keeps_receipt_delivery_retryable_without_actual(services) -> None:
    project, _, _, purchase_order, po_line = _create_approved_project_purchase_order(
        services, close_financial_period=True
    )
    purchasing = services["inventory_purchasing_service"]
    sent = purchasing.send_purchase_order(purchase_order.id)
    purchasing.post_receipt(
        sent.id,
        receipt_date=datetime(2026, 5, 14, 10, tzinfo=timezone.utc),
        receipt_lines=[{
            "purchase_order_line_id": po_line.id,
            "quantity_accepted": 1,
            "unit_cost": 100,
        }],
    )

    session = services["session"]
    session.expire_all()
    assert session.execute(select(ProjectCostEntryORM)).scalars().all() == []
    commitment = session.execute(select(ProjectCommitmentLineORM)).scalar_one()
    assert commitment.project_id == project.id
    assert commitment.state == "partially_received"
    outbox = session.execute(
        select(ProcurementFinancialOutboxORM).where(
            ProcurementFinancialOutboxORM.aggregate_type == "receipt_line"
        )
    ).scalar_one()
    inbox = session.execute(
        select(ProjectFinanceInboxORM).where(
            ProjectFinanceInboxORM.aggregate_type == "receipt_line"
        )
    ).scalar_one()
    assert outbox.status == OutboxDeliveryStatus.RETRY.value
    assert inbox.status == InboxProcessingStatus.RETRY.value
    assert outbox.last_error_code == "FINANCIAL_PERIOD_POSTING_BLOCKED"
    assert inbox.last_error_code == "FINANCIAL_PERIOD_POSTING_BLOCKED"


def test_unlinked_purchase_order_does_not_emit_project_finance_events(services) -> None:
    _, _, _, purchase_order, _ = _create_approved_project_purchase_order(
        services, project_linked=False
    )
    sent = services["inventory_purchasing_service"].send_purchase_order(
        purchase_order.id
    )
    assert sent.status is PurchaseOrderStatus.SENT
    assert services["session"].execute(
        select(ProcurementFinancialOutboxORM)
    ).scalars().all() == []
    assert services["session"].execute(
        select(ProjectCommitmentLineORM)
    ).scalars().all() == []


def test_task_linked_procurement_is_resolved_only_by_pm_consumer(services) -> None:
    project, _, _, purchase_order, _ = _create_approved_project_purchase_order(
        services, link_via_task=True
    )
    services["inventory_purchasing_service"].send_purchase_order(purchase_order.id)

    commitment = services["session"].execute(
        select(ProjectCommitmentLineORM)
    ).scalar_one()
    assert commitment.project_id == project.id
    assert commitment.task_id is not None


def test_receipt_and_stock_changes_roll_back_when_outbox_write_fails(
    services, monkeypatch
) -> None:
    _, item, storeroom, purchase_order, po_line = (
        _create_approved_project_purchase_order(services)
    )
    purchasing = services["inventory_purchasing_service"]
    sent = purchasing.send_purchase_order(purchase_order.id)
    outbox_service = services["procurement_financial_outbox_service"]

    def _fail(_envelope):
        raise RuntimeError("receipt outbox unavailable")

    monkeypatch.setattr(outbox_service, "enqueue", _fail)
    with pytest.raises(RuntimeError, match="receipt outbox unavailable"):
        purchasing.post_receipt(
            sent.id,
            receipt_date=datetime(2026, 5, 18, 8, tzinfo=timezone.utc),
            receipt_lines=[{
                "purchase_order_line_id": po_line.id,
                "quantity_accepted": 1,
                "unit_cost": 100,
            }],
        )

    persisted = purchasing.get_purchase_order(sent.id)
    balance = services["inventory_stock_service"].get_balance_for_stock_position(
        stock_item_id=item.id, storeroom_id=storeroom.id
    )
    commitment = services["session"].execute(
        select(ProjectCommitmentLineORM)
    ).scalar_one()
    assert persisted.status is PurchaseOrderStatus.SENT
    assert services["session"].execute(select(ReceiptHeaderORM)).scalars().all() == []
    assert services["session"].execute(select(ProjectCostEntryORM)).scalars().all() == []
    assert commitment.state == "sent"
    assert commitment.matched_amount == Decimal("0.0000")
    assert balance is not None
    assert balance.on_order_qty == pytest.approx(5.0)
    assert balance.on_hand_qty == pytest.approx(0.0)


def test_commitment_transactional_handler_runs_before_the_dispatcher_commits(services) -> None:
    """P36-FIX2: the transactional handler must receive the actual canonical `UnitOfWork`
    instance that owns this transaction -- never `ProcurementFinancialDispatcher` itself.
    `ProcurementFinancialDispatcher` is not a `UnitOfWork` (no `record_event`/`commit`/
    `__enter__`/`__exit__`); passing it as the handler's `uow` argument would be duck-typed
    impersonation, not the canonical architecture. The handler instead receives a real
    `SqlAlchemyUnitOfWorkBase` bound to the dispatcher's own session -- proven both by identity
    (not the dispatcher) and by shape (implements the full `UnitOfWork` protocol)."""
    from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase

    dispatcher = services["procurement_financial_dispatcher"]
    seen = []
    received_uows = []

    def _observe(event, uow) -> None:
        seen.append(event)
        received_uows.append(uow)

    subscription = dispatcher._transactional_dispatcher.subscribe(
        CommitmentLineChanged, _observe
    )
    try:
        _, _, _, purchase_order, _ = _create_approved_project_purchase_order(services)
        services["inventory_purchasing_service"].send_purchase_order(purchase_order.id)
    finally:
        subscription.dispose()

    assert len(seen) == 1
    assert seen[0].change_type.value == "CREATED"
    assert len(received_uows) == 1
    handler_uow = received_uows[0]
    assert handler_uow is not dispatcher, "must not be the dispatcher impersonating a UoW"
    assert isinstance(handler_uow, SqlAlchemyUnitOfWorkBase)
    assert hasattr(handler_uow, "record_event") and hasattr(handler_uow, "commit")
    assert handler_uow._session is dispatcher._session, (
        "the UoW wraps the dispatcher's own session -- one transaction owner, not a second one"
    )


def test_commitment_transactional_handler_failure_rolls_back_and_yields_zero_postcommit_event(
    services,
) -> None:
    """P36-FIX core proof: when a precommit Commitment transactional handler fails, the mutation
    must not persist and no postcommit event/ViewInvalidation may occur -- the exact guarantee a
    bare `session.commit()` + `post_commit_bus.publish(event)` sequence could never provide."""
    dispatcher = services["procurement_financial_dispatcher"]

    def _boom(_event, _uow) -> None:
        raise RuntimeError("simulated precommit Commitment handler failure")

    subscription = dispatcher._transactional_dispatcher.subscribe(CommitmentLineChanged, _boom)
    postcommit_seen = []
    post_commit_subscription = dispatcher._post_commit_bus.subscribe(
        CommitmentLineChanged, lambda e, c: postcommit_seen.append(e)
    )
    try:
        _, _, _, purchase_order, _ = _create_approved_project_purchase_order(services)
        services["inventory_purchasing_service"].send_purchase_order(purchase_order.id)
    finally:
        subscription.dispose()
        post_commit_subscription.dispose()

    assert services["session"].execute(
        select(ProjectCommitmentLineORM)
    ).scalars().all() == [], "the failed-precommit-handler mutation must not persist"
    assert postcommit_seen == [], "a precommit failure must never reach the postcommit bus"

    outbox = services["session"].execute(
        select(ProcurementFinancialOutboxORM)
    ).scalars().all()
    assert all(
        row.status != OutboxDeliveryStatus.PUBLISHED.value for row in outbox
    ), "the delivery must not be marked published when its handler failed"
