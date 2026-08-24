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
from src.core.modules.project_management.application.financials.cost.entries import (
    CostEntryApprovalOutcome,
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
    ProjectCostEntryStatus,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.finance.money.money import Money


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user = auth.authenticate(username, password)
    services["user_session"].set_principal(auth.build_principal(user))


def _source(*, command_id: str = "command-1", content_hash: str = "a" * 64):
    return FinancialSourceReference(
        tenant_id="tenant-a",
        organization_id="org-a",
        project_id="project-a",
        source_module=FinancialSourceModule.PROJECT_MANAGEMENT,
        source_type=FinancialSourceType.MANUAL_COMMAND,
        source_id=command_id,
        source_revision="1",
        content_hash=content_hash,
        posting_purpose=FinancialPostingPurpose.MANUAL_ACTUAL,
    )


def _create_project_finance_setup(services):
    organization = services["organization_service"].get_active_organization()
    project = services["project_service"].create_project(
        "Canonical actuals",
        financial_currency_code=organization.base_currency,
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="ACTUAL-LABOR",
        name="Actual labor",
    )
    period = services["financial_period_service"].create_period(
        code="FY26-P01",
        name="January 2026",
        fiscal_year=2026,
        period_number=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    return organization, project, cost_code, period


def _create_draft(services, *, command_id: str = "manual-1", amount: str = "125.50"):
    organization, project, cost_code, period = _create_project_finance_setup(services)
    entry = services["cost_entry_service"].create_manual_entry(
        project_id=project.id,
        command_id=command_id,
        description="Approved labor adjustment",
        amount=Decimal(amount),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 1, 12),
        cost_code_id=cost_code.id,
    )
    return organization, project, cost_code, period, entry


def test_cost_entry_domain_enforces_signed_lifecycle_and_complete_posting_snapshot() -> None:
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        ProjectCostEntry.create_draft(
            tenant_id="tenant-a",
            organization_id="org-a",
            project_id="project-a",
            description="Invalid actual",
            kind=ProjectCostEntryKind.ACTUAL,
            money=Money.of(Decimal("-1"), "EUR"),
            transaction_date=date(2026, 1, 10),
            cost_code_id="cost-code-a",
            source=_source(),
            task_id=None,
            resource_id=None,
            actor_id="user-a",
            occurred_at=now,
        )

    entry = ProjectCostEntry.create_draft(
        tenant_id="tenant-a",
        organization_id="org-a",
        project_id="project-a",
        description="Valid actual",
        kind=ProjectCostEntryKind.ACTUAL,
        money=Money.of(Decimal("10"), "EUR"),
        transaction_date=date(2026, 1, 10),
        cost_code_id="cost-code-a",
        source=_source(),
        task_id=None,
        resource_id=None,
        actor_id="user-a",
        occurred_at=now,
    )
    with pytest.raises(BusinessRuleError):
        entry.approve(actor_id="approver-a", occurred_at=now)
    entry.submit(actor_id="user-a", occurred_at=now)
    entry.approve(actor_id="approver-a", occurred_at=now)
    entry.post(
        actor_id="controller-a",
        occurred_at=now,
        posting_date=date(2026, 1, 10),
        financial_period_id="period-a",
        base_money=Money.of(Decimal("10"), "EUR"),
        exchange_rate=Decimal("1"),
        exchange_rate_date=date(2026, 1, 10),
        exchange_rate_source="identity",
        exchange_rate_captured_at=now,
    )
    assert entry.status == ProjectCostEntryStatus.POSTED
    with pytest.raises(BusinessRuleError):
        entry.update_draft(
            description="Forbidden edit",
            amount=Decimal("11"),
            currency_code="EUR",
            transaction_date=date(2026, 1, 10),
            cost_code_id="cost-code-a",
            task_id=None,
            resource_id=None,
            source_content_hash="b" * 64,
            updated_by="user-a",
            updated_at=now,
        )


def test_manual_entry_lifecycle_is_idempotent_posts_and_reverses_exactly(services) -> None:
    organization, project, cost_code, _period, draft = _create_draft(services)
    service = services["cost_entry_service"]

    replay = service.create_manual_entry(
        project_id=project.id,
        command_id="manual-1",
        description="Approved labor adjustment",
        amount=Decimal("125.50"),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 1, 12),
        cost_code_id=cost_code.id,
    )
    assert replay.id == draft.id
    with pytest.raises(BusinessRuleError) as conflict:
        service.create_manual_entry(
            project_id=project.id,
            command_id="manual-1",
            description="Conflicting replay",
            amount=Decimal("125.50"),
            currency_code=organization.base_currency,
            transaction_date=date(2026, 1, 12),
            cost_code_id=cost_code.id,
        )
    assert conflict.value.code == "PROJECT_COST_ENTRY_SOURCE_REPLAY_CONFLICT"

    submitted = service.submit(draft.id, expected_version=draft.row_version)
    approved_result = service.approve(
        submitted.id,
        expected_version=submitted.row_version,
    )
    assert approved_result.outcome == CostEntryApprovalOutcome.APPLIED
    approved = service.get_entry(draft.id)
    posted = service.post(
        approved.id,
        expected_version=approved.row_version,
        posting_date=date(2026, 1, 15),
    )
    assert posted.status == ProjectCostEntryStatus.POSTED
    assert posted.base_amount == posted.amount
    assert posted.exchange_rate == Decimal("1")

    reversal = service.reverse(
        posted.id,
        expected_version=posted.row_version,
        command_id="reverse-manual-1",
        posting_date=date(2026, 1, 20),
        reason="Correct duplicate source transaction",
    )
    original = service.get_entry(posted.id)
    assert original.status == ProjectCostEntryStatus.REVERSED
    assert original.reversed_by_entry_id == reversal.id
    assert reversal.entry_kind == ProjectCostEntryKind.REVERSAL
    assert reversal.reverses_entry_id == original.id
    assert reversal.amount == -original.amount
    assert reversal.base_amount == -original.base_amount
    assert reversal.exchange_rate == original.exchange_rate
    assert reversal.currency_code == original.currency_code
    assert reversal.base_currency_code == original.base_currency_code
    assert reversal.amount + original.amount == Decimal("0")

    reversal_retry = service.reverse(
        posted.id,
        expected_version=posted.row_version,
        command_id="reverse-manual-1",
        posting_date=date(2026, 1, 20),
        reason="Correct duplicate source transaction",
    )
    assert reversal_retry.id == reversal.id

    entries, total = service.list_for_project(project.id, limit=1)
    assert total == 2
    assert len(entries) == 1


def test_cost_entry_query_pages_and_sorts_before_the_former_fifty_row_cap(
    services,
) -> None:
    organization, project, cost_code, _period = _create_project_finance_setup(services)
    service = services["cost_entry_service"]
    for index in range(55):
        service.create_manual_entry(
            project_id=project.id,
            command_id=f"r17-actual-{index:03d}",
            description=f"Actual {index:03d}",
            amount=Decimal("0.01"),
            currency_code=organization.base_currency,
            transaction_date=date(2026, 1, 12),
            cost_code_id=cost_code.id,
        )

    foreign_project = services["project_service"].create_project(
        "Other scoped actuals",
        financial_currency_code=organization.base_currency,
    )
    service.create_manual_entry(
        project_id=foreign_project.id,
        command_id="r17-foreign-actual",
        description="Foreign Actual",
        amount=Decimal("99.99"),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 1, 12),
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
        cost_entry_service=service
    ).list_cost_entries(
        project.id,
        offset=50,
        limit=10,
        sort_key="title",
        sort_direction="asc",
    )

    assert first_total == third_total == 55
    assert [row.description for row in first_page[:2]] == ["Actual 000", "Actual 001"]
    assert [row.description for row in third_page] == [
        f"Actual {index:03d}" for index in range(40, 55)
    ]
    assert [row.description for row in descending_page] == [
        f"Actual {index:03d}" for index in range(54, 49, -1)
    ]
    assert desktop_page.total == 55
    assert [row.description for row in desktop_page.items] == [
        f"Actual {index:03d}" for index in range(50, 55)
    ]


def test_cross_currency_posting_requires_and_freezes_fx_snapshot(services) -> None:
    organization, project, cost_code, _period = _create_project_finance_setup(services)
    transaction_currency = "USD" if organization.base_currency != "USD" else "EUR"
    service = services["cost_entry_service"]
    draft = service.create_manual_entry(
        project_id=project.id,
        command_id="fx-command",
        description="Imported equipment charge",
        amount=Decimal("100"),
        currency_code=transaction_currency,
        transaction_date=date(2026, 1, 5),
        cost_code_id=cost_code.id,
    )
    submitted = service.submit(draft.id, expected_version=draft.row_version)
    service.approve(submitted.id, expected_version=submitted.row_version)
    approved = service.get_entry(draft.id)
    with pytest.raises(ValidationError) as missing_fx:
        service.post(
            approved.id,
            expected_version=approved.row_version,
            posting_date=date(2026, 1, 8),
        )
    assert missing_fx.value.code == "PROJECT_COST_ENTRY_FX_SNAPSHOT_REQUIRED"

    captured_at = datetime(2026, 1, 8, 9, 0, tzinfo=timezone.utc)
    posted = service.post(
        approved.id,
        expected_version=approved.row_version,
        posting_date=date(2026, 1, 8),
        exchange_rate=Decimal("0.900000000000"),
        exchange_rate_date=date(2026, 1, 8),
        exchange_rate_source="ECB closing rate",
        exchange_rate_captured_at=captured_at,
    )
    assert posted.base_amount == Decimal("90.00")
    assert posted.base_currency_code == organization.base_currency
    assert posted.exchange_rate_source == "ECB closing rate"
    assert posted.exchange_rate_captured_at == captured_at


def test_posting_rejects_closed_period(services) -> None:
    _organization, _project, _cost_code, period, draft = _create_draft(services)
    service = services["cost_entry_service"]
    submitted = service.submit(draft.id, expected_version=draft.row_version)
    service.approve(submitted.id, expected_version=submitted.row_version)
    approved = service.get_entry(draft.id)
    services["financial_period_service"].close_period(
        period.id,
        expected_version=period.version,
    )
    with pytest.raises(BusinessRuleError) as blocked:
        service.post(
            approved.id,
            expected_version=approved.row_version,
            posting_date=date(2026, 1, 15),
        )
    assert blocked.value.code == "FINANCIAL_PERIOD_POSTING_BLOCKED"


def test_governed_cost_approval_applies_as_deciding_principal(
    services, monkeypatch
) -> None:
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "project_cost.approve")
    _organization, project, _cost_code, _period, draft = _create_draft(services)
    service = services["cost_entry_service"]
    submitted = service.submit(draft.id, expected_version=draft.row_version)
    services["auth_service"].register_user(
        "cost-requester",
        "StrongPass123",
        role_names=["planner"],
    )
    _login(services, "cost-requester", "StrongPass123")
    result = service.approve(submitted.id, expected_version=submitted.row_version)
    assert result.outcome == CostEntryApprovalOutcome.PENDING_APPROVAL
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    requester_id = request.requested_by_user_id

    _login(services, "admin", "ChangeMe123!")
    approver_id = services["user_session"].principal.user_id
    services["approval_service"].approve_and_apply(request.id, note="Approved actual")
    approved = service.get_entry(submitted.id)
    assert approved.status == ProjectCostEntryStatus.APPROVED
    assert approved.approved_by == approver_id
    assert approved.approved_by != requester_id


def test_cost_entry_repository_isolates_active_organization(services) -> None:
    _organization, _project, _cost_code, _period, draft = _create_draft(services)
    organization_service = services["organization_service"]
    original = organization_service.get_active_organization()
    other = organization_service.create_organization(
        organization_code="COST2",
        display_name="Second cost organization",
        timezone_name="UTC",
        base_currency="EUR",
        is_active=True,
    )
    organization_service.set_active_organization(other.id)
    try:
        with pytest.raises(NotFoundError) as hidden:
            services["cost_entry_service"].get_entry(draft.id)
        assert getattr(hidden.value, "code", None) == "PROJECT_COST_ENTRY_NOT_FOUND"
    finally:
        organization_service.set_active_organization(original.id)

    assert services["cost_entry_service"].get_entry(draft.id).id == draft.id


def test_cost_entry_migration_installs_database_immutability_guards(tmp_path) -> None:
    database_path = tmp_path / "project-cost-entry-migration.db"
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)

    with engine.begin() as connection:
        triggers = {
            row[0]
            for row in connection.execute(
                sa.text(
                    "SELECT name FROM sqlite_master WHERE type='trigger' "
                    "AND name LIKE 'trg_project_cost_entries_immutable_%'"
                )
            )
        }
        assert triggers == {
            "trg_project_cost_entries_immutable_delete",
            "trg_project_cost_entries_immutable_update",
        }
        tenant_id = "cost-migration-tenant"
        organization_id = "cost-migration-organization"
        connection.execute(
            sa.text(
                "INSERT INTO tenants (id, tenant_code, display_name) VALUES "
                "(:tenant_id, 'COST-MIGRATION', 'Cost Migration Tenant')"
            ),
            {"tenant_id": tenant_id},
        )
        connection.execute(
            sa.text(
                "INSERT INTO organizations "
                "(id, tenant_id, organization_code, display_name) VALUES "
                "(:organization_id, :tenant_id, 'COST-MIGRATION-ORG', "
                "'Cost Migration Organization')"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
        connection.execute(
            sa.text(
                "INSERT INTO projects (id, tenant_id, organization_id, name, description, "
                "status, version) VALUES "
                "('cost-project', :tenant_id, :organization_id, 'Cost Project', '', "
                "'ACTIVE', 1)"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
        connection.execute(
            sa.text(
                "INSERT INTO project_finance_cost_codes "
                "(id, tenant_id, organization_id, code, name, is_active, version, created_at, updated_at) "
                "VALUES ('actual-code', :tenant_id, :organization_id, 'ACTUAL', 'Actual', 1, 1, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
        connection.execute(
            sa.text(
                "INSERT INTO financial_periods "
                "(id, tenant_id, organization_id, code, name, fiscal_year, period_number, "
                "start_date, end_date, status, version, created_by, created_at, updated_at) "
                "VALUES ('period-1', :tenant_id, :organization_id, 'FY26-P01', 'January', 2026, 1, "
                "'2026-01-01', '2026-01-31', 'open', 1, 'admin', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
        connection.execute(
            sa.text(
                "INSERT INTO project_cost_entries "
                "(id, tenant_id, organization_id, project_id, description, entry_kind, status, "
                "amount, currency_code, base_amount, base_currency_code, exchange_rate, "
                "exchange_rate_date, exchange_rate_source, exchange_rate_captured_at, "
                "transaction_date, posting_date, financial_period_id, cost_code_id, source_module, "
                "source_type, source_id, source_revision, source_content_hash, posting_purpose, "
                "idempotency_key, version, created_by, created_at, updated_by, updated_at, "
                "posted_by, posted_at) VALUES "
                "('posted-1', :tenant_id, :organization_id, 'cost-project', 'Posted actual', "
                "'actual', 'posted', 10, 'EUR', 10, 'EUR', 1, '2026-01-10', 'identity', "
                "CURRENT_TIMESTAMP, '2026-01-10', '2026-01-10', 'period-1', 'actual-code', "
                "'project_management', 'manual_command', 'cmd-1', '1', :content_hash, "
                "'manual_actual', :idempotency_key, 1, 'admin', CURRENT_TIMESTAMP, 'admin', "
                "CURRENT_TIMESTAMP, 'admin', CURRENT_TIMESTAMP)"
            ),
            {
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "content_hash": "a" * 64,
                "idempotency_key": "pfin:v1:" + "b" * 64,
            },
        )
        with pytest.raises(sa.exc.IntegrityError):
            connection.execute(
                sa.text("UPDATE project_cost_entries SET amount = 11 WHERE id = 'posted-1'")
            )

    with engine.begin() as connection:
        with pytest.raises(sa.exc.IntegrityError):
            connection.execute(
                sa.text("DELETE FROM project_cost_entries WHERE id = 'posted-1'")
            )

    engine.dispose()
