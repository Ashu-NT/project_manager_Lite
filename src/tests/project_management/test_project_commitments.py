from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
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
from src.core.modules.project_management.domain.financials.commitment import (
    ProjectCommitmentLine,
    ProjectCommitmentLineState,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryKind,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.finance import DecimalQuantityPayload, MonetaryRatePayload, Money


def _setup(services):
    organization = services["organization_service"].get_active_organization()
    project = services["project_service"].create_project(
        "Commitment project", financial_currency_code=organization.base_currency
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="PROCURE", name="Procurement"
    )
    site = services["site_service"].create_site(
        site_code="COMMIT", name="Commitment Site", currency_code=organization.base_currency
    )
    supplier = services["party_service"].create_party(
        party_code="COMMIT-SUP", party_name="Commitment Supplier", party_type="SUPPLIER"
    )
    period = services["financial_period_service"].create_period(
        code="COMMIT-2026-08", name="August 2026", fiscal_year=2026, period_number=8,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 31),
    )
    return organization, project, cost_code, site, supplier, period


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
    source_index: int | None = None,
) -> ProcurementCommitmentFinancialSource:
    suffix = "commit-1" if source_index is None else f"commit-{source_index:03d}"
    reference = FinancialSourceReference(
        tenant_id=organization.tenant_id,
        organization_id=organization.id,
        project_id=project.id,
        source_module=FinancialSourceModule.INVENTORY_PROCUREMENT,
        source_type=FinancialSourceType.PURCHASE_ORDER_LINE,
        source_id=f"po-{suffix}",
        source_line_id=f"po-line-{suffix}",
        source_revision=str(revision),
        content_hash=content_hash or (
            f"{revision:x}" * 64
            if source_index is None
            else f"{source_index:064x}"[-64:]
        ),
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


def _posted_receipt_entry(
    services, *, organization, project, cost_code, period, amount: str = "40"
) -> ProjectCostEntry:
    now = datetime(2026, 8, 10, 10, tzinfo=timezone.utc)
    source = FinancialSourceReference(
        tenant_id=organization.tenant_id,
        organization_id=organization.id,
        project_id=project.id,
        source_module=FinancialSourceModule.INVENTORY_PROCUREMENT,
        source_type=FinancialSourceType.RECEIPT_LINE,
        source_id="receipt-commit-1",
        source_line_id="receipt-line-commit-1",
        source_revision="1",
        content_hash="e" * 64,
        posting_purpose=FinancialPostingPurpose.RECEIPT_ACCRUAL,
    )
    entry = ProjectCostEntry.create_draft(
        tenant_id=organization.tenant_id,
        organization_id=organization.id,
        project_id=project.id,
        description="Posted receipt accrual",
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


def test_commitment_domain_releases_only_closed_or_cancelled_exposure() -> None:
    now = datetime(2026, 8, 3, tzinfo=timezone.utc)
    line = ProjectCommitmentLine(
        id="line-1", tenant_id="tenant-1", organization_id="org-1",
        project_id="project-1", commitment_id="commitment-1",
        purchase_order_line_id="po-line-1", cost_code_id="code-1",
        state=ProjectCommitmentLineState.FULLY_RECEIVED,
        ordered_quantity=Decimal("10"), quantity_unit="EA", unit_price=Decimal("10"),
        amount=Decimal("100"), currency_code="EUR", base_amount=Decimal("100"),
        base_currency_code="EUR", exchange_rate=Decimal("1"),
        exchange_rate_date=date(2026, 8, 3), exchange_rate_source="identity",
        exchange_rate_captured_at=now, source_revision=1,
        source_content_hash="a" * 64, source_idempotency_key="source-1",
        created_by="actor-1", created_at=now, updated_by="actor-1", updated_at=now,
    )
    line.apply_match(Money.of("40", "EUR"), actor_id="actor-1", occurred_at=now)
    assert line.remaining_money.amount == Decimal("60")
    line.state = ProjectCommitmentLineState.CLOSED
    assert line.remaining_money.amount == Decimal("0")
    with pytest.raises(BusinessRuleError):
        line.apply_match(Money.of("70", "EUR"), actor_id="actor-1", occurred_at=now)


def test_source_ingestion_is_versioned_idempotent_and_lifecycle_aware(services) -> None:
    organization, project, cost_code, site, supplier, _period = _setup(services)
    service = services["commitment_service"]
    first_source = _commitment_source(
        organization=organization, project=project, site=site, supplier=supplier, revision=1
    )
    first = service.ingest_procurement_source(first_source, cost_code_id=cost_code.id)
    assert first.amount == Decimal("100.00")
    assert first.remaining_money.amount == Decimal("100.00")

    replay = service.ingest_procurement_source(first_source, cost_code_id=cost_code.id)
    assert replay.id == first.id

    changed = service.ingest_procurement_source(
        _commitment_source(
            organization=organization, project=project, site=site, supplier=supplier,
            revision=3, state=ProcurementCommitmentState.PARTIALLY_RECEIVED, quantity="12",
        ),
        cost_code_id=cost_code.id,
    )
    assert changed.id == first.id
    assert changed.source_revision == 3
    assert changed.amount == Decimal("120.00")

    historical_replay = service.ingest_procurement_source(
        first_source, cost_code_id=cost_code.id
    )
    assert historical_replay.source_revision == 3
    with pytest.raises(BusinessRuleError) as out_of_order:
        service.ingest_procurement_source(
            _commitment_source(
                organization=organization, project=project, site=site, supplier=supplier,
                revision=2, state=ProcurementCommitmentState.PARTIALLY_RECEIVED,
                quantity="11",
            ),
            cost_code_id=cost_code.id,
        )
    assert out_of_order.value.code == "PROJECT_COMMITMENT_SOURCE_OUT_OF_ORDER"
    with pytest.raises(BusinessRuleError) as conflict:
        service.ingest_procurement_source(
            _commitment_source(
                organization=organization, project=project, site=site, supplier=supplier,
                revision=1, content_hash="f" * 64,
            ),
            cost_code_id=cost_code.id,
        )
    assert conflict.value.code == "PROJECT_COMMITMENT_SOURCE_REPLAY_CONFLICT"

    cancelled = service.ingest_procurement_source(
        _commitment_source(
            organization=organization, project=project, site=site, supplier=supplier,
            revision=4, state=ProcurementCommitmentState.CANCELLED, quantity="12",
        ),
        cost_code_id=cost_code.id,
    )
    assert cancelled.remaining_money.amount == Decimal("0")


def test_commitment_query_pages_and_sorts_before_the_former_fifty_row_cap(
    services,
) -> None:
    organization, project, cost_code, site, supplier, _period = _setup(services)
    service = services["commitment_service"]
    for index in range(1, 56):
        service.ingest_procurement_source(
            _commitment_source(
                organization=organization,
                project=project,
                site=site,
                supplier=supplier,
                revision=1,
                source_index=index,
            ),
            cost_code_id=cost_code.id,
        )

    first_page, first_total = service.list_for_project(
        project.id,
        offset=0,
        limit=20,
        sort_key="title",
        sort_direction="asc",
    )
    third_page, third_total = service.list_for_project(
        project.id,
        offset=40,
        limit=20,
        sort_key="title",
        sort_direction="asc",
    )
    descending_page, _ = service.list_for_project(
        project.id,
        offset=0,
        limit=5,
        sort_key="title",
        sort_direction="desc",
    )
    desktop_page = ProjectManagementFinancialsDesktopApi(
        commitment_service=service
    ).list_commitments(
        project.id,
        offset=50,
        limit=10,
        sort_key="title",
        sort_direction="asc",
    )

    assert first_total == third_total == 55
    assert [row.purchase_order_line_id for row in first_page[:2]] == [
        "po-line-commit-001",
        "po-line-commit-002",
    ]
    assert [row.purchase_order_line_id for row in third_page] == [
        f"po-line-commit-{index:03d}" for index in range(41, 56)
    ]
    assert [row.purchase_order_line_id for row in descending_page] == [
        f"po-line-commit-{index:03d}" for index in range(55, 50, -1)
    ]
    assert desktop_page.total == 55
    assert [row.purchase_order_line_id for row in desktop_page.items] == [
        f"po-line-commit-{index:03d}" for index in range(51, 56)
    ]


def test_posted_receipt_actual_matches_once_and_reduces_remaining(services) -> None:
    organization, project, cost_code, site, supplier, period = _setup(services)
    service = services["commitment_service"]
    line = service.ingest_procurement_source(
        _commitment_source(
            organization=organization, project=project, site=site, supplier=supplier, revision=1
        ),
        cost_code_id=cost_code.id,
    )
    entry = _posted_receipt_entry(
        services, organization=organization, project=project,
        cost_code=cost_code, period=period,
    )
    match = service.match_cost_entry(line_id=line.id, cost_entry_id=entry.id)
    replay = service.match_cost_entry(line_id=line.id, cost_entry_id=entry.id)
    assert replay.id == match.id
    refreshed = service.get_line(line.id)
    assert refreshed.matched_amount == Decimal("40.00")
    assert refreshed.remaining_money.amount == Decimal("60.00")
    snapshot = services["finance_service"].get_finance_snapshot(
        project.id, as_of=date(2026, 8, 31)
    )
    assert snapshot.committed == Decimal("60.00")
    assert snapshot.actual == Decimal("40.00")
    assert snapshot.exposure == Decimal("100.00")


def test_commitment_repository_isolates_active_organization(services) -> None:
    organization, project, cost_code, site, supplier, _period = _setup(services)
    line = services["commitment_service"].ingest_procurement_source(
        _commitment_source(
            organization=organization, project=project, site=site, supplier=supplier, revision=1
        ),
        cost_code_id=cost_code.id,
    )
    organization_service = services["organization_service"]
    other = organization_service.create_organization(
        organization_code="COMMIT2", display_name="Second commitment organization",
        timezone_name="UTC", base_currency="EUR", is_enabled=True,
    )
    organization_service.enable_organization(other.id)
    services["tenant_context_service"].set_active_organization(other.id)
    try:
        with pytest.raises(NotFoundError):
            services["commitment_service"].get_line(line.id)
    finally:
        organization_service.enable_organization(organization.id)
        services["tenant_context_service"].set_active_organization(organization.id)
    assert services["commitment_service"].get_line(line.id).id == line.id


def test_commitment_migration_installs_immutable_revision_and_match_guards(tmp_path) -> None:
    database_path = tmp_path / "project-commitment-migration.db"
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    with engine.begin() as connection:
        tables = set(sa.inspect(connection).get_table_names())
        assert {
            "project_commitments", "project_commitment_lines",
            "project_commitment_source_revisions", "project_commitment_matches",
        } <= tables
        triggers = {
            row[0]
            for row in connection.execute(
                sa.text(
                    "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                    "AND name LIKE 'trg_project_commitment_%_immutable_%'"
                )
            )
        }
    assert "trg_project_commitment_source_revisions_immutable_update" in triggers
    assert "trg_project_commitment_matches_immutable_delete" in triggers
    engine.dispose()

    command.downgrade(config, "base")
    downgraded_engine = sa.create_engine(
        config.get_main_option("sqlalchemy.url"), future=True
    )
    with downgraded_engine.begin() as connection:
        downgraded_tables = set(sa.inspect(connection).get_table_names())
    assert "project_cost_entries" not in downgraded_tables
    assert "project_commitments" not in downgraded_tables
    assert "project_commitment_lines" not in downgraded_tables
    assert "project_commitment_source_revisions" not in downgraded_tables
    assert "project_commitment_matches" not in downgraded_tables
    downgraded_engine.dispose()
