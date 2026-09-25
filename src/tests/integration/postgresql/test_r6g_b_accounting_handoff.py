from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.accounting.request_service import AccountingHandoffRequestService
from src.core.modules.project_management.application.financials.governance import FinanceGovernanceCommandBoundary
from src.core.modules.project_management.application.financials.invoicing.preparation_service import ProjectBillingPreparationService
from src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff import ProjectAccountingHandoffORM, ProjectAccountingOutboxORM
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.accounting.handoff import SqlAlchemyAccountingHandoffRepository
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import SqlAlchemyFinanceGovernanceUnitOfWorkFactory
from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
from src.infra.composition.accounting_integration import build_accounting_capability
from src.infra.events.in_process_post_commit_event_bus import InProcessPostCommitEventBus
from src.infra.events.in_process_transactional_event_dispatcher import InProcessTransactionalEventDispatcher
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role
from src.tests.integration.postgresql.test_r6f_billing_concurrency import billing_scope  # noqa: F401

pytestmark = pytest.mark.postgresql_integration


@pytest.fixture
def handoff_scope(postgres_test_environment, billing_scope):
    scope = billing_scope
    actors = (str(uuid4()), str(uuid4()))
    now = datetime.now(timezone.utc)
    with postgres_test_environment.admin_engine.begin() as connection:
        for actor in actors:
            connection.execute(text("INSERT INTO users (id, username, password_hash, account_type, is_active, created_at, updated_at, version) VALUES (:id, :id, 'no-login', 'human', true, :now, :now, 1)"), {"id": actor, "now": now})
        connection.execute(text("UPDATE project_billing_profiles SET customer_party_id='customer-reference' WHERE project_id=:project"), {"project": scope.project})
        connection.execute(text("UPDATE project_billing_preparations SET approved_by=:actor, approved_at=:now, approval_request_id='approved-request' WHERE id=:id"), {"actor": actors[0], "now": now, "id": scope.preparation})
        connection.execute(text("INSERT INTO project_finance_profiles (id, tenant_id, organization_id, project_id, currency_code, billing_method, is_billable, created_at, updated_at) VALUES (:project, :tenant, :org, :project, 'USD', 'fixed_price', true, :now, :now)"), {"project": scope.project, "tenant": scope.tenant, "org": scope.org, "now": now})
        connection.execute(text("INSERT INTO organization_module_entitlements (tenant_id, organization_id, module_code, licensed, enabled, lifecycle_status, updated_at) VALUES (:tenant, :org, 'accounting_integration', true, true, 'active', :now)"), {"tenant": scope.tenant, "org": scope.org, "now": now})
        connection.execute(text("INSERT INTO organization_accounting_connectors (tenant_id, organization_id, adapter_id, connection_id, secret_reference, enabled, version) VALUES (:tenant, :org, 'test_connector', 'test_connection', 'test_secret_ref', true, 1)"), {"tenant": scope.tenant, "org": scope.org})
    scope.actors = actors
    return scope


def boundary(environment, scope, actor, *, barrier=None):
    user = UserSessionContext()
    permissions = frozenset({"finance.read", "finance.accounting_handoff.request"})
    user.set_principal(UserSessionPrincipal(
        user_id=actor, username=actor, display_name="Handoff requester", role_names=frozenset(),
        permissions=permissions, scoped_access={"project": {scope.project: permissions}},
        active_tenant_id=scope.tenant, active_organization_id=scope.org,
    ))
    user.set_active_tenant_id(scope.tenant)
    user.set_active_organization_id(scope.org)
    factory = SqlAlchemyFinanceGovernanceUnitOfWorkFactory(
        session_factory=sessionmaker(bind=environment.runtime_engine, expire_on_commit=False),
        transactional_dispatcher=InProcessTransactionalEventDispatcher(), post_commit_bus=InProcessPostCommitEventBus(),
        tenant_context_service=scope, user_session=user,
    )
    def operations(uow):
        validate_postgresql_execution_role(uow._session)
        uow._session.execute(text("SET LOCAL lock_timeout = '8s'"))
        service = ProjectBillingPreparationService(
            session=uow._session, billing_repo=uow.billing, financial_profile_repo=uow.profiles,
            cost_entry_repo=uow.cost_entries, labor_posting_repo=uow.labor_postings, rate_resolver=None,
            financial_period_service=None, approval_service=None, tenant_context_service=scope,
            clock=SystemClock(), user_session=user, enterprise_audit_service=uow._enterprise_audit_service,
            record_event=uow.record_event,
        )
        service._handoff_request_service = AccountingHandoffRequestService(
            preparations=service, handoffs=uow.accounting_handoffs, outbox=uow.accounting_outbox, context=uow.context,
            capability=build_accounting_capability(session=uow._session, tenant_context_service=scope, user_session=user, installed_adapters={"test_connector"}),
        )
        if barrier:
            barrier.wait(timeout=10)
        return SimpleNamespace(billing_preparations=service, post_commit_actions=[])
    return FinanceGovernanceCommandBoundary(uow_factory=factory, operations_factory=operations)


def request(boundary, scope):
    return boundary.billing_preparation(lambda service: service.request_delivery(scope.preparation, expected_row_version=1))


def test_two_authorized_users_converge_in_independent_runtime_uows(postgres_test_environment, handoff_scope):
    scope = handoff_scope
    barrier = Barrier(2)
    def writer(actor):
        return request(boundary(postgres_test_environment, scope, actor, barrier=barrier), scope).message_id
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(writer, scope.actors))
    assert results[0] == results[1]
    with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as session:
        validate_postgresql_execution_role(session)
        assert session.scalar(select(func.count()).select_from(ProjectAccountingHandoffORM)) == 1
        assert session.scalar(select(func.count()).select_from(ProjectAccountingOutboxORM)) == 1
        assert session.scalar(text("SELECT version FROM project_billing_preparations WHERE id=:id"), {"id": scope.preparation}) == 2


@pytest.mark.parametrize("failure", ["enqueue", "audit", "state", "commit"])
def test_runtime_uow_rolls_back_and_retries(postgres_test_environment, handoff_scope, monkeypatch, failure):
    from src.core.modules.project_management.application.financials.accounting import request_service
    from src.core.platform.application.integration.delivery_service import IntegrationOutboxService
    from sqlalchemy.orm import Session
    scope = handoff_scope
    command = boundary(postgres_test_environment, scope, scope.actors[0])
    targets = {"enqueue": (IntegrationOutboxService, "enqueue"), "audit": (request_service, "record_audit_entry"), "state": (ProjectBillingPreparationService, "_mark_delivery_requested"), "commit": (Session, "commit")}
    def fail(*args, **kwargs):
        raise RuntimeError("injected database transaction failure")
    with monkeypatch.context() as patch:
        patch.setattr(*targets[failure], fail)
        with pytest.raises(RuntimeError, match="injected database"):
            request(command, scope)
    with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as session:
        assert session.scalar(select(func.count()).select_from(ProjectAccountingHandoffORM)) == 0
        assert session.scalar(select(func.count()).select_from(ProjectAccountingOutboxORM)) == 0
        assert session.scalar(text("SELECT status FROM project_billing_preparations WHERE id=:id"), {"id": scope.preparation}) == "approved"
    request(command, scope)


def test_handoff_scope_and_database_identity_constraints(postgres_test_environment, handoff_scope):
    scope = handoff_scope
    request(boundary(postgres_test_environment, scope, scope.actors[0]), scope)
    with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as session:
        validate_postgresql_execution_role(session)
        table = ProjectAccountingHandoffORM.__table__
        saved = dict(session.execute(select(table)).mappings().one())
        repository = SqlAlchemyAccountingHandoffRepository(session)
        repository._tenant_context_service = scope
        assert repository.get_for_preparation("wrong-project", scope.preparation) is None
        for changes in ({"id": str(uuid4())}, {"id": str(uuid4()), "project_id": "wrong-project"}):
            with pytest.raises(IntegrityError):
                with session.begin_nested():
                    session.execute(insert(table).values(**(saved | changes)))
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.execute(update(ProjectAccountingOutboxORM).values(project_id="wrong-project"))
    for tenant, org in (("other-tenant", scope.org), (scope.tenant, "other-org"), (None, None)):
        with postgres_test_environment.runtime_session(tenant_id=tenant, organization_id=org) as session:
            assert session.scalar(select(func.count()).select_from(ProjectAccountingHandoffORM)) == 0
            assert session.scalar(select(func.count()).select_from(ProjectAccountingOutboxORM)) == 0
            with pytest.raises(IntegrityError):
                session.execute(insert(ProjectAccountingHandoffORM).values(**(saved | {"id": str(uuid4())})))
            session.rollback()
