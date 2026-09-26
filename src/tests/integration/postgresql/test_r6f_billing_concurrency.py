from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import MetaData, Table, insert, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceCommandBoundary,
)
from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    BillingPreparationLineAdded,
)
from src.core.modules.project_management.application.financials.invoicing.preparation_service import (
    ProjectBillingPreparationService,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillingPreparationStatus,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.invoicing.billing import (
    SqlAlchemyProjectBillingRepository,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
)
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds
from src.core.platform.common.exceptions import ConcurrencyError
from src.core.platform.domain.security.auth.session import (
    UserSessionContext,
    UserSessionPrincipal,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role
from src.tests.integration.postgresql.test_r6b_billing_reader import _seed_scope

pytestmark = pytest.mark.postgresql_integration


def test_source_lock_cannot_attach_another_preparations_line(postgres_test_environment, billing_scope):
    scope = billing_scope
    metadata = MetaData()
    prep = Table("project_billing_preparations", metadata, autoload_with=postgres_test_environment.admin_engine)
    lines = Table("project_billing_preparation_lines", metadata, autoload_with=postgres_test_environment.admin_engine)
    locks = Table("project_billing_source_locks", metadata, autoload_with=postgres_test_environment.admin_engine)
    with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as session:
        validate_postgresql_execution_role(session)
        sibling = dict(session.execute(select(prep).where(prep.c.id == scope.preparation)).mappings().one())
        sibling.update(id=str(uuid4()), preparation_number=str(uuid4()), idempotency_key=str(uuid4()))
        session.execute(insert(prep).values(**sibling))
        line = dict(session.execute(select(lines).where(lines.c.preparation_id == scope.preparation)).mappings().one())
        line.update(id=str(uuid4()), preparation_id=sibling["id"])
        session.execute(insert(lines).values(**line))
        session.commit()
        with pytest.raises(IntegrityError) as error:
            session.execute(update(locks).where(locks.c.preparation_id == scope.preparation).values(preparation_line_id=line["id"]))
        assert error.value.orig.sqlstate == "23503"
        session.rollback()


@pytest.fixture
def billing_scope(postgres_test_environment):
    suffix = uuid4().hex
    tenant, org = f"tenant-{suffix}", f"org-{suffix}"
    with postgres_test_environment.admin_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO tenants (id, tenant_code, display_name, tenant_status, is_active, version) "
            "VALUES (:id, :code, 'Billing race', 'active', true, 1)"
        ), {"id": tenant, "code": suffix})
        _seed_scope(connection, suffix=suffix, tenant_id=tenant, organization_id=org)
    return SimpleNamespace(
        tenant=tenant, org=org, project=f"r6b-billing-project-{suffix}",
        preparation=f"r6b-billing-preparation-{suffix}", schedule=f"r6b-billing-schedule-{suffix}",
        require_active_scope_ids=lambda **_: ActiveScopeIds(tenant, org),
        get_active_tenant_id=lambda: tenant,
        get_active_organization_id=lambda: org,
    )


def _repository(session, scope):
    validate_postgresql_execution_role(session)
    session.execute(text("SET LOCAL lock_timeout = '8s'"))
    repo = SqlAlchemyProjectBillingRepository(session)
    repo._tenant_context_service = scope
    return repo


@pytest.mark.parametrize("aggregate", ["profile", "schedule", "preparation", "submit", "approve_reject"])
def test_live_billing_version_race(postgres_test_environment, billing_scope, aggregate):
    scope = billing_scope
    barrier = Barrier(2)
    initial_status = "draft" if aggregate == "submit" else "submitted"
    if aggregate in {"submit", "approve_reject"}:
        with postgres_test_environment.admin_engine.begin() as connection:
            connection.execute(text(
                "UPDATE project_billing_preparations SET status=:status WHERE id=:id"
            ), {"status": initial_status, "id": scope.preparation})

    def writer(index):
        with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as session:
            repo = _repository(session, scope)
            if aggregate == "profile":
                value = repo.get_profile(scope.project)
                value.contract_reference = f"winner-{index}"
                save = repo.update_profile
            elif aggregate == "schedule":
                value = repo.get_schedule_line(scope.schedule)
                value.name = f"winner-{index}"
                save = repo.update_schedule_line
            else:
                value = repo.get_preparation(scope.preparation)
                value.total_amount = Decimal(100 + index)
                if aggregate == "submit":
                    value.status = BillingPreparationStatus.SUBMITTED
                elif aggregate == "approve_reject":
                    value.status = BillingPreparationStatus.APPROVED if index == 0 else BillingPreparationStatus.REJECTED
                save = repo.update_preparation
            version = value.row_version
            barrier.wait(timeout=10)
            try:
                save(value, expected_row_version=version)
                session.commit()
                return "committed"
            except ConcurrencyError:
                session.rollback()
                return "stale"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(writer, [0, 1]))
    assert sorted(results) == ["committed", "stale"]
    with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as session:
        repo = _repository(session, scope)
        value = repo.get_profile(scope.project) if aggregate == "profile" else (
            repo.get_schedule_line(scope.schedule) if aggregate == "schedule" else repo.get_preparation(scope.preparation)
        )
        assert value.row_version == 2


def test_live_billing_source_reservation_race_is_atomic(postgres_test_environment, billing_scope):
    scope = billing_scope
    source = str(uuid4())
    barrier = Barrier(2)

    def writer(_):
        with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as session:
            repo = _repository(session, scope)
            preparation = deepcopy(repo.get_preparation(scope.preparation))
            preparation.id = str(uuid4())
            preparation.preparation_number = preparation.id
            preparation.idempotency_key = preparation.id
            preparation.status = BillingPreparationStatus.DRAFT
            line = deepcopy(repo.list_preparation_lines(scope.preparation)[0])
            lock = deepcopy(repo.list_source_locks(scope.preparation)[0])
            line.id, lock.id = str(uuid4()), str(uuid4())
            line.preparation_id = lock.preparation_id = preparation.id
            line.source_id = lock.source_id = source
            lock.preparation_line_id = line.id
            barrier.wait(timeout=10)
            try:
                repo.add_preparation(preparation)
                repo.reserve_source(line, lock)
                session.commit()
                return "committed"
            except IntegrityError as error:
                session.rollback()
                assert error.orig.sqlstate == "23505"
                return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(writer, [0, 1])) == ["committed", "duplicate"]
    with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as session:
        validate_postgresql_execution_role(session)
        assert session.scalar(text("SELECT count(*) FROM project_billing_preparation_lines WHERE source_id=:source"), {"source": source}) == 1
        assert session.scalar(text("SELECT count(*) FROM project_billing_source_locks WHERE source_id=:source"), {"source": source}) == 1
        assert session.scalar(text("SELECT count(*) FROM project_billing_preparations WHERE project_id=:project"), {"project": scope.project}) == 2


@pytest.mark.parametrize("failure", ["none", "audit", "event", "after_write"])
def test_governed_billing_reservation_atomicity(postgres_test_environment, billing_scope, failure):
    scope = billing_scope
    with postgres_test_environment.admin_engine.begin() as connection:
        connection.execute(text("DELETE FROM project_billing_preparation_lines WHERE preparation_id=:id"), {"id": scope.preparation})
        connection.execute(text(
            "UPDATE project_billing_preparations SET status='draft', line_count=0, total_amount=0 WHERE id=:id"
        ), {"id": scope.preparation})
    user_session = UserSessionContext()
    permissions = frozenset({"finance.manage", "finance.read"})
    user_session.set_principal(UserSessionPrincipal(
        user_id="billing-runtime-user", username="billing-runtime-user", display_name="Billing User",
        role_names=frozenset(), permissions=permissions,
        scoped_access={"project": {scope.project: permissions}},
        active_tenant_id=scope.tenant, active_organization_id=scope.org,
    ))
    user_session.set_active_tenant_id(scope.tenant)
    user_session.set_active_organization_id(scope.org)
    published = []
    bus = InProcessPostCommitEventBus()
    bus.subscribe(BillingPreparationLineAdded, lambda event, context: published.append(event))
    dispatcher = InProcessTransactionalEventDispatcher()

    def fail(*args, **kwargs):
        raise RuntimeError("injected billing failure")

    if failure == "event":
        dispatcher.subscribe(BillingPreparationLineAdded, fail)
    factory = SqlAlchemyFinanceGovernanceUnitOfWorkFactory(
        session_factory=sessionmaker(bind=postgres_test_environment.runtime_engine, expire_on_commit=False),
        transactional_dispatcher=dispatcher, post_commit_bus=bus,
        tenant_context_service=scope, user_session=user_session,
    )

    def operations(uow):
        validate_postgresql_execution_role(uow._session)
        audit = uow._enterprise_audit_service
        if failure == "audit":
            audit.record = fail
        service = ProjectBillingPreparationService(
            session=uow._session, billing_repo=uow.billing, financial_profile_repo=uow.profiles,
            cost_entry_repo=uow.cost_entries, labor_posting_repo=uow.labor_postings,
            rate_resolver=None, financial_period_service=None, approval_service=None,
            tenant_context_service=scope, clock=SystemClock(), user_session=user_session,
            enterprise_audit_service=audit, record_event=uow.record_event,
        )
        return SimpleNamespace(billing_preparations=service, post_commit_actions=[])

    boundary = FinanceGovernanceCommandBoundary(uow_factory=factory, operations_factory=operations)

    def command(service):
        result = service.add_fixed_price_source(scope.preparation, schedule_line_id=scope.schedule, expected_row_version=1)
        if failure == "after_write":
            fail()
        return result

    if failure == "none":
        boundary.billing_preparation(command)
    else:
        with pytest.raises(RuntimeError, match="injected billing failure"):
            boundary.billing_preparation(command)
    expected = int(failure == "none")
    with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as session:
        repo = _repository(session, scope)
        assert len(repo.list_preparation_lines(scope.preparation)) == expected
        assert len(repo.list_source_locks(scope.preparation)) == expected
        preparation = repo.get_preparation(scope.preparation)
        assert preparation.line_count == expected
        assert preparation.row_version == 1 + expected
        assert preparation.total_amount == Decimal("5000.25") * expected
        assert session.scalar(text("SELECT count(*) FROM audit_entries WHERE organization_id=:org"), {"org": scope.org}) == expected
    assert len(published) == expected


def test_live_billing_correction_branch_race(postgres_test_environment, billing_scope):
    scope = billing_scope
    barrier = Barrier(2)

    def writer(_):
        with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as session:
            repo = _repository(session, scope)
            correction = deepcopy(repo.get_preparation(scope.preparation))
            correction.id = str(uuid4())
            correction.preparation_number = correction.id
            correction.idempotency_key = correction.id
            correction.correction_of_preparation_id = scope.preparation
            correction.status = BillingPreparationStatus.DRAFT
            correction.created_at = datetime.now(timezone.utc)
            barrier.wait(timeout=10)
            try:
                repo.add_preparation(correction)
                session.commit()
                return "committed"
            except IntegrityError as error:
                session.rollback()
                assert error.orig.sqlstate == "23505"
                return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(writer, [0, 1])) == ["committed", "duplicate"]


@pytest.mark.parametrize("action", ["submit", "decision"])
def test_governed_billing_application_race(postgres_test_environment, billing_scope, action):
    scope = billing_scope
    actor = str(uuid4())
    now = datetime.now(timezone.utc)
    with postgres_test_environment.admin_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users (id, username, password_hash, account_type, is_active, created_at, updated_at, version) "
            "VALUES (:id, :id, 'not-login-capable', 'human', true, :now, :now, 1)"
        ), {"id": actor, "now": now})
        connection.execute(text(
            "UPDATE project_billing_preparations SET status=:status WHERE id=:id"
        ), {"status": "draft" if action == "submit" else "submitted", "id": scope.preparation})
        connection.execute(text(
            "UPDATE project_billing_source_locks SET status='reserved', finalized_at=NULL WHERE preparation_id=:id"
        ), {"id": scope.preparation})
    user = UserSessionContext()
    permissions = frozenset({"finance.manage", "finance.read", "approval.decide"})
    user.set_principal(UserSessionPrincipal(
        user_id=actor, username=actor, display_name="Independent reviewer",
        role_names=frozenset(), permissions=permissions, scoped_access={"project": {scope.project: permissions}},
        active_tenant_id=scope.tenant, active_organization_id=scope.org,
    ))
    user.set_active_tenant_id(scope.tenant)
    user.set_active_organization_id(scope.org)
    barrier = Barrier(2)
    factory = SqlAlchemyFinanceGovernanceUnitOfWorkFactory(
        session_factory=sessionmaker(bind=postgres_test_environment.runtime_engine, expire_on_commit=False),
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=InProcessPostCommitEventBus(), tenant_context_service=scope, user_session=user,
    )

    def operations(uow):
        validate_postgresql_execution_role(uow._session)
        uow._session.execute(text("SET LOCAL lock_timeout = '8s'"))
        service = ProjectBillingPreparationService(
            session=uow._session, billing_repo=uow.billing, financial_profile_repo=uow.profiles,
            cost_entry_repo=uow.cost_entries, labor_posting_repo=uow.labor_postings,
            rate_resolver=None, financial_period_service=None, approval_service=None,
            tenant_context_service=scope, clock=SystemClock(), user_session=user,
            enterprise_audit_service=uow._enterprise_audit_service, record_event=uow.record_event,
        )
        service._approval_repo = uow.approvals
        read = service._require_preparation

        def synchronized_read(preparation_id):
            result = read(preparation_id)
            barrier.wait(timeout=10)
            return result

        service._require_preparation = synchronized_read
        return SimpleNamespace(billing_preparations=service, post_commit_actions=[])

    boundary = FinanceGovernanceCommandBoundary(uow_factory=factory, operations_factory=operations)

    def writer(index):
        def command(service):
            if action == "submit":
                return service.submit_preparation(scope.preparation, expected_row_version=1)
            if index == 0:
                return service._apply_approval_decision(scope.preparation, approved_by=actor, expected_version=1)
            return service._apply_rejection_decision(scope.preparation, rejected_by=actor, expected_version=1, notes="Needs correction")
        try:
            boundary.billing_preparation(command)
            return "committed"
        except ConcurrencyError:
            return "stale"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(writer, [0, 1])) == ["committed", "stale"]
    with postgres_test_environment.runtime_session(tenant_id=scope.tenant, organization_id=scope.org) as session:
        repo = _repository(session, scope)
        preparation = repo.get_preparation(scope.preparation)
        assert preparation.row_version == 2
        if action == "submit":
            assert preparation.status is BillingPreparationStatus.SUBMITTED
            assert session.scalar(text("SELECT count(*) FROM approval_requests WHERE entity_id=:id"), {"id": scope.preparation}) == 1
        else:
            expected = "finalized" if preparation.status is BillingPreparationStatus.APPROVED else "released"
            assert preparation.status in {BillingPreparationStatus.APPROVED, BillingPreparationStatus.REJECTED}
            assert {lock.status.value for lock in repo.list_source_locks(scope.preparation)} == {expected}
