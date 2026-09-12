from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa

from src.core.modules.project_management.domain.financials.cost_entry import ProjectCostEntryStatus
from src.core.modules.project_management.application.financials.cost.entries.approved_time_consumer import (
    APPROVED_TIME_FINANCE_PRINCIPAL_NAME,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.modules.project_management.contracts.reads.financials.models.finance_integration_facts import (
    ApprovedTimePostingFailureQuery,
)
from src.core.modules.project_management.infrastructure.persistence.orm.labor_posting import ApprovedTimeLaborPostingORM
from src.core.platform.integration import InboxProcessingStatus, OutboxDeliveryStatus
from src.core.platform.integration import IntegrationEventEnvelope
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus
from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.core.platform.common.exceptions import ConcurrencyError
from src.core.platform.infrastructure.persistence.orm.time_management.time_financial_outbox import TimeFinancialOutboxORM
from src.core.modules.project_management.infrastructure.persistence.orm.finance_inbox import ProjectFinanceInboxORM
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import AuditEntryORM


def _setup(services):
    principals = services["service_principal_service"].list_service_principals()
    if not any(
        principal.name == APPROVED_TIME_FINANCE_PRINCIPAL_NAME
        for principal in principals
    ):
        services["service_principal_service"].create_service_principal(
            name=APPROVED_TIME_FINANCE_PRINCIPAL_NAME,
            description="Posts approved Time facts into PM Finance labor actuals.",
            initial_role_name="viewer",
        )
    organization = services["tenant_context_service"].get_active_organization()
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


def _approve_without_immediate_dispatch(services, *, resource_id, assignment_id):
    services["timesheet_service"].set_approved_time_dispatcher(None)
    services["task_service"].add_time_entry(
        assignment_id,
        entry_date=date(2026, 5, 11),
        hours=Decimal("2"),
    )
    submitted = services["timesheet_service"].submit_timesheet_period(
        resource_id,
        period_start=date(2026, 5, 1),
    )
    services["timesheet_service"].approve_timesheet_period(
        submitted.period_id,
        expected_version=submitted.version,
    )
    row = services["session"].execute(select(TimeFinancialOutboxORM)).scalar_one()
    return row, IntegrationEventEnvelope.model_validate_json(row.envelope_json)


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
    assert labor.rate_base_amount == Decimal("50.000000")
    assert labor.rate_origin == "configured"
    assert labor.rate_line_version == 1
    assert labor.rate_provenance_complete is True
    assert labor.worker_service_principal_id is not None
    assert labor.source_event_id is not None
    principal = services["service_principal_service"].resolve_execution_principal(
        name=APPROVED_TIME_FINANCE_PRINCIPAL_NAME
    )
    assert labor.worker_service_principal_id == principal.id
    audit = session.execute(
        select(AuditEntryORM).where(
            AuditEntryORM.operation == "project_cost_entry.post_approved_time"
        )
    ).scalar_one()
    assert audit.actor_id == principal.id
    assert audit.actor_type == "service_principal"
    assert audit.actor_username == APPROVED_TIME_FINANCE_PRINCIPAL_NAME
    assert audit.request_id == labor.correlation_id
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


def test_post_commit_delivery_emits_scoped_refresh_after_durable_processing(services) -> None:
    from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
        CostEntryRecorded,
    )

    _, project, resource, _, assignment = _setup(services)
    events: list[object] = []

    post_commit_bus = services["approved_time_financial_dispatcher"]._post_commit_bus
    subscription = post_commit_bus.subscribe(
        CostEntryRecorded, lambda e, c: events.append(e)
    )
    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 8), hours=Decimal("1")
    )
    submitted = services["timesheet_service"].submit_timesheet_period(
        resource.id, period_start=date(2026, 5, 1)
    )

    try:
        services["timesheet_service"].approve_timesheet_period(
            submitted.period_id, expected_version=submitted.version
        )
    finally:
        subscription.dispose()

    _, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 1
    outbox = services["session"].execute(select(TimeFinancialOutboxORM)).scalar_one()
    inbox = services["session"].execute(select(ProjectFinanceInboxORM)).scalar_one()
    assert outbox.status == OutboxDeliveryStatus.PUBLISHED.value
    assert outbox.last_error_code is None
    assert inbox.status == InboxProcessingStatus.PROCESSED.value
    assert len(events) == 1
    assert events[0].project_id == project.id
    assert events[0].tenant_id == inbox.tenant_id
    assert events[0].organization_id == inbox.organization_id


def test_refresh_subscriber_failure_does_not_retry_approved_time_delivery(services) -> None:
    from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
        CostEntryRecorded,
    )

    _, project, resource, _, assignment = _setup(services)

    def fail_refresh(_event, _context) -> None:
        raise RuntimeError("presentation refresh unavailable")

    post_commit_bus = services["approved_time_financial_dispatcher"]._post_commit_bus
    subscription = post_commit_bus.subscribe(CostEntryRecorded, fail_refresh)
    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 9), hours=Decimal("1")
    )
    submitted = services["timesheet_service"].submit_timesheet_period(
        resource.id, period_start=date(2026, 5, 1)
    )
    try:
        approved = services["timesheet_service"].approve_timesheet_period(
            submitted.period_id, expected_version=submitted.version
        )
    finally:
        subscription.dispose()

    assert approved.status is TimesheetPeriodStatus.APPROVED
    _, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 1
    outbox = services["session"].execute(select(TimeFinancialOutboxORM)).scalar_one()
    inbox = services["session"].execute(select(ProjectFinanceInboxORM)).scalar_one()
    assert outbox.status == OutboxDeliveryStatus.PUBLISHED.value
    assert inbox.status == InboxProcessingStatus.PROCESSED.value


def test_exact_delivery_replay_after_finance_commit_has_one_monetary_effect(services) -> None:
    _, project, resource, _, assignment = _setup(services)
    outbox, envelope = _approve_without_immediate_dispatch(
        services,
        resource_id=resource.id,
        assignment_id=assignment.id,
    )
    dispatcher = services["approved_time_financial_dispatcher"]

    assert dispatcher._consume_under_unit_of_work(envelope).value == "ready"
    assert dispatcher._consume_under_unit_of_work(envelope).value == "duplicate_processed"

    rows, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 1
    assert rows[0].amount == Decimal("100.0000")
    assert services["session"].execute(
        select(sa.func.count()).select_from(ApprovedTimeLaborPostingORM)
    ).scalar_one() == 1
    assert outbox.status == OutboxDeliveryStatus.PENDING.value


def test_approved_time_worker_records_success_and_replay_statement_counts(services) -> None:
    _, project, resource, _, assignment = _setup(services)
    _, envelope = _approve_without_immediate_dispatch(
        services, resource_id=resource.id, assignment_id=assignment.id
    )
    dispatcher = services["approved_time_financial_dispatcher"]
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    engine = services["session"].get_bind()
    sa.event.listen(engine, "before_cursor_execute", capture)
    try:
        assert dispatcher._consume_under_unit_of_work(envelope).value == "ready"
        posted = len(statements)
        statements.clear()
        assert dispatcher._consume_under_unit_of_work(envelope).value == "duplicate_processed"
        replay = len(statements)
    finally:
        sa.event.remove(engine, "before_cursor_execute", capture)

    print("R6D-F approved-Time worker SQL statements:", {"post": posted, "replay": replay})
    assert posted > 0 and replay > 0
    assert services["cost_entry_service"].list_for_project(project.id)[1] == 1


def test_disabled_worker_identity_is_quarantined_without_posting(services) -> None:
    _, project, resource, _, assignment = _setup(services)
    principal = services["service_principal_service"].resolve_execution_principal(
        name=APPROVED_TIME_FINANCE_PRINCIPAL_NAME
    )
    services["service_principal_service"].disable_service_principal(principal.id)

    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 12), hours=Decimal("2")
    )
    submitted = services["timesheet_service"].submit_timesheet_period(
        resource.id, period_start=date(2026, 5, 1)
    )
    services["timesheet_service"].approve_timesheet_period(
        submitted.period_id, expected_version=submitted.version
    )

    _, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 0
    assert services["session"].execute(
        select(sa.func.count()).select_from(ApprovedTimeLaborPostingORM)
    ).scalar_one() == 0
    inbox = services["session"].execute(select(ProjectFinanceInboxORM)).scalar_one()
    assert inbox.status == InboxProcessingStatus.QUARANTINED.value
    assert inbox.last_error_code == "INTEGRATION_SERVICE_PRINCIPAL_DISABLED"


def test_missing_cost_rate_is_durable_and_never_posts_zero_actual(services) -> None:
    _, project, resource, _, assignment = _setup(services)
    card = services["rate_card_service"].list_rate_cards(project_id=project.id)[0]
    services["rate_card_service"].deactivate_rate_card(
        card.id, expected_version=card.version
    )

    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 13), hours=Decimal("2")
    )
    submitted = services["timesheet_service"].submit_timesheet_period(
        resource.id, period_start=date(2026, 5, 1)
    )
    services["timesheet_service"].approve_timesheet_period(
        submitted.period_id, expected_version=submitted.version
    )

    _, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 0
    inbox = services["session"].execute(select(ProjectFinanceInboxORM)).scalar_one()
    assert inbox.status == InboxProcessingStatus.RETRY.value
    assert inbox.last_error_code == "RATE_CARD_NO_APPLICABLE_RATE"
    assert "No applicable rate" in inbox.last_error_message


def test_posting_failure_read_is_bounded_scoped_and_sensitive_by_permission(
    services,
) -> None:
    _, project, resource, _, assignment = _setup(services)
    card = services["rate_card_service"].list_rate_cards(project_id=project.id)[0]
    services["rate_card_service"].deactivate_rate_card(
        card.id,
        expected_version=card.version,
    )
    services["task_service"].add_time_entry(
        assignment.id,
        entry_date=date(2026, 5, 13),
        hours=Decimal("2"),
    )
    submitted = services["timesheet_service"].submit_timesheet_period(
        resource.id,
        period_start=date(2026, 5, 1),
    )
    services["timesheet_service"].approve_timesheet_period(
        submitted.period_id,
        expected_version=submitted.version,
    )

    request = ApprovedTimePostingFailureQuery(
        page=1,
        page_size=1,
        sort_key="source",
        sort_direction="asc",
        status="retry",
    )
    page = services["finance_workspace_query"].list_approved_time_posting_failures(
        project.id,
        request=request,
    )
    assert page.total == 1
    assert page.page_size == 1
    assert page.sort_key == "source"
    assert page.sort_direction == "asc"
    assert page.items[0].resource_id == resource.id
    assert page.items[0].failure_code == "RATE_CARD_NO_APPLICABLE_RATE"
    assert "No applicable rate" in page.items[0].failure_message

    unrelated_project = services["project_service"].create_project(
        "Unrelated Finance Project"
    )
    unrelated = services[
        "finance_workspace_query"
    ].list_approved_time_posting_failures(
        unrelated_project.id,
        request=request,
    )
    assert unrelated.total == 0

    user_session = services["user_session"]
    tenant_id = user_session.stored_active_tenant_id()
    organization_id = user_session.stored_active_organization_id()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="finance-reader",
            username="finance-reader",
            display_name="Finance Reader",
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"finance.read"}),
            project_access={project.id: frozenset({"finance.read"})},
            active_tenant_id=tenant_id,
            active_organization_id=organization_id,
        )
    )
    redacted = services[
        "finance_workspace_query"
    ].list_approved_time_posting_failures(
        project.id,
        request=request,
    )
    assert redacted.total == 1
    assert redacted.items[0].resource_id == ""
    assert redacted.items[0].failure_message == (
        "Detailed integration evidence requires sensitive Finance access."
    )


def test_rate_changes_do_not_revalue_existing_labor_provenance(services) -> None:
    organization, project, resource, _, assignment = _setup(services)
    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 14), hours=Decimal("2")
    )
    submitted = services["timesheet_service"].submit_timesheet_period(
        resource.id, period_start=date(2026, 5, 1)
    )
    services["timesheet_service"].approve_timesheet_period(
        submitted.period_id, expected_version=submitted.version
    )
    original = services["session"].execute(select(ApprovedTimeLaborPostingORM)).scalar_one()
    original_evidence = (
        original.rate_card_id,
        original.rate_line_id,
        original.rate_line_version,
        original.rate_base_amount,
        original.rate_amount,
        original.rate_resolved_at,
    )

    card = services["rate_card_service"].list_rate_cards(project_id=project.id)[0]
    services["rate_card_service"].deactivate_rate_card(card.id, expected_version=card.version)
    successor = services["rate_card_service"].create_rate_card(
        name="Approved Time successor rates", project_id=project.id
    )
    services["rate_card_service"].create_line(
        successor.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("75"),
        rate_currency=organization.base_currency,
        resource_id=resource.id,
    )
    services["session"].expire_all()
    persisted = services["session"].execute(select(ApprovedTimeLaborPostingORM)).scalar_one()
    assert (
        persisted.rate_card_id,
        persisted.rate_line_id,
        persisted.rate_line_version,
        persisted.rate_base_amount,
        persisted.rate_amount,
        persisted.rate_resolved_at,
    ) == original_evidence


def test_same_source_revision_with_different_hash_is_quarantined(services) -> None:
    _, project, resource, _, assignment = _setup(services)
    _, envelope = _approve_without_immediate_dispatch(
        services,
        resource_id=resource.id,
        assignment_id=assignment.id,
    )
    dispatcher = services["approved_time_financial_dispatcher"]
    assert dispatcher._consume_under_unit_of_work(envelope).value == "ready"

    payload = dict(envelope.payload)
    payload["source_content_hash"] = "f" * 64
    conflicting = envelope.model_copy(
        update={
            "event_id": str(uuid4()),
            "aggregate_version": envelope.aggregate_version + 1,
            "payload": payload,
        }
    )
    services["time_financial_outbox_service"].enqueue(conflicting)
    services["session"].commit()
    dispatcher.dispatch_pending()

    _, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 1
    conflict = services["session"].execute(
        select(ProjectFinanceInboxORM).where(
            ProjectFinanceInboxORM.event_id == conflicting.event_id
        )
    ).scalar_one()
    assert conflict.status == InboxProcessingStatus.QUARANTINED.value
    assert conflict.last_error_code == "APPROVED_TIME_SOURCE_HASH_CONFLICT"


def test_finance_audit_failure_rolls_back_labor_cost_and_inbox_success(
    services, monkeypatch
) -> None:
    _, project, resource, _, assignment = _setup(services)

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("finance audit unavailable")

    monkeypatch.setattr(
        "src.core.modules.project_management.application.financials.cost.entries.cost_entry_service.record_project_cost_entry_audit",
        fail_audit,
    )
    services["task_service"].add_time_entry(
        assignment.id, entry_date=date(2026, 5, 15), hours=Decimal("2")
    )
    submitted = services["timesheet_service"].submit_timesheet_period(
        resource.id, period_start=date(2026, 5, 1)
    )
    services["timesheet_service"].approve_timesheet_period(
        submitted.period_id, expected_version=submitted.version
    )

    _, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 0
    assert services["session"].execute(
        select(sa.func.count()).select_from(ApprovedTimeLaborPostingORM)
    ).scalar_one() == 0
    inbox = services["session"].execute(select(ProjectFinanceInboxORM)).scalar_one()
    assert inbox.status == InboxProcessingStatus.RETRY.value
    assert inbox.last_error_code == "RUNTIMEERROR"


def test_approved_time_transactional_handler_receives_the_real_uow_not_the_dispatcher(
    services,
) -> None:
    from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
        CostEntryRecorded,
    )
    from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase

    _, project, resource, _, assignment = _setup(services)
    dispatcher = services["approved_time_financial_dispatcher"]
    seen: list[object] = []
    received_uows: list[object] = []

    def _observe(event, uow) -> None:
        seen.append(event)
        received_uows.append(uow)

    subscription = dispatcher._transactional_dispatcher.subscribe(CostEntryRecorded, _observe)
    try:
        services["task_service"].add_time_entry(
            assignment.id, entry_date=date(2026, 5, 6), hours=Decimal("2")
        )
        submitted = services["timesheet_service"].submit_timesheet_period(
            resource.id, period_start=date(2026, 5, 1)
        )
        services["timesheet_service"].approve_timesheet_period(
            submitted.period_id, expected_version=submitted.version
        )
    finally:
        subscription.dispose()

    assert len(seen) == 1
    assert seen[0].project_id == project.id
    assert len(received_uows) == 1
    handler_uow = received_uows[0]
    assert handler_uow is not dispatcher, "must not be the dispatcher impersonating a UoW"
    assert isinstance(handler_uow, SqlAlchemyUnitOfWorkBase)
    assert handler_uow._session is not dispatcher._session


def test_approved_time_transactional_handler_failure_rolls_back_and_yields_zero_postcommit_event(
    services,
) -> None:
    """When a precommit Cost Entry transactional handler fails, the mutation must not persist and
    no postcommit event may occur."""
    from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
        CostEntryRecorded,
    )

    _, project, resource, _, assignment = _setup(services)
    dispatcher = services["approved_time_financial_dispatcher"]

    def _boom(_event, _uow) -> None:
        raise RuntimeError("simulated precommit Cost Entry handler failure")

    subscription = dispatcher._transactional_dispatcher.subscribe(CostEntryRecorded, _boom)
    postcommit_seen: list[object] = []
    post_commit_subscription = dispatcher._post_commit_bus.subscribe(
        CostEntryRecorded, lambda e, c: postcommit_seen.append(e)
    )
    try:
        services["task_service"].add_time_entry(
            assignment.id, entry_date=date(2026, 5, 7), hours=Decimal("2")
        )
        submitted = services["timesheet_service"].submit_timesheet_period(
            resource.id, period_start=date(2026, 5, 1)
        )
        services["timesheet_service"].approve_timesheet_period(
            submitted.period_id, expected_version=submitted.version
        )
    finally:
        subscription.dispose()
        post_commit_subscription.dispose()

    _, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 0, "the failed-precommit-handler mutation must not persist"
    assert postcommit_seen == [], "a precommit failure must never reach the postcommit bus"

    outbox = services["session"].execute(select(TimeFinancialOutboxORM)).scalar_one()
    assert outbox.status != OutboxDeliveryStatus.PUBLISHED.value


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
