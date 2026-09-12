from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import event, select

from src.core.modules.project_management.application.financials.procurement_consumer import (
    PROCUREMENT_FINANCE_PRINCIPAL_NAME,
)
from src.core.modules.project_management.application.financials.commitments.event_handlers.view_invalidation import (
    COMMITMENT_CATEGORY,
)
from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
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
from src.core.platform.infrastructure.persistence.orm.integration.procurement_financial_outbox import (
    ProcurementFinancialOutboxORM,
)
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
    AuditEntryORM,
)
from src.core.platform.integration import (
    PROCUREMENT_COMMITMENT_EVENT_TYPE,
    PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE,
    IntegrationEventEnvelope,
    ProcurementCommitmentEventPayload,
    ProcurementReceiptAccrualEventPayload,
)
from src.core.platform.finance import DecimalQuantityPayload, MonetaryRatePayload


def _setup(services):
    services["service_principal_service"].create_service_principal(
        name=PROCUREMENT_FINANCE_PRINCIPAL_NAME,
        description="Projects Procurement facts into PM Finance.",
        initial_role_name="viewer",
    )
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "Procurement delivery", financial_currency_code=organization.base_currency
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="PROC-DELIVERY", name="Procurement delivery"
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id,
        expected_version=profile.version,
        default_cost_code_id=cost_code.id,
    )
    site = services["site_service"].create_site(
        site_code="PROC-DELIVERY", name="Procurement delivery site",
        currency_code=organization.base_currency,
    )
    supplier = services["party_service"].create_party(
        party_code="PROC-DELIVERY", party_name="Procurement supplier",
        party_type="SUPPLIER",
    )
    services["financial_period_service"].create_period(
        code="PROC-2026-08", name="August 2026", fiscal_year=2026,
        period_number=8, start_date=date(2026, 8, 1), end_date=date(2026, 8, 31),
    )
    services["session"].commit()
    return organization, project, site, supplier


def _envelope(organization, event_type, payload, *, aggregate_id, revision):
    return IntegrationEventEnvelope(
        event_id=str(uuid4()),
        event_type=event_type,
        schema_version=1,
        tenant_id=organization.tenant_id,
        organization_id=organization.id,
        aggregate_type="purchase_order_line" if event_type == PROCUREMENT_COMMITMENT_EVENT_TYPE else "receipt_line",
        aggregate_id=aggregate_id,
        aggregate_version=revision,
        occurred_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
        correlation_id=str(uuid4()),
        payload=payload.model_dump(mode="json"),
    )


def _commitment(
    organization, project, site, supplier, *, revision=1, state="SENT",
    quantity="10", line_id="po-line-delivery",
):
    payload = ProcurementCommitmentEventPayload(
        project_id=project.id,
        purchase_order_id="po-delivery",
        purchase_order_line_id=line_id,
        purchase_order_number="PO-DELIVERY",
        supplier_party_id=supplier.id,
        site_id=site.id,
        state=state,
        source_revision=revision,
        source_content_hash=f"{revision:064x}",
        ordered_quantity=DecimalQuantityPayload(value=quantity, unit="EA"),
        unit_price=MonetaryRatePayload(
            amount="10", currency=organization.base_currency, per_unit="EA"
        ),
        order_date=date(2026, 8, 3),
        expected_delivery_date=date(2026, 8, 20),
    )
    return _envelope(
        organization, PROCUREMENT_COMMITMENT_EVENT_TYPE, payload,
        aggregate_id=payload.purchase_order_line_id, revision=revision,
    )


def _receipt(
    organization, project, site, supplier, *, revision=1, quantity="4",
    suffix="",
):
    payload = ProcurementReceiptAccrualEventPayload(
        project_id=project.id,
        receipt_id=f"receipt-delivery{suffix}",
        receipt_line_id=f"receipt-line-delivery{suffix}",
        receipt_number=f"REC-DELIVERY{suffix}",
        purchase_order_id="po-delivery",
        purchase_order_line_id="po-line-delivery",
        supplier_party_id=supplier.id,
        site_id=site.id,
        source_revision=revision,
        source_content_hash=f"{revision + 100:064x}",
        posted_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
        accepted_quantity=DecimalQuantityPayload(value=quantity, unit="EA"),
        unit_cost=MonetaryRatePayload(
            amount="10", currency=organization.base_currency, per_unit="EA"
        ),
    )
    return _envelope(
        organization, PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE, payload,
        aggregate_id=payload.receipt_line_id, revision=revision,
    )


def _deliver(services, envelope):
    services["procurement_financial_outbox_service"].enqueue(envelope)
    services["session"].commit()
    return services["procurement_financial_dispatcher"].dispatch_pending()


def _measure_delivery_statements(services, envelope):
    services["procurement_financial_outbox_service"].enqueue(envelope)
    services["session"].commit()
    statements = []
    engine = services["session"].get_bind()

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        processed = services["procurement_financial_dispatcher"].dispatch_pending()
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    return processed, len(statements)


def test_procurement_delivery_records_bounded_statement_characterization(services):
    organization, project, site, supplier = _setup(services)
    counts = {}
    events = {
        "create": _commitment(organization, project, site, supplier),
        "revise": _commitment(organization, project, site, supplier, revision=2, quantity="12"),
        "close": _commitment(organization, project, site, supplier, revision=3, state="CLOSED", quantity="12"),
        "stale": _commitment(organization, project, site, supplier, revision=1, quantity="11"),
        "receipt": _receipt(organization, project, site, supplier),
    }
    for name in ("create", "revise", "close"):
        processed, counts[name] = _measure_delivery_statements(services, events[name])
        assert processed == 1
    processed, counts["replay"] = _measure_delivery_statements(services, events["create"])
    assert processed == 0
    processed, counts["stale"] = _measure_delivery_statements(services, events["stale"])
    assert processed == 0
    processed, counts["receipt"] = _measure_delivery_statements(services, events["receipt"])
    assert processed == 1

    print("R6D-E delivery SQL statement counts:", dict(sorted(counts.items())))
    assert all(0 < count < 200 for count in counts.values())


def test_procurement_delivery_projects_receipt_actual_and_match_once(services):
    organization, project, site, supplier = _setup(services)
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope):
            return True

    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), hints.append
    )
    commitment = _commitment(organization, project, site, supplier)
    receipt = _receipt(organization, project, site, supplier)
    assert _deliver(services, commitment) == 1
    assert len([hint for hint in hints if hint.category == COMMITMENT_CATEGORY]) == 1
    hints.clear()
    assert _deliver(services, receipt) == 1
    assert len([hint for hint in hints if hint.category == COMMITMENT_CATEGORY]) == 1

    session = services["session"]
    line = session.execute(select(ProjectCommitmentLineORM)).scalar_one()
    entry = session.execute(select(ProjectCostEntryORM)).scalar_one()
    match = session.execute(select(ProjectCommitmentMatchORM)).scalar_one()
    assert line.amount == Decimal("100")
    assert line.matched_amount == Decimal("40")
    assert entry.amount == Decimal("40")
    assert match.amount == Decimal("40")
    assert match.cost_entry_id == entry.id
    assert session.execute(select(ProjectCommitmentSourceRevisionORM)).scalars().all()
    assert {row.status for row in session.execute(select(ProcurementFinancialOutboxORM)).scalars()} == {"published"}
    assert {row.status for row in session.execute(select(ProjectFinanceInboxORM)).scalars()} == {"processed"}

    principal = services["service_principal_service"].resolve_execution_principal(
        name=PROCUREMENT_FINANCE_PRINCIPAL_NAME
    )
    audits = session.execute(
        select(AuditEntryORM).where(AuditEntryORM.source == "integration_worker")
    ).scalars().all()
    assert audits
    assert all(row.actor_id == principal.id and row.actor_type == "service_principal" for row in audits)

    assert services["procurement_financial_dispatcher"]._consume_under_unit_of_work(receipt).value == "duplicate_processed"
    session.expire_all()
    assert len(session.execute(select(ProjectCostEntryORM)).scalars().all()) == 1
    assert len(session.execute(select(ProjectCommitmentMatchORM)).scalars().all()) == 1


def test_separate_procurement_commits_with_one_correlation_each_invalidate(services):
    organization, project, site, supplier = _setup(services)
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope):
            return True

    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), hints.append
    )
    first = _commitment(organization, project, site, supplier)
    second = _commitment(
        organization, project, site, supplier, line_id="po-line-delivery-2"
    ).model_copy(update={"correlation_id": first.correlation_id})

    assert _deliver(services, first) == 1
    assert _deliver(services, second) == 1
    assert len([hint for hint in hints if hint.category == COMMITMENT_CATEGORY]) == 2


def test_changed_receipt_revision_quarantines_without_double_actual(services):
    organization, project, site, supplier = _setup(services)
    assert _deliver(services, _commitment(organization, project, site, supplier)) == 1
    assert _deliver(services, _receipt(organization, project, site, supplier)) == 1
    assert _deliver(services, _receipt(organization, project, site, supplier, revision=2, quantity="5")) == 0

    session = services["session"]
    assert len(session.execute(select(ProjectCostEntryORM)).scalars().all()) == 1
    assert len(session.execute(select(ProjectCommitmentMatchORM)).scalars().all()) == 1
    assert session.execute(select(ProjectCommitmentLineORM.matched_amount)).scalar_one() == Decimal("40")
    inbox = session.execute(
        select(ProjectFinanceInboxORM).where(ProjectFinanceInboxORM.aggregate_version == 2)
    ).scalar_one()
    assert inbox.status == "quarantined"
    assert inbox.quarantine_reason_code == "PROCUREMENT_RECEIPT_CORRECTION_CONTRACT_REQUIRED"


def test_newer_line_revision_wins_and_terminal_line_remains_visible(services):
    organization, project, site, supplier = _setup(services)
    assert _deliver(services, _commitment(organization, project, site, supplier)) == 1
    assert _deliver(services, _commitment(organization, project, site, supplier, revision=5, quantity="12")) == 1
    assert _deliver(services, _commitment(organization, project, site, supplier, revision=4, quantity="11")) == 0
    session = services["session"]
    line = session.execute(select(ProjectCommitmentLineORM)).scalar_one()
    assert line.source_revision == 5
    assert line.amount == Decimal("120")
    assert len(session.execute(select(ProjectCommitmentSourceRevisionORM)).scalars().all()) == 2

    assert _deliver(services, _commitment(organization, project, site, supplier, revision=6, state="CLOSED", quantity="12")) == 1
    visible = services["commitment_service"].get_line(line.id)
    assert visible.source_revision == 6
    assert visible.remaining_money.amount == 0
    assert len(session.execute(select(ProjectCommitmentLineORM)).scalars().all()) == 1


def test_receipt_match_over_commitment_keeps_actual_and_zero_open(services):
    organization, project, site, supplier = _setup(services)
    assert _deliver(services, _commitment(organization, project, site, supplier)) == 1
    assert _deliver(services, _receipt(organization, project, site, supplier, quantity="12")) == 1
    session = services["session"]
    line = session.execute(select(ProjectCommitmentLineORM)).scalar_one()
    entry = session.execute(select(ProjectCostEntryORM)).scalar_one()
    match = session.execute(select(ProjectCommitmentMatchORM)).scalar_one()
    assert entry.amount == Decimal("120")
    assert match.amount == Decimal("100")
    assert line.matched_amount == Decimal("100")
    assert services["commitment_service"].get_line(line.id).remaining_money.amount == 0


def test_distinct_partial_receipts_reach_full_match_without_duplicate_actual(services):
    organization, project, site, supplier = _setup(services)
    assert _deliver(services, _commitment(organization, project, site, supplier)) == 1
    assert _deliver(services, _receipt(organization, project, site, supplier, quantity="3", suffix="-a")) == 1
    assert _deliver(services, _receipt(organization, project, site, supplier, quantity="7", suffix="-b")) == 1
    session = services["session"]
    line = session.execute(select(ProjectCommitmentLineORM)).scalar_one()
    assert line.matched_amount == Decimal("100")
    assert services["commitment_service"].get_line(line.id).remaining_money.amount == 0
    assert sorted(row.amount for row in session.execute(select(ProjectCostEntryORM)).scalars()) == [
        Decimal("30"), Decimal("70")
    ]
    assert len(session.execute(select(ProjectCommitmentMatchORM)).scalars().all()) == 2


def test_added_po_line_projects_once_without_replacing_existing_line(services):
    organization, project, site, supplier = _setup(services)
    first = _commitment(organization, project, site, supplier)
    second = _commitment(
        organization, project, site, supplier, line_id="po-line-delivery-2"
    )
    assert _deliver(services, first) == 1
    assert _deliver(services, second) == 1
    assert services["procurement_financial_dispatcher"]._consume_under_unit_of_work(second).value == "duplicate_processed"
    session = services["session"]
    assert {row.purchase_order_line_id for row in session.execute(select(ProjectCommitmentLineORM)).scalars()} == {
        "po-line-delivery", "po-line-delivery-2"
    }
    assert len(session.execute(select(ProjectCommitmentSourceRevisionORM)).scalars().all()) == 2


def test_exposure_filter_is_server_scoped_and_paged(services):
    organization, project, site, supplier = _setup(services)
    for line_id in ("po-line-delivery", "po-line-delivery-2", "po-line-delivery-3"):
        assert _deliver(services, _commitment(
            organization, project, site, supplier, line_id=line_id
        )) == 1
    assert _deliver(services, _commitment(
        organization, project, site, supplier, line_id="po-line-delivery-2",
        revision=2, state="CLOSED",
    )) == 1

    api = ProjectManagementFinancialsDesktopApi(
        commitment_service=services["commitment_service"]
    )
    first = api.list_commitments(project.id, exposure="open", limit=1, offset=0)
    second = api.list_commitments(project.id, exposure="open", limit=1, offset=1)
    closed = api.list_commitments(project.id, exposure="none", limit=1)
    assert first.total == second.total == 2
    assert first.items[0].id != second.items[0].id
    assert closed.total == 1
    assert closed.items[0].id not in {first.items[0].id, second.items[0].id}

    from src.core.platform.common.exceptions import ValidationError
    import pytest

    with pytest.raises(ValidationError):
        api.list_commitments(project.id, exposure="unknown")


def test_audit_failure_rolls_back_projection_and_retains_durable_retry(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    organization, project, site, supplier = _setup(services)
    envelope = _commitment(organization, project, site, supplier)
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope):
            return True

    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), hints.append
    )

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit store unavailable")

    monkeypatch.setattr(EnterpriseAuditService, "record", fail_audit)
    assert _deliver(services, envelope) == 0
    session = services["session"]
    assert session.execute(select(ProjectCommitmentLineORM)).scalars().all() == []
    assert session.execute(select(ProjectCommitmentSourceRevisionORM)).scalars().all() == []
    assert [hint for hint in hints if hint.category == COMMITMENT_CATEGORY] == []
    outbox = session.execute(select(ProcurementFinancialOutboxORM)).scalar_one()
    inbox = session.execute(select(ProjectFinanceInboxORM)).scalar_one()
    assert outbox.status == "retry"
    assert inbox.status == "retry"
    assert outbox.last_error_code == "RUNTIMEERROR"
