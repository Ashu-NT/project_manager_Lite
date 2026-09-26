import hashlib
from dataclasses import replace

import pytest
from sqlalchemy import func, select, update

from src.core.modules.project_management.domain.financials.accounting.handoff import (
    AccountingHandoffSnapshot,
)
from src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff import (
    ProjectAccountingHandoffORM,
    ProjectAccountingOutboxORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.billing import (
    ProjectBillingProfileORM,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
    AuditEntryORM,
)
from src.core.platform.infrastructure.persistence.orm.integration.accounting_connector import (
    AccountingConnectorORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.modules.modules import (
    ModuleEntitlementORM,
)
from src.tests.project_management.application.test_p39_finance_billing_full_modernization import (
    _login,
    _ready_schedule_line,
    _setup_billable_project,
    _spy_hints,
    _submitted_preparation,
)


def approved_preparation(services):
    _, project, _ = _setup_billable_project(services)
    _, line = _ready_schedule_line(services, project)
    submitted = _submitted_preparation(services, project, line)
    approval = services["approval_service"].list_pending(project_id=project.id)[0]
    services["auth_service"].register_user(
        "handoff-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "handoff-reviewer", "StrongPass123")
    services["approval_service"].approve_and_apply(approval.id)
    _login(services, "admin", "ChangeMe123!")
    return services["billing_preparation_service"].get_preparation(submitted.id)


def test_durable_request_and_profile_independent_replay(accounting_services, session):
    services = accounting_services
    approved = approved_preparation(services)
    billing = services["billing_preparation_service"]
    payload = billing.request_delivery(
        approved.id, expected_row_version=approved.row_version
    )
    row = session.scalars(select(ProjectAccountingHandoffORM)).one()
    outbox = session.scalars(select(ProjectAccountingOutboxORM)).one()
    snapshot = AccountingHandoffSnapshot.model_validate_json(row.payload_bytes)
    assert (
        row.id == payload.handoff_id == outbox.event_id == snapshot.evidence.message_id
    )
    assert snapshot.approved_preparation_version == approved.row_version
    assert (
        hashlib.sha256(row.payload_bytes).hexdigest()
        == row.payload_hash
        == snapshot.content_hash
    )
    before = row.payload_bytes
    session.execute(
        update(ProjectBillingProfileORM).values(
            contract_reference="CHANGED", payment_terms_days=99
        )
    )
    session.commit()
    hints = _spy_hints(services)
    assert (
        billing.request_delivery(approved.id, expected_row_version=approved.row_version)
        == payload
    )
    assert not hints
    session.expire_all()
    assert (
        session.scalars(select(ProjectAccountingHandoffORM)).one().payload_bytes
        == before
    )
    assert (
        session.scalar(select(func.count()).select_from(ProjectAccountingOutboxORM))
        == 1
    )
    pending = billing.get_preparation(approved.id)
    assert pending.status.value == "delivery_pending"
    assert pending.delivery_requested_at == snapshot.requested_at
    assert pending.delivered_at is None


@pytest.mark.parametrize(
    "failure",
    ["before_snapshot", "snapshot_validation", "enqueue", "state", "audit", "commit"],
)
def test_handoff_failure_rolls_back_everything_then_retry(
    accounting_services, session, monkeypatch, failure
):
    from src.core.modules.project_management.application.financials.accounting import (
        request_service,
    )
    from src.core.modules.project_management.application.financials.invoicing.preparation_service import (
        ProjectBillingPreparationService,
    )
    from src.core.modules.project_management.infrastructure.persistence.repositories.finance.accounting.handoff import (
        SqlAlchemyAccountingHandoffRepository,
    )
    from src.core.platform.application.integration.delivery_service import (
        IntegrationOutboxService,
    )
    from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase

    services = accounting_services
    approved = approved_preparation(services)
    hints = _spy_hints(services)
    audit_count = session.scalar(select(func.count()).select_from(AuditEntryORM))
    targets = {
        "before_snapshot": (SqlAlchemyAccountingHandoffRepository, "add"),
        "snapshot_validation": (request_service, "AccountingHandoffSnapshot"),
        "enqueue": (IntegrationOutboxService, "enqueue"),
        "state": (ProjectBillingPreparationService, "_mark_delivery_requested"),
        "audit": (request_service, "record_audit_entry"),
        "commit": (SqlAlchemyUnitOfWorkBase, "commit"),
    }

    def fail(*args, **kwargs):
        raise RuntimeError("injected request failure")

    with monkeypatch.context() as patch:
        patch.setattr(*targets[failure], fail)
        with pytest.raises(RuntimeError, match="injected request failure"):
            services["billing_preparation_service"].request_delivery(
                approved.id, expected_row_version=approved.row_version
            )
    assert not hints
    session.expire_all()
    assert (
        session.scalar(select(func.count()).select_from(AuditEntryORM)) == audit_count
    )
    assert (
        session.scalar(select(func.count()).select_from(ProjectAccountingHandoffORM))
        == 0
    )
    assert (
        session.scalar(select(func.count()).select_from(ProjectAccountingOutboxORM))
        == 0
    )
    assert (
        services["billing_preparation_service"]
        .get_preparation(approved.id)
        .status.value
        == "approved"
    )
    services["billing_preparation_service"].request_delivery(
        approved.id, expected_row_version=approved.row_version
    )
    assert (
        session.scalar(select(func.count()).select_from(ProjectAccountingHandoffORM))
        == 1
    )


@pytest.mark.parametrize(
    "state,reason",
    [
        ("module", "module_not_enabled"),
        ("connector", "integration_not_configured"),
        ("adapter", "adapter_not_installed"),
    ],
)
def test_command_rechecks_changed_capability(
    accounting_services, session, state, reason
):
    services = accounting_services
    approved = approved_preparation(services)
    fact = (
        services["finance_workspace_query"]
        .get_billing_read_workspace(
            approved.project_id, selected_preparation_id=approved.id
        )
        .selected_preparation
    )
    assert fact.can_request_delivery
    if state == "module":
        session.execute(
            update(ModuleEntitlementORM)
            .where(ModuleEntitlementORM.module_code == "accounting_integration")
            .values(enabled=False)
        )
    elif state == "connector":
        session.execute(update(AccountingConnectorORM).values(enabled=False))
    else:
        session.execute(update(AccountingConnectorORM).values(adapter_id="unknown"))
    session.commit()
    with pytest.raises(BusinessRuleError) as error:
        services["billing_preparation_service"].request_delivery(
            approved.id, expected_row_version=approved.row_version
        )
    assert error.value.code == reason
    assert (
        session.scalar(select(func.count()).select_from(ProjectAccountingHandoffORM))
        == 0
    )


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "broken", "-1"])
def test_snapshot_rejects_invalid_money(accounting_services, session, value):
    services = accounting_services
    approved = approved_preparation(services)
    services["billing_preparation_service"].request_delivery(
        approved.id, expected_row_version=approved.row_version
    )
    snapshot = AccountingHandoffSnapshot.model_validate_json(
        session.scalars(select(ProjectAccountingHandoffORM)).one().payload_bytes
    )
    with pytest.raises(ValueError):
        evidence = replace(snapshot.evidence, total_amount=value)
        AccountingHandoffSnapshot(**{**snapshot.model_dump(), "evidence": evidence})


def test_finance_manage_does_not_grant_handoff_or_external_status(accounting_services):
    services = accounting_services
    approved = approved_preparation(services)
    user = services["user_session"]
    permissions = frozenset({"finance.read", "finance.manage"})
    user.set_principal(
        replace(
            user.principal,
            permissions=permissions,
            role_names=frozenset(),
            scoped_access={"project": {approved.project_id: permissions}},
        )
    )
    query = services["finance_workspace_query"]
    detail = query.get_billing_read_workspace(
        approved.project_id, selected_preparation_id=approved.id
    ).selected_preparation
    assert not detail.can_request_delivery
    assert detail.handoff_denial_reason == "permission_denied"
    assert not detail.can_view_accounting_status
    with pytest.raises(BusinessRuleError):
        services["billing_preparation_service"].request_delivery(
            approved.id, expected_row_version=approved.row_version
        )
    with pytest.raises(BusinessRuleError):
        query.get_accounting_statuses(approved.project_id)


def test_absent_accounting_does_not_block_preparation(services):
    approved = approved_preparation(services)
    detail = (
        services["finance_workspace_query"]
        .get_billing_read_workspace(
            approved.project_id, selected_preparation_id=approved.id
        )
        .selected_preparation
    )
    assert detail.handoff_denial_reason == "adapter_not_installed"
    assert not detail.can_request_delivery
    assert detail.can_view_accounting_status
    with pytest.raises(BusinessRuleError) as error:
        services["billing_preparation_service"].request_delivery(
            approved.id, expected_row_version=approved.row_version
        )
    assert error.value.code == "adapter_not_installed"


def test_invalid_approved_evidence_cannot_leave_a_partial_request(
    accounting_services, session
):
    from src.core.modules.project_management.infrastructure.persistence.orm.billing import (
        ProjectBillingPreparationLineORM,
    )

    approved = approved_preparation(accounting_services)
    session.execute(
        update(ProjectBillingPreparationLineORM)
        .where(
            ProjectBillingPreparationLineORM.preparation_id == approved.id,
        )
        .values(currency_code="EUR" if approved.currency_code != "EUR" else "USD")
    )
    session.commit()
    audit_count = session.scalar(select(func.count()).select_from(AuditEntryORM))
    hints = _spy_hints(accounting_services)
    with pytest.raises(ValueError):
        accounting_services["billing_preparation_service"].request_delivery(
            approved.id,
            expected_row_version=approved.row_version,
        )
    assert not hints
    assert (
        session.scalar(select(func.count()).select_from(ProjectAccountingHandoffORM))
        == 0
    )
    assert (
        session.scalar(select(func.count()).select_from(ProjectAccountingOutboxORM))
        == 0
    )
    assert (
        session.scalar(select(func.count()).select_from(AuditEntryORM)) == audit_count
    )
    assert (
        accounting_services["billing_preparation_service"]
        .get_preparation(approved.id)
        .status.value
        == "approved"
    )


def test_changed_snapshot_is_rejected_and_history_survives_disable(
    accounting_services, session
):
    from src.core.modules.project_management.infrastructure.persistence.repositories.finance.accounting.handoff import (
        SqlAlchemyAccountingHandoffRepository,
    )

    services = accounting_services
    approved = approved_preparation(services)
    services["billing_preparation_service"].request_delivery(
        approved.id, expected_row_version=approved.row_version
    )
    repository = SqlAlchemyAccountingHandoffRepository(session)
    repository._tenant_context_service = services["tenant_context_service"]
    original = repository.get_for_preparation(approved.project_id, approved.id)
    changed = AccountingHandoffSnapshot(
        **(original.model_dump() | {"requested_by": "different-actor"})
    )
    with pytest.raises(BusinessRuleError) as error:
        repository.add(changed)
    assert error.value.code == "ACCOUNTING_HANDOFF_CONTENT_CONFLICT"
    session.execute(update(AccountingConnectorORM).values(enabled=False))
    session.commit()
    page = services["finance_workspace_query"].get_accounting_statuses(
        approved.project_id
    )
    assert page.total == 1
    assert (
        repository.get_for_preparation(approved.project_id, approved.id).canonical_bytes
        == original.canonical_bytes
    )


@pytest.mark.parametrize("change", ["currency", "sum", "empty", "schema", "float"])
def test_snapshot_currency_sum_schema_and_empty_lines(
    accounting_services, session, change
):
    services = accounting_services
    approved = approved_preparation(services)
    services["billing_preparation_service"].request_delivery(
        approved.id, expected_row_version=approved.row_version
    )
    snapshot = AccountingHandoffSnapshot.model_validate_json(
        session.scalars(select(ProjectAccountingHandoffORM)).one().payload_bytes
    )
    raw = snapshot.model_dump(mode="json")
    if change == "currency":
        raw["evidence"]["lines"][0]["currency_code"] = (
            "USD" if raw["evidence"]["currency_code"] != "USD" else "EUR"
        )
    elif change == "sum":
        raw["evidence"]["total_amount"] = "17.00"
    elif change == "empty":
        raw["evidence"]["lines"] = []
    elif change == "schema":
        raw["schema_name"] = "unknown.v1"
    else:
        raw["evidence"]["lines"][0]["net_amount"] = 24000.0
    with pytest.raises(ValueError):
        AccountingHandoffSnapshot.model_validate(raw)


def test_read_capability_serializes_safe_reason(accounting_services):
    from src.core.modules.project_management.api.desktop.financials.serializers.billing_workspace_serializer import (
        serialize_finance_billing_workspace,
    )

    services = accounting_services
    approved = approved_preparation(services)
    facts = services["finance_workspace_query"].get_billing_read_workspace(
        approved.project_id, selected_preparation_id=approved.id
    )
    assert facts.selected_preparation.can_request_delivery
    assert "secret" not in repr(serialize_finance_billing_workspace(facts)).lower()


def test_configuration_permission_is_distinct_and_versioned(accounting_services):
    from src.core.shared.events.domain_event_context import DomainEventContext

    services = accounting_services
    commands = services["accounting_connector_commands"]
    user = services["user_session"]
    original = user.principal
    user.set_principal(
        replace(
            original,
            role_names=frozenset(),
            permissions=frozenset({"finance.accounting_handoff.request"}),
        )
    )
    values = dict(
        adapter_id="test_connector",
        connection_id="other",
        secret_reference="ref",
        enabled=True,
        expected_version=1,
    )
    try:
        with pytest.raises(BusinessRuleError):
            commands.configure(**values)
    finally:
        user.set_principal(original)
    configured = commands.configure(**values)
    assert configured.version == 2
    with pytest.raises(BusinessRuleError):
        commands.configure(**values)
    with commands._uow_factory.create(
        context=DomainEventContext(correlation_id="verify-config")
    ) as uow:
        assert uow.accounting_connectors.get().version == 2


def test_configuration_audit_failure_rolls_back(
    accounting_services, session, monkeypatch
):
    from src.core.platform.application.integration.accounting import (
        configuration_service,
    )

    def fail(*args, **kwargs):
        raise RuntimeError("configuration audit unavailable")

    before = session.scalar(select(func.count()).select_from(AuditEntryORM))
    monkeypatch.setattr(configuration_service, "record_audit_entry", fail)
    with pytest.raises(RuntimeError, match="configuration audit unavailable"):
        accounting_services["accounting_connector_commands"].configure(
            adapter_id="test_connector",
            connection_id="changed",
            secret_reference="ref",
            enabled=False,
            expected_version=1,
        )
    session.expire_all()
    config = session.scalars(select(AccountingConnectorORM)).one()
    assert config.version == 1 and config.enabled
    assert config.connection_id == "test_connection"
    assert session.scalar(select(func.count()).select_from(AuditEntryORM)) == before


def test_missing_connector_is_safe_and_does_not_block_billing(
    accounting_services, session
):
    from sqlalchemy import delete

    session.execute(delete(AccountingConnectorORM))
    session.commit()
    approved = approved_preparation(accounting_services)
    detail = (
        accounting_services["finance_workspace_query"]
        .get_billing_read_workspace(
            approved.project_id,
            selected_preparation_id=approved.id,
        )
        .selected_preparation
    )
    assert detail.handoff_denial_reason == "integration_not_configured"
    with pytest.raises(BusinessRuleError) as error:
        accounting_services["billing_preparation_service"].request_delivery(
            approved.id,
            expected_row_version=approved.row_version,
        )
    assert error.value.code == "integration_not_configured"


def test_handoff_permission_for_another_project_is_not_sufficient(accounting_services):
    approved = approved_preparation(accounting_services)
    user = accounting_services["user_session"]
    permissions = frozenset({"finance.read", "finance.accounting_handoff.request"})
    user.set_principal(
        replace(
            user.principal,
            role_names=frozenset(),
            permissions=permissions,
            scoped_access={"project": {"unrelated-project": permissions}},
        )
    )
    with pytest.raises(BusinessRuleError):
        accounting_services["billing_preparation_service"].request_delivery(
            approved.id,
            expected_row_version=approved.row_version,
        )


@pytest.mark.parametrize("line_count", [1, 25])
def test_handoff_uses_one_scoped_line_query(accounting_services, session, line_count):
    from uuid import uuid4

    from sqlalchemy import event

    from src.core.modules.project_management.infrastructure.persistence.orm.billing import (
        ProjectBillingPreparationLineORM,
        ProjectBillingPreparationORM,
    )

    approved = approved_preparation(accounting_services)
    line = session.scalars(select(ProjectBillingPreparationLineORM)).one()
    for index in range(1, line_count):
        values = {
            column.name: getattr(line, column.name)
            for column in ProjectBillingPreparationLineORM.__table__.columns
        }
        values.update(
            id=str(uuid4()),
            source_id=str(uuid4()),
            description=f"Approved source {index}",
        )
        session.add(ProjectBillingPreparationLineORM(**values))
    session.execute(
        update(ProjectBillingPreparationORM)
        .where(
            ProjectBillingPreparationORM.id == approved.id,
        )
        .values(line_count=line_count, total_amount=line.net_amount * line_count)
    )
    session.commit()
    selects = []

    def record(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    event.listen(session.bind, "before_cursor_execute", record)
    try:
        accounting_services["billing_preparation_service"].request_delivery(
            approved.id,
            expected_row_version=approved.row_version,
        )
    finally:
        event.remove(session.bind, "before_cursor_execute", record)
    line_queries = [
        query for query in selects if "FROM project_billing_preparation_lines" in query
    ]
    assert len(line_queries) == 1
    assert "preparation_id =" in line_queries[0]
    assert len(selects) < 60


def test_correction_gets_new_identity_without_changing_parent(
    accounting_services, session, accounting_outcome):
    from datetime import date, datetime, timezone
    from decimal import Decimal

    from src.core.modules.project_management.domain.financials.billing_preparation import (
        BillingExternalEventType,
    )

    services = accounting_services
    approved = approved_preparation(services)
    billing = services["billing_preparation_service"]
    parent = billing.request_delivery(
        approved.id, expected_row_version=approved.row_version
    )
    parent_bytes = session.scalars(
        select(ProjectAccountingHandoffORM.payload_bytes)
    ).one()
    for event_type in (
        BillingExternalEventType.DELIVERY_ACCEPTED,
        BillingExternalEventType.RECONCILED,
    ):
        accounting_outcome(
            approved.id,
            outcome={"delivery_accepted": "acknowledged", "reconciled": "reconciled"}[event_type.value],
            event_id=event_type.value,
            occurred_at=datetime.now(timezone.utc),
            reconciliation_reference="confirmed",
        )
    profiles = services["billing_profile_service"]
    line = profiles.add_schedule_line(
        approved.project_id,
        name="Correction source",
        amount=Decimal(100),
        due_date=date(2026, 8, 20),
    )
    line = profiles.mark_schedule_line_ready(
        line.id, expected_row_version=line.row_version
    )
    correction = billing.create_preparation(
        approved.project_id,
        preparation_number="CORRECTION",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        idempotency_key="correction",
        correction_of_preparation_id=approved.id,
    )
    billing.add_fixed_price_source(
        correction.id,
        schedule_line_id=line.id,
        expected_row_version=correction.row_version,
    )
    correction = billing.get_preparation(correction.id)
    correction = billing.submit_preparation(
        correction.id, expected_row_version=correction.row_version
    )
    approval = services["approval_service"].list_pending(
        project_id=approved.project_id
    )[0]
    _login(services, "handoff-reviewer", "StrongPass123")
    services["approval_service"].approve_and_apply(approval.id)
    _login(services, "admin", "ChangeMe123!")
    correction = billing.get_preparation(correction.id)
    successor = billing.request_delivery(
        correction.id, expected_row_version=correction.row_version
    )
    assert successor.handoff_id != parent.handoff_id
    assert (
        session.scalars(
            select(ProjectAccountingHandoffORM.payload_bytes).where(
                ProjectAccountingHandoffORM.id == parent.handoff_id
            )
        ).one()
        == parent_bytes
    )
    assert (
        session.scalar(select(func.count()).select_from(ProjectAccountingOutboxORM))
        == 2
    )
