from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillingPreparationStatus,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.invoicing.billing import (
    SqlAlchemyProjectBillingRepository,
)
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds
from src.core.platform.common.exceptions import ConcurrencyError
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role
from src.tests.integration.postgresql.test_r6b_billing_reader import _seed_scope

pytestmark = pytest.mark.postgresql_integration


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
            line = deepcopy(repo.list_preparation_lines(scope.preparation)[0])
            lock = deepcopy(repo.list_source_locks(scope.preparation)[0])
            line.id, lock.id = str(uuid4()), str(uuid4())
            line.source_id = lock.source_id = source
            lock.preparation_line_id = line.id
            barrier.wait(timeout=10)
            try:
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
        repo = _repository(session, scope)
        assert len([row for row in repo.list_preparation_lines(scope.preparation) if row.source_id == source]) == 1
        assert len([row for row in repo.list_source_locks(scope.preparation) if row.source_id == source]) == 1


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
