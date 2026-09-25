import hashlib
from dataclasses import replace

import pytest
from sqlalchemy import func, select, update

from src.core.modules.project_management.domain.financials.accounting.handoff import AccountingHandoffSnapshot
from src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff import ProjectAccountingHandoffORM, ProjectAccountingOutboxORM
from src.core.modules.project_management.infrastructure.persistence.orm.billing import ProjectBillingProfileORM
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.orm.integration.accounting_connector import AccountingConnectorORM
from src.core.platform.infrastructure.persistence.orm.tenant.modules.modules import ModuleEntitlementORM
from src.tests.project_management.application.test_p39_finance_billing_full_modernization import (
    _login, _ready_schedule_line, _setup_billable_project, _spy_hints, _submitted_preparation,
)


def approved_preparation(services):
    _, project, _ = _setup_billable_project(services)
    _, line = _ready_schedule_line(services, project)
    submitted = _submitted_preparation(services, project, line)
    approval = services["approval_service"].list_pending(project_id=project.id)[0]
    services["auth_service"].register_user("handoff-reviewer", "StrongPass123", role_names=["approver"])
    _login(services, "handoff-reviewer", "StrongPass123")
    services["approval_service"].approve_and_apply(approval.id)
    _login(services, "admin", "ChangeMe123!")
    return services["billing_preparation_service"].get_preparation(submitted.id)


def test_durable_request_and_profile_independent_replay(accounting_services, session):
    services = accounting_services
    approved = approved_preparation(services)
    billing = services["billing_preparation_service"]
    payload = billing.request_delivery(approved.id, expected_row_version=approved.row_version)
    row = session.scalars(select(ProjectAccountingHandoffORM)).one()
    outbox = session.scalars(select(ProjectAccountingOutboxORM)).one()
    snapshot = AccountingHandoffSnapshot.model_validate_json(row.payload_bytes)
    assert row.id == payload.message_id == outbox.event_id
    assert snapshot.approved_preparation_version == approved.row_version
    assert hashlib.sha256(row.payload_bytes).hexdigest() == row.payload_hash == snapshot.content_hash
    before = row.payload_bytes
    session.execute(update(ProjectBillingProfileORM).values(contract_reference="CHANGED", payment_terms_days=99))
    session.commit()
    hints = _spy_hints(services)
    assert billing.request_delivery(approved.id, expected_row_version=approved.row_version) == payload
    assert not hints
    session.expire_all()
    assert session.scalars(select(ProjectAccountingHandoffORM)).one().payload_bytes == before
    assert session.scalar(select(func.count()).select_from(ProjectAccountingOutboxORM)) == 1
    pending = billing.get_preparation(approved.id)
    assert pending.status.value == "delivery_pending"
    assert pending.delivery_requested_at == snapshot.requested_at
    assert pending.delivered_at is None


@pytest.mark.parametrize("failure", ["before_snapshot", "enqueue", "state", "audit", "commit"])
def test_handoff_failure_rolls_back_everything_then_retry(accounting_services, session, monkeypatch, failure):
    from src.core.modules.project_management.application.financials.accounting import request_service
    from src.core.modules.project_management.application.financials.invoicing.preparation_service import ProjectBillingPreparationService
    from src.core.modules.project_management.infrastructure.persistence.repositories.finance.accounting.handoff import SqlAlchemyAccountingHandoffRepository
    from src.core.platform.application.integration.delivery_service import IntegrationOutboxService
    from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase

    services = accounting_services
    approved = approved_preparation(services)
    hints = _spy_hints(services)
    targets = {
        "before_snapshot": (SqlAlchemyAccountingHandoffRepository, "add"),
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
            services["billing_preparation_service"].request_delivery(approved.id, expected_row_version=approved.row_version)
    assert not hints
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(ProjectAccountingHandoffORM)) == 0
    assert session.scalar(select(func.count()).select_from(ProjectAccountingOutboxORM)) == 0
    assert services["billing_preparation_service"].get_preparation(approved.id).status.value == "approved"
    services["billing_preparation_service"].request_delivery(approved.id, expected_row_version=approved.row_version)
    assert session.scalar(select(func.count()).select_from(ProjectAccountingHandoffORM)) == 1


@pytest.mark.parametrize("state,reason", [("module", "module_not_enabled"), ("connector", "integration_not_configured"), ("adapter", "adapter_not_installed")])
def test_command_rechecks_changed_capability(accounting_services, session, state, reason):
    services = accounting_services
    approved = approved_preparation(services)
    fact = services["finance_workspace_query"].get_billing_read_workspace(approved.project_id, selected_preparation_id=approved.id).selected_preparation
    assert fact.can_request_delivery
    if state == "module":
        session.execute(update(ModuleEntitlementORM).where(ModuleEntitlementORM.module_code == "accounting_integration").values(enabled=False))
    elif state == "connector":
        session.execute(update(AccountingConnectorORM).values(enabled=False))
    else:
        session.execute(update(AccountingConnectorORM).values(adapter_id="unknown"))
    session.commit()
    with pytest.raises(BusinessRuleError) as error:
        services["billing_preparation_service"].request_delivery(approved.id, expected_row_version=approved.row_version)
    assert error.value.code == reason
    assert session.scalar(select(func.count()).select_from(ProjectAccountingHandoffORM)) == 0


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "broken", "-1"])
def test_snapshot_rejects_invalid_money(accounting_services, session, value):
    services = accounting_services
    approved = approved_preparation(services)
    services["billing_preparation_service"].request_delivery(approved.id, expected_row_version=approved.row_version)
    snapshot = AccountingHandoffSnapshot.model_validate_json(session.scalars(select(ProjectAccountingHandoffORM)).one().payload_bytes)
    evidence = replace(snapshot.evidence, total_amount=value)
    with pytest.raises(ValueError):
        AccountingHandoffSnapshot(**{**snapshot.model_dump(), "evidence": evidence})
