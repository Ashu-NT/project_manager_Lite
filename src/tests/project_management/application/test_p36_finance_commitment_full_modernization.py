"""Commitment projection events, invalidation, worker ownership, and concurrency guards."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.financials.commitments.commitment_events import (
    CommitmentLineChangeType,
    CommitmentLineChanged,
    CommitmentMatchChangeType,
    CommitmentMatchChanged,
)
from src.core.modules.project_management.application.financials.commitments.event_handlers.view_invalidation import (
    COMMITMENT_CATEGORY,
    COMMITMENT_LIST_SCOPE_CODE,
    build_commitment_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.procurement_consumer import (
    PROCUREMENT_FINANCE_PRINCIPAL_NAME,
    ProcurementExecutionContext,
)
from src.core.modules.project_management.contracts.financial_sources.procurement import (
    ProcurementCommitmentFinancialSource,
    ProcurementCommitmentState,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceReference,
    FinancialSourceType,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryKind,
)
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError
from src.core.platform.finance import DecimalQuantityPayload, MonetaryRatePayload, Money
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import ResourceScope
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog


def _pm_catalog(services) -> ProjectManagementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)


def _spy_hints(services):
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )
    return hints


def _commitment_hints(hints):
    return [h for h in hints if h.category == COMMITMENT_CATEGORY]


def _setup(services):
    if not any(
        principal.name == PROCUREMENT_FINANCE_PRINCIPAL_NAME
        for principal in services["service_principal_service"].list_service_principals()
    ):
        services["service_principal_service"].create_service_principal(
            name=PROCUREMENT_FINANCE_PRINCIPAL_NAME,
            description="Projects Procurement facts into PM Finance.",
            initial_role_name="viewer",
        )
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "P36 Commitment project", financial_currency_code=organization.base_currency
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="P36-PROCURE", name="P36 Procurement"
    )
    site = services["site_service"].create_site(
        site_code="P36-COMMIT", name="P36 Commitment Site", currency_code=organization.base_currency
    )
    supplier = services["party_service"].create_party(
        party_code="P36-COMMIT-SUP", party_name="P36 Commitment Supplier", party_type="SUPPLIER"
    )
    period = services["financial_period_service"].create_period(
        code="P36-COMMIT-2026-08", name="August 2026", fiscal_year=2026, period_number=8,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 31),
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id,
        expected_version=profile.version,
        default_cost_code_id=cost_code.id,
    )
    return organization, project, cost_code, site, supplier, period


def _apply_source(services, source):
    principal = services["service_principal_service"].resolve_execution_principal(
        name=PROCUREMENT_FINANCE_PRINCIPAL_NAME
    )
    reference = source.reference
    services["commitment_service"].apply_procurement_source(
        source,
        execution=ProcurementExecutionContext(
            service_principal=principal,
            source_event_id=f"event-{reference.idempotency_key}",
            source_event_type="inventory_procurement.purchase_order_line.financial_state.v1",
            source_aggregate_id=source.purchase_order_line_id,
            source_revision=int(reference.source_revision),
            correlation_id=f"correlation-{reference.idempotency_key}",
            causation_id=None,
        ),
    )
    services["session"].commit()
    return services["commitment_service"]._commitment_repo.get_line_by_source(
        source.purchase_order_id,
        source.purchase_order_line_id,
    )


def _commitment_source(
    *,
    organization,
    project,
    site,
    supplier,
    revision: int,
    state: ProcurementCommitmentState = ProcurementCommitmentState.SENT,
    quantity: str = "10",
    content_hash: str | None = None,
    suffix: str = "p36-commit-1",
) -> ProcurementCommitmentFinancialSource:
    reference = FinancialSourceReference(
        tenant_id=organization.tenant_id,
        organization_id=organization.id,
        project_id=project.id,
        source_module=FinancialSourceModule.INVENTORY_PROCUREMENT,
        source_type=FinancialSourceType.PURCHASE_ORDER_LINE,
        source_id=f"po-{suffix}",
        source_line_id=f"po-line-{suffix}",
        source_revision=str(revision),
        content_hash=content_hash or (f"{revision:x}" * 64),
        posting_purpose=FinancialPostingPurpose.PURCHASE_COMMITMENT,
    )
    return ProcurementCommitmentFinancialSource(
        reference=reference,
        purchase_order_id=f"po-{suffix}",
        purchase_order_line_id=f"po-line-{suffix}",
        purchase_order_number=f"PO-{suffix.upper()}",
        supplier_party_id=supplier.id,
        site_id=site.id,
        state=state,
        ordered_quantity=DecimalQuantityPayload(value=quantity, unit="EA"),
        unit_price=MonetaryRatePayload(
            amount="10", currency=organization.base_currency, per_unit="EA"
        ),
        order_date=date(2026, 8, 3),
        expected_delivery_date=date(2026, 8, 20),
    )


def _posted_receipt_entry(services, *, organization, project, cost_code, period, amount: str = "40"):
    now = datetime(2026, 8, 10, 10, tzinfo=timezone.utc)
    source = FinancialSourceReference(
        tenant_id=organization.tenant_id,
        organization_id=organization.id,
        project_id=project.id,
        source_module=FinancialSourceModule.INVENTORY_PROCUREMENT,
        source_type=FinancialSourceType.RECEIPT_LINE,
        source_id="p36-receipt-commit-1",
        source_line_id="p36-receipt-line-commit-1",
        source_revision="1",
        content_hash="e" * 64,
        posting_purpose=FinancialPostingPurpose.RECEIPT_ACCRUAL,
    )
    entry = ProjectCostEntry.create_draft(
        tenant_id=organization.tenant_id,
        organization_id=organization.id,
        project_id=project.id,
        description="P36 posted receipt accrual",
        kind=ProjectCostEntryKind.ACTUAL,
        money=Money.of(amount, organization.base_currency),
        transaction_date=date(2026, 8, 10),
        cost_code_id=cost_code.id,
        source=source,
        task_id=None,
        resource_id=None,
        actor_id=services["user_session"].principal.user_id,
        occurred_at=now,
    )
    entry.submit(actor_id=entry.created_by, occurred_at=now)
    entry.approve(actor_id=entry.created_by, occurred_at=now)
    entry.post(
        actor_id=entry.created_by,
        occurred_at=now,
        posting_date=date(2026, 8, 10),
        financial_period_id=period.id,
        base_money=Money.of(amount, organization.base_currency),
        exchange_rate=Decimal("1"),
        exchange_rate_date=date(2026, 8, 10),
        exchange_rate_source="identity",
        exchange_rate_captured_at=now,
    )
    services["cost_entry_service"]._entry_repo.add(entry)
    services["session"].commit()
    return entry


# ---------------------------------------------------------------------------
# ViewInvalidation handler: unit-level mapping/dedupe (both event types share one target)
# ---------------------------------------------------------------------------


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def test_line_changed_maps_to_single_project_scoped_target():
    channel = _fake_channel()
    handler = build_commitment_view_invalidation_handler(channel)
    event = CommitmentLineChanged(
        tenant_id="t1", organization_id="o1", project_id="p1",
        commitment_line_id="line-1", change_type=CommitmentLineChangeType.CREATED,
        occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="c1"))
    assert len(channel.notified) == 1
    hint = channel.notified[0]
    assert hint.scope_code == COMMITMENT_LIST_SCOPE_CODE
    assert isinstance(hint.scope, ResourceScope)
    assert hint.scope.module_code == "project_management"
    assert hint.scope.entity_type == "project"
    assert hint.scope.entity_id == "p1"
    assert hint.entity_id == "p1"


def test_match_changed_maps_to_the_same_single_target():
    channel = _fake_channel()
    handler = build_commitment_view_invalidation_handler(channel)
    event = CommitmentMatchChanged(
        tenant_id="t1", organization_id="o1", project_id="p1",
        commitment_line_id="line-1", match_id="match-1",
        change_type=CommitmentMatchChangeType.MATCHED,
        occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="c2"))
    assert len(channel.notified) == 1
    assert channel.notified[0].scope_code == COMMITMENT_LIST_SCOPE_CODE


def test_dedupe_by_target_within_one_transaction_across_both_event_types():
    channel = _fake_channel()
    handler = build_commitment_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    handler(
        CommitmentLineChanged(
            tenant_id="t1", organization_id="o1", project_id="p1",
            commitment_line_id="line-1", change_type=CommitmentLineChangeType.CREATED,
            occurred_at=now,
        ),
        DomainEventContext(correlation_id="same-tx"),
    )
    handler(
        CommitmentMatchChanged(
            tenant_id="t1", organization_id="o1", project_id="p1",
            commitment_line_id="line-1", match_id="match-1",
            change_type=CommitmentMatchChangeType.MATCHED,
            occurred_at=now,
        ),
        DomainEventContext(correlation_id="same-tx"),
    )
    assert len(channel.notified) == 1, "same project target within one transaction coalesces"

    handler(
        CommitmentLineChanged(
            tenant_id="t1", organization_id="o1", project_id="p1",
            commitment_line_id="line-1", change_type=CommitmentLineChangeType.REVISED,
            occurred_at=now,
        ),
        DomainEventContext(correlation_id="next-tx"),
    )
    assert len(channel.notified) == 2, "a new transaction is never coalesced with the previous one"


# ---------------------------------------------------------------------------
# Real producer path -- Procurement-inbox (dispatcher-owned raw instance)
# ---------------------------------------------------------------------------


def test_dispatcher_builds_procurement_consumer_inside_fresh_finance_uow(services):
    dispatcher = services["procurement_financial_dispatcher"]

    assert not hasattr(dispatcher, "_consumer")
    assert dispatcher._uow_factory is not None
    assert callable(dispatcher._consumer_factory)
    assert callable(dispatcher._principal_resolver)
    service = services["commitment_service"]
    assert not hasattr(service, "ingest_procurement_source")
    assert not hasattr(service, "match_cost_entry")
    assert not hasattr(service, "reverse_match")
    assert not hasattr(services["finance_governance_commands"], "commitment")


# ---------------------------------------------------------------------------
# Concurrency -- preserved, unweakened
# ---------------------------------------------------------------------------


def test_concurrent_line_update_second_writer_rejected(services, session):
    """The pre-existing pessimistic (`for_update`) plus optimistic (`expected_row_version`)
    defense-in-depth concurrency guard on `ProjectCommitmentLine` is exercised directly at the
    repository layer, unchanged by P36's transaction-convergence work."""
    from sqlalchemy.orm import sessionmaker

    from src.core.modules.project_management.infrastructure.persistence.repositories.finance.commitments.commitment import (
        SqlAlchemyProjectCommitmentRepository,
    )

    organization, project, cost_code, site, supplier, _period = _setup(services)
    service = services["commitment_service"]
    line = _apply_source(
        services,
        _commitment_source(
            organization=organization, project=project, site=site, supplier=supplier, revision=1
        ),
    )
    assert line.row_version == 1

    repo_a = SqlAlchemyProjectCommitmentRepository(session)
    repo_a._tenant_context_service = services["tenant_context_service"]
    session_b = sessionmaker(bind=session.bind, future=True)()
    try:
        repo_b = SqlAlchemyProjectCommitmentRepository(session_b)
        repo_b._tenant_context_service = services["tenant_context_service"]
        read_by_a = repo_a.get_line(line.id)
        read_by_b = repo_b.get_line(line.id)
        assert read_by_a.row_version == read_by_b.row_version == 1

        read_by_a.task_id = None
        repo_a.update_line(read_by_a, expected_row_version=1)
        session.commit()

        with pytest.raises(ConcurrencyError):
            repo_b.update_line(read_by_b, expected_row_version=1)
        session_b.rollback()
    finally:
        session_b.close()


# ---------------------------------------------------------------------------
# UI: FinancialsWorkspaceController narrow per-target destination invalidation
# ---------------------------------------------------------------------------


def test_financials_controller_commitment_stale_invalidates_the_legacy_five_destinations(services):
    """Preserves the exact same 5-destination legacy fan-out the retired `commitments_changed`
    signal drove (`financials_refresh_mixin.py`'s former `_commitments_changed` callback)."""
    catalog = _pm_catalog(services)
    controller = catalog.financialsWorkspace
    controller._set_selected_project_id("proj-a")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onCommitmentStale("proj-a")
    assert controller._invalidated_destinations == {
        "overview", "planning", "costs", "performance", "commercial"
    }

    controller._invalidated_destinations.clear()
    controller.onCommitmentStale("proj-b")
    assert controller._invalidated_destinations == set(), "non-selected project must not invalidate"
