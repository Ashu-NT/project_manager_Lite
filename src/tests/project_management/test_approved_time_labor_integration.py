from datetime import date
from decimal import Decimal

from sqlalchemy import select
from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa

from src.core.modules.project_management.domain.financials.cost_entry import ProjectCostEntryStatus
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.modules.project_management.infrastructure.persistence.orm.labor_posting import ApprovedTimeLaborPostingORM
from src.core.platform.integration import InboxProcessingStatus, OutboxDeliveryStatus
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus
from src.core.platform.common.exceptions import ConcurrencyError
from src.core.platform.infrastructure.persistence.orm.time_management.time_financial_outbox import TimeFinancialOutboxORM
from src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox import ProjectFinanceInboxORM
from src.core.shared.events.domain_events import domain_events


def _setup(services):
    organization = services["organization_service"].get_active_organization()
    project = services["project_service"].create_project(
        "Approved Time Finance", financial_currency_code=organization.base_currency
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="LABOR-ACTUAL", name="Labor actual"
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id,
        expected_version=profile.version,
        default_cost_code_id=cost_code.id,
    )
    services["financial_period_service"].create_period(
        code="LABOR-2026-05", name="May 2026", fiscal_year=2026,
        period_number=5, start_date=date(2026, 5, 1), end_date=date(2026, 5, 31),
    )
    resource = services["resource_service"].create_resource(
        "Approved Time Engineer", hourly_rate=0, currency_code=organization.base_currency
    )
    card = services["rate_card_service"].create_rate_card(
        name="Approved Time rates", project_id=project.id
    )
    services["rate_card_service"].create_line(
        card.id, rate_type=RateType.COST, unit="HOUR", rate_amount=Decimal("50"),
        rate_currency=organization.base_currency, resource_id=resource.id,
    )
    task = services["task_service"].create_task(
        project.id, "Approved Time Task", start_date=date(2026, 5, 1), duration_days=10
    )
    assignment = services["task_service"].assign_resource(
        task.id, resource.id, allocation_percent=100
    )
    return organization, project, resource, task, assignment


def test_approved_time_posts_once_and_correction_reverses_and_replaces(services) -> None:
    _, project, resource, _, assignment = _setup(services)
    tasks = services["task_service"]
    time = services["timesheet_service"]
    entry = tasks.add_time_entry(
        assignment.id, entry_date=date(2026, 5, 4), hours=Decimal("4"), note="Initial"
    )
    submitted = time.submit_timesheet_period(resource.id, period_start=date(2026, 5, 1))
    approved = time.approve_timesheet_period(
        submitted.period_id, expected_version=submitted.version, note="Approved"
    )
    assert approved.locked_at is None

    rows, total = services["cost_entry_service"].list_for_project(project.id)
    outbox_debug = services["session"].execute(select(TimeFinancialOutboxORM)).scalars().all()
    assert total == 1, [
        (row.status, row.last_error_code, row.last_error_message) for row in outbox_debug
    ]
    assert rows[0].status is ProjectCostEntryStatus.POSTED
    assert rows[0].amount == Decimal("200.0000")

    session = services["session"]
    labor = session.execute(select(ApprovedTimeLaborPostingORM)).scalar_one()
    assert labor.source_revision == 1
    assert labor.hours == Decimal("4.0000")
    assert labor.rate_amount == Decimal("50.000000")
    assert session.execute(select(TimeFinancialOutboxORM.status)).scalar_one() == OutboxDeliveryStatus.PUBLISHED.value
    assert session.execute(select(ProjectFinanceInboxORM.status)).scalar_one() == InboxProcessingStatus.PROCESSED.value

    locked = time.lock_timesheet_period(
        approved.period_id, expected_version=approved.version
    )
    assert locked.status.value == "LOCKED"
    _, unchanged_total = services["cost_entry_service"].list_for_project(project.id)
    assert unchanged_total == 1
    unlocked = time.unlock_timesheet_period(
        locked.period_id,
        expected_version=locked.version,
        note="Unlock correction control",
    )
    reopened = time.reopen_approved_timesheet_period_for_correction(
        unlocked.period_id,
        expected_version=unlocked.version,
        note="Correct entered hours",
    )
    assert reopened.status.value == "OPEN"
    tasks.update_time_entry(
        entry.id,
        expected_version=entry.version,
        hours=Decimal("5"),
        note="Corrected",
    )
    resubmitted = time.submit_timesheet_period(resource.id, period_start=date(2026, 5, 1))
    time.approve_timesheet_period(
        resubmitted.period_id,
        expected_version=resubmitted.version,
        note="Correction approved",
    )

    rows, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 3
    statuses = sorted(row.status.value for row in rows)
    assert statuses == ["posted", "posted", "reversed"]
    assert sum(row.amount for row in rows) == Decimal("250.0000")
    revisions = session.execute(
        select(ApprovedTimeLaborPostingORM).order_by(ApprovedTimeLaborPostingORM.source_revision)
    ).scalars().all()
    assert [row.source_revision for row in revisions] == [1, 2]
    assert revisions[1].reversal_cost_entry_id is not None


def test_rejected_time_creates_no_financial_delivery(services) -> None:
    _, _, resource, _, assignment = _setup(services)
    time = services["timesheet_service"]
    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 5), hours=Decimal("2")
    )
    submitted = time.submit_timesheet_period(resource.id, period_start=date(2026, 5, 1))
    time.reject_timesheet_period(
        submitted.period_id,
        expected_version=submitted.version,
        note="Needs correction",
    )
    assert services["session"].execute(select(TimeFinancialOutboxORM)).scalars().all() == []


def test_approval_rolls_back_when_atomic_outbox_write_fails(services, monkeypatch) -> None:
    _, _, resource, _, assignment = _setup(services)
    time = services["timesheet_service"]
    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 6), hours=Decimal("3")
    )
    submitted = time.submit_timesheet_period(resource.id, period_start=date(2026, 5, 1))

    def _fail(_envelope):
        raise RuntimeError("outbox unavailable")

    monkeypatch.setattr(services["time_financial_outbox_service"], "enqueue", _fail)
    with pytest.raises(RuntimeError, match="outbox unavailable"):
        time.approve_timesheet_period(
            submitted.period_id, expected_version=submitted.version
        )
    persisted = services["timesheet_service"]._timesheet_period_repo.get(submitted.period_id)
    assert persisted.status is TimesheetPeriodStatus.SUBMITTED
    assert services["session"].execute(select(TimeFinancialOutboxORM)).scalars().all() == []


def test_stale_reviewer_cannot_overwrite_an_approved_period(services) -> None:
    _, _, resource, _, assignment = _setup(services)
    time = services["timesheet_service"]
    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 9), hours=Decimal("3")
    )
    submitted = time.submit_timesheet_period(
        resource.id, period_start=date(2026, 5, 1)
    )
    approved = time.approve_timesheet_period(
        submitted.period_id, expected_version=submitted.version
    )

    with pytest.raises(ConcurrencyError) as error:
        time.reject_timesheet_period(
            submitted.period_id,
            expected_version=submitted.version,
            note="Stale return attempt",
        )

    assert error.value.code == "TIMESHEET_PERIOD_STALE"
    persisted = time._timesheet_period_repo.get(submitted.period_id)
    assert persisted.status is TimesheetPeriodStatus.APPROVED
    assert persisted.version == approved.version


def test_audit_failure_rolls_back_transition_version_and_outbox(services, monkeypatch) -> None:
    _, _, resource, _, assignment = _setup(services)
    time = services["timesheet_service"]
    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 10), hours=Decimal("3")
    )
    submitted = time.submit_timesheet_period(
        resource.id, period_start=date(2026, 5, 1)
    )

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        "src.core.platform.application.time_management.time.timesheet_periods.record_audit_entry",
        fail_audit,
    )
    with pytest.raises(RuntimeError, match="audit unavailable"):
        time.approve_timesheet_period(
            submitted.period_id, expected_version=submitted.version
        )

    persisted = time._timesheet_period_repo.get(submitted.period_id)
    assert persisted.status is TimesheetPeriodStatus.SUBMITTED
    assert persisted.version == submitted.version
    assert services["session"].execute(select(TimeFinancialOutboxORM)).scalars().all() == []


def test_closed_financial_period_keeps_approved_time_retryable_without_posting(services) -> None:
    _, project, resource, _, assignment = _setup(services)
    period_service = services["financial_period_service"]
    financial_period = period_service.list_periods()[0]
    period_service.close_period(financial_period.id, expected_version=financial_period.version)

    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 7), hours=Decimal("2")
    )
    submitted = services["timesheet_service"].submit_timesheet_period(
        resource.id, period_start=date(2026, 5, 1)
    )
    approved = services["timesheet_service"].approve_timesheet_period(
        submitted.period_id,
        expected_version=submitted.version,
        note="Approved source fact",
    )

    assert approved.status is TimesheetPeriodStatus.APPROVED
    _, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 0
    outbox = services["session"].execute(select(TimeFinancialOutboxORM)).scalar_one()
    assert outbox.status == OutboxDeliveryStatus.RETRY.value
    assert outbox.last_error_code == "FINANCIAL_PERIOD_POSTING_BLOCKED"
    inbox = services["session"].execute(select(ProjectFinanceInboxORM)).scalar_one()
    assert inbox.status == InboxProcessingStatus.RETRY.value
    assert inbox.last_error_code == "FINANCIAL_PERIOD_POSTING_BLOCKED"


def test_post_commit_ui_refresh_failure_does_not_retry_financial_delivery(services) -> None:
    _, project, resource, _, assignment = _setup(services)
    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 8), hours=Decimal("1")
    )
    submitted = services["timesheet_service"].submit_timesheet_period(
        resource.id, period_start=date(2026, 5, 1)
    )

    def _fail_refresh(_project_id: str) -> None:
        raise RuntimeError("local refresh unavailable")

    domain_events.cost_entries_changed.connect(_fail_refresh)
    try:
        services["timesheet_service"].approve_timesheet_period(
            submitted.period_id, expected_version=submitted.version
        )
    finally:
        domain_events.cost_entries_changed.disconnect(_fail_refresh)

    _, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 1
    outbox = services["session"].execute(select(TimeFinancialOutboxORM)).scalar_one()
    inbox = services["session"].execute(select(ProjectFinanceInboxORM)).scalar_one()
    assert outbox.status == OutboxDeliveryStatus.PUBLISHED.value
    assert outbox.last_error_code is None
    assert inbox.status == InboxProcessingStatus.PROCESSED.value


def test_labor_posting_migration_is_reversible_and_immutable(tmp_path) -> None:
    database_path = tmp_path / "approved-time-labor.db"
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert "project_approved_time_labor_postings" in sa.inspect(engine).get_table_names()
    with engine.connect() as connection:
        triggers = set(connection.execute(sa.text(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'trg_project_approved_time_labor_postings_immutable_%'"
        )).scalars())
    assert triggers == {
        "trg_project_approved_time_labor_postings_immutable_update",
        "trg_project_approved_time_labor_postings_immutable_delete",
    }
    engine.dispose()
    command.downgrade(config, "base")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert "project_approved_time_labor_postings" not in sa.inspect(engine).get_table_names()
    engine.dispose()
