from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from threading import Event, Thread
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import (
    ProjectCostEntryService,
)
from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceCommandBoundary,
    FinanceGovernanceOperations,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
)
from src.core.platform.application.finance.financial_period_service import (
    FinancialPeriodService,
)
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError
from src.core.platform.domain.security.auth.session import (
    UserSessionContext,
    UserSessionPrincipal,
)
from src.infra.events.in_process_post_commit_event_bus import InProcessPostCommitEventBus
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role


pytestmark = pytest.mark.postgresql_integration

TENANT_A = "r6dc-tenant-a"
TENANT_B = "r6dc-tenant-b"
ORG_A = "r6dc-org-a"
ORG_A2 = "r6dc-org-a2"
ORG_B = "r6dc-org-b"
PROJECT_A = "r6dc-project-a"
PROJECT_A2 = "r6dc-project-a2"
COST_A = "r6dc-cost-a"
COST_B = "r6dc-cost-b"
TASK_A2 = "r6dc-task-a2"
RESOURCE_A = "r6dc-resource-a"
RESOURCE_B = "r6dc-resource-b"
PERIOD_A = "r6dc-period-a"
POSTED_A = "r6dc-posted-a"
POSTED_A2 = "r6dc-posted-a2"


class _TenantContext:
    def __init__(self, tenant_id: str, organization_id: str) -> None:
        self.tenant_id = tenant_id
        self.organization_id = organization_id

    def require_active_scope_ids(self, *, operation_label):
        del operation_label
        return ActiveScopeIds(self.tenant_id, self.organization_id)

    def require_organization_context(self, *, operation_label):
        del operation_label
        return SimpleNamespace(
            tenant_id=self.tenant_id,
            organization_id=self.organization_id,
            organization=SimpleNamespace(base_currency="USD"),
        )

    def get_active_tenant_id(self):
        return self.tenant_id

    def get_active_organization_id(self):
        return self.organization_id


@pytest.fixture(scope="module", autouse=True)
def seeded_actual_scopes(postgres_test_environment):
    now = datetime(2026, 9, 9, 10, 0, tzinfo=timezone.utc)
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant_id, code in ((TENANT_A, "R6DC-A"), (TENANT_B, "R6DC-B")):
            connection.execute(
                text(
                    "INSERT INTO tenants "
                    "(id, tenant_code, display_name, tenant_status, is_active, version) "
                    "VALUES (:id, :code, :code, 'active', true, 1)"
                ),
                {"id": tenant_id, "code": code},
            )
        for tenant_id, org_id, code in (
            (TENANT_A, ORG_A, "R6DC-ORG-A"),
            (TENANT_A, ORG_A2, "R6DC-ORG-A2"),
            (TENANT_B, ORG_B, "R6DC-ORG-B"),
        ):
            connection.execute(
                text(
                    "INSERT INTO organizations "
                    "(id, tenant_id, organization_code, display_name, timezone_name, "
                    "base_currency, is_enabled, version) "
                    "VALUES (:org, :tenant, :code, :code, 'UTC', 'USD', true, 1)"
                ),
                {"org": org_id, "tenant": tenant_id, "code": code},
            )
        for project_id, org_id, code in (
            (PROJECT_A, ORG_A, "R6DC-P-A"),
            (PROJECT_A2, ORG_A, "R6DC-P-A2"),
        ):
            connection.execute(
                text(
                    "INSERT INTO projects "
                    "(id, tenant_id, project_code, name, description, status, "
                    "organization_id, version) VALUES "
                    "(:id, :tenant, :code, :code, '', 'ACTIVE', :org, 1)"
                ),
                {"id": project_id, "tenant": TENANT_A, "code": code, "org": org_id},
            )
        for cost_id, tenant_id, org_id, code in (
            (COST_A, TENANT_A, ORG_A, "R6DC-COST-A"),
            (COST_B, TENANT_B, ORG_B, "R6DC-COST-B"),
        ):
            connection.execute(
                text(
                    "INSERT INTO project_finance_cost_codes "
                    "(id, tenant_id, organization_id, code, name, is_active, version, "
                    "created_at, updated_at) VALUES "
                    "(:id, :tenant, :org, :code, :code, true, 1, :now, :now)"
                ),
                {
                    "id": cost_id,
                    "tenant": tenant_id,
                    "org": org_id,
                    "code": code,
                    "now": now,
                },
            )
        connection.execute(
            text(
                "INSERT INTO project_finance_profiles "
                "(id, tenant_id, organization_id, project_id, currency_code, version, "
                "created_at, updated_at) VALUES "
                "('r6dc-profile-a', :tenant, :org, :project, 'USD', 1, :now, :now)"
            ),
            {"tenant": TENANT_A, "org": ORG_A, "project": PROJECT_A, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO financial_periods "
                "(id, tenant_id, organization_id, code, name, fiscal_year, "
                "period_number, start_date, end_date, status, version, created_by, "
                "created_at, updated_by, updated_at) VALUES "
                "(:id, :tenant, :org, 'R6DC-P01', 'R6D-C September', 2026, 9, "
                ":start, :end, 'open', 1, 'seed', :now, 'seed', :now)"
            ),
            {
                "id": PERIOD_A,
                "tenant": TENANT_A,
                "org": ORG_A,
                "start": date(2026, 9, 1),
                "end": date(2026, 9, 30),
                "now": now,
            },
        )
        for entry_id, project_id in (
            (POSTED_A, PROJECT_A),
            (POSTED_A2, PROJECT_A2),
        ):
            connection.execute(
                text(
                    "INSERT INTO project_cost_entries "
                    "(id, tenant_id, organization_id, project_id, description, "
                    "entry_kind, status, amount, currency_code, base_amount, "
                    "base_currency_code, exchange_rate, exchange_rate_date, "
                    "exchange_rate_source, exchange_rate_captured_at, transaction_date, "
                    "posting_date, financial_period_id, cost_code_id, source_module, "
                    "source_type, source_id, source_revision, source_content_hash, "
                    "posting_purpose, idempotency_key, version, created_by, created_at, "
                    "updated_by, updated_at, posted_by, posted_at, rejection_notes) VALUES "
                    "(:id, :tenant, :org, :project, 'Posted reversal fixture', "
                    "'actual', 'posted', 100.00, 'USD', 100.00, 'USD', 1.0, :day, "
                    "'same-currency', :now, :day, :day, :period, :cost, "
                    "'project_management', 'manual_command', :id, '1', :hash, "
                    "'manual_actual', :idempotency, 1, 'seed', :now, 'seed', :now, "
                    "'seed', :now, '')"
                ),
                {
                    "id": entry_id,
                    "tenant": TENANT_A,
                    "org": ORG_A,
                    "project": project_id,
                    "day": date(2026, 9, 9),
                    "period": PERIOD_A,
                    "cost": COST_A,
                    "hash": "b" * 64,
                    "idempotency": f"r6dc:{entry_id}",
                    "now": now,
                },
            )
        connection.execute(
            text(
                "INSERT INTO tasks "
                "(id, project_id, task_code, wbs_code, sort_order, name, description, "
                "status, priority, percent_complete, is_milestone, version) VALUES "
                "(:id, :project, 'R6DC-T-A2', '1', 0, 'Foreign task', '', "
                "'TODO', 0, 0, false, 1)"
            ),
            {"id": TASK_A2, "project": PROJECT_A2},
        )
        for resource_id, tenant_id, org_id, code in (
            (RESOURCE_A, TENANT_A, ORG_A, "R6DC-R-A"),
            (RESOURCE_B, TENANT_B, ORG_B, "R6DC-R-B"),
        ):
            connection.execute(
                text(
                    "INSERT INTO resources "
                    "(id, tenant_id, organization_id, resource_code, name, kind, role, "
                    "hourly_rate, is_active, capacity_percent, cost_type, worker_type, version) "
                    "VALUES (:id, :tenant, :org, :code, :code, 'PERSON', '', 0, true, "
                    "100, 'LABOR', 'EXTERNAL', 1)"
                ),
                {
                    "id": resource_id,
                    "tenant": tenant_id,
                    "org": org_id,
                    "code": code,
                },
            )


def _user_session() -> UserSessionContext:
    permissions = frozenset(
        {
            "finance.read",
            "project_cost.create",
            "project_cost.update_draft",
            "project_cost.submit",
            "project_cost.approve",
            "project_cost.post",
            "project_cost.reverse",
        }
    )
    user_session = UserSessionContext()
    user_session.set_principal(
        UserSessionPrincipal(
            user_id="r6dc-runtime-user",
            username="r6dc-runtime-user",
            display_name="R6D-C Runtime User",
            role_names=frozenset(),
            permissions=permissions,
            scoped_access={"project": {PROJECT_A: permissions}},
            active_tenant_id=TENANT_A,
            active_organization_id=ORG_A,
        )
    )
    user_session.set_active_tenant_id(TENANT_A)
    user_session.set_active_organization_id(ORG_A)
    return user_session


def _boundary(postgres_test_environment):
    user_session = _user_session()
    scope = _TenantContext(TENANT_A, ORG_A)
    factory = SqlAlchemyFinanceGovernanceUnitOfWorkFactory(
        session_factory=sessionmaker(
            bind=postgres_test_environment.runtime_engine,
            expire_on_commit=False,
        ),
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=InProcessPostCommitEventBus(),
        tenant_context_service=scope,
        user_session=user_session,
    )

    def operations(uow):
        period_service = FinancialPeriodService(
            session=uow._session,
            period_repo=uow.financial_periods,
            tenant_context_service=scope,
            user_session=user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
        )
        cost_entries = ProjectCostEntryService(
            session=uow._session,
            entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            resource_repo=uow.resources,
            financial_period_service=period_service,
            clock=SystemClock(),
            user_session=user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            tenant_context_service=scope,
            record_event=uow.record_event,
        )
        empty = SimpleNamespace()
        return FinanceGovernanceOperations(
            budgets=empty,
            forecast_versions=empty,
            forecast_generation=empty,
            financial_changes=empty,
            financial_setup=empty,
            rate_cards=empty,
            planned_costs=empty,
            cost_entries=cost_entries,
            billing_profiles=empty,
            billing_preparations=empty,
        )

    return FinanceGovernanceCommandBoundary(
        uow_factory=factory,
        operations_factory=operations,
    )


def _insert_draft(
    session,
    *,
    row_id: str,
    tenant_id: str,
    organization_id: str,
    project_id: str,
    cost_code_id: str,
    task_id=None,
    resource_id=None,
):
    now = datetime.now(timezone.utc)
    session.execute(
        text(
            "INSERT INTO project_cost_entries "
            "(id, tenant_id, organization_id, project_id, description, entry_kind, "
            "status, amount, currency_code, transaction_date, cost_code_id, task_id, "
            "resource_id, source_module, source_type, source_id, source_revision, "
            "source_content_hash, posting_purpose, idempotency_key, version, created_by, "
            "created_at, updated_by, updated_at, rejection_notes) VALUES "
            "(:id, :tenant, :org, :project, 'R6D-C attack probe', 'actual', 'draft', "
            "10.00, 'USD', :day, :cost, :task, :resource, 'project_management', "
            "'manual_command', :id, '1', :hash, 'manual_actual', :idempotency, 1, "
            "'probe', :now, 'probe', :now, '')"
        ),
        {
            "id": row_id,
            "tenant": tenant_id,
            "org": organization_id,
            "project": project_id,
            "day": date(2026, 9, 9),
            "cost": cost_code_id,
            "task": task_id,
            "resource": resource_id,
            "hash": "a" * 64,
            "idempotency": f"r6dc:{row_id}",
            "now": now,
        },
    )


def _insert_reversal(session, *, row_id: str, project_id: str, original_id: str):
    now = datetime.now(timezone.utc)
    session.execute(
        text(
            "INSERT INTO project_cost_entries "
            "(id, tenant_id, organization_id, project_id, description, entry_kind, "
            "status, amount, currency_code, base_amount, base_currency_code, "
            "exchange_rate, exchange_rate_date, exchange_rate_source, "
            "exchange_rate_captured_at, transaction_date, posting_date, "
            "financial_period_id, cost_code_id, source_module, source_type, source_id, "
            "source_revision, source_content_hash, posting_purpose, idempotency_key, "
            "reverses_entry_id, version, created_by, created_at, updated_by, updated_at, "
            "posted_by, posted_at, rejection_notes) VALUES "
            "(:id, :tenant, :org, :project, 'Signed reversal probe', 'reversal', "
            "'posted', -100.00, 'USD', -100.00, 'USD', 1.0, :day, 'same-currency', "
            ":now, :day, :day, :period, :cost, 'project_management', "
            "'manual_command', :id, '1', :hash, 'manual_actual', :idempotency, "
            ":original, 1, 'probe', :now, 'probe', :now, 'probe', :now, '')"
        ),
        {
            "id": row_id,
            "tenant": TENANT_A,
            "org": ORG_A,
            "project": project_id,
            "day": date(2026, 9, 10),
            "period": PERIOD_A,
            "cost": COST_A,
            "hash": "c" * 64,
            "idempotency": f"r6dc:{row_id}",
            "original": original_id,
            "now": now,
        },
    )


def test_manual_actual_command_uses_runtime_role_fresh_uow_and_stale_write_guard(
    postgres_test_environment,
):
    boundary = _boundary(postgres_test_environment)
    draft = boundary.cost_entry(
        lambda service: service.create_manual_entry(
            project_id=PROJECT_A,
            command_id="r6dc-runtime-create",
            description="Runtime governed actual",
            amount=Decimal("125.40"),
            currency_code="USD",
            transaction_date=date(2026, 9, 9),
            cost_code_id=COST_A,
            resource_id=RESOURCE_A,
        )
    )
    updated = boundary.cost_entry(
        lambda service: service.update_draft(
            draft.id,
            expected_version=draft.row_version,
            description="Runtime governed actual corrected",
            amount=Decimal("126.40"),
            currency_code="USD",
            transaction_date=date(2026, 9, 9),
            cost_code_id=COST_A,
            resource_id=RESOURCE_A,
        )
    )
    assert updated.amount == Decimal("126.40")
    with pytest.raises(ConcurrencyError):
        boundary.cost_entry(
            lambda service: service.update_draft(
                draft.id,
                expected_version=draft.row_version,
                description="Stale overwrite",
                amount=Decimal("999.00"),
                currency_code="USD",
                transaction_date=date(2026, 9, 9),
                cost_code_id=COST_A,
                resource_id=RESOURCE_A,
            )
        )

    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A,
        organization_id=ORG_A,
    )
    try:
        validate_postgresql_execution_role(session)
        assert session.scalar(
            text("SELECT amount FROM project_cost_entries WHERE id=:id"),
            {"id": draft.id},
        ) == Decimal("126.4000")
    finally:
        session.close()


def test_project_permission_denies_same_organization_foreign_project(
    postgres_test_environment,
):
    boundary = _boundary(postgres_test_environment)
    with pytest.raises(BusinessRuleError) as denied:
        boundary.cost_entry(
            lambda service: service.create_manual_entry(
                project_id=PROJECT_A2,
                command_id="r6dc-foreign-project",
                description="Must be denied",
                amount=Decimal("10.00"),
                currency_code="USD",
                transaction_date=date(2026, 9, 9),
                cost_code_id=COST_A,
            )
        )
    assert denied.value.code == "PERMISSION_DENIED"


@pytest.mark.parametrize(
    ("scope", "row_scope", "row_id"),
    (
        ((TENANT_B, ORG_B), (TENANT_A, ORG_A), "r6dc-tenant-attack"),
        ((TENANT_A, ORG_A2), (TENANT_A, ORG_A), "r6dc-org-attack"),
    ),
)
def test_runtime_rls_denies_foreign_cost_entry_insert(
    postgres_test_environment, scope, row_scope, row_id
):
    session = postgres_test_environment.runtime_session(
        tenant_id=scope[0], organization_id=scope[1]
    )
    try:
        with pytest.raises(DBAPIError):
            _insert_draft(
                session,
                row_id=row_id,
                tenant_id=row_scope[0],
                organization_id=row_scope[1],
                project_id=PROJECT_A,
                cost_code_id=COST_A,
            )
            session.commit()
    finally:
        session.rollback()
        session.close()


@pytest.mark.parametrize(
    ("row_id", "cost_code_id", "task_id", "resource_id"),
    (
        ("r6dc-cost-ref-attack", COST_B, None, None),
        ("r6dc-task-ref-attack", COST_A, TASK_A2, None),
        ("r6dc-resource-ref-attack", COST_A, None, RESOURCE_B),
    ),
)
def test_scoped_foreign_keys_deny_foreign_actual_dimensions(
    postgres_test_environment, row_id, cost_code_id, task_id, resource_id
):
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    try:
        with pytest.raises(DBAPIError):
            _insert_draft(
                session,
                row_id=row_id,
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                cost_code_id=cost_code_id,
                task_id=task_id,
                resource_id=resource_id,
            )
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_actual_filter_index_exists(postgres_test_environment):
    with postgres_test_environment.admin_engine.connect() as connection:
        index_names = set(
            connection.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname='public' AND tablename='project_cost_entries'"
                )
            ).scalars()
        )
    assert "idx_project_cost_entries_scope_filters" in index_names


def test_foreign_project_reversal_original_is_denied(postgres_test_environment):
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    try:
        with pytest.raises(DBAPIError):
            _insert_reversal(
                session,
                row_id="r6dc-foreign-original-attack",
                project_id=PROJECT_A,
                original_id=POSTED_A2,
            )
            session.commit()
    finally:
        session.rollback()
        session.close()


def test_concurrent_reversal_inserts_allow_exactly_one_offset(
    postgres_test_environment,
):
    first = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    second_started = Event()
    second_finished = Event()
    failures: list[BaseException] = []

    _insert_reversal(
        first,
        row_id="r6dc-race-reversal-a",
        project_id=PROJECT_A,
        original_id=POSTED_A,
    )

    def contend() -> None:
        second = postgres_test_environment.runtime_session(
            tenant_id=TENANT_A, organization_id=ORG_A
        )
        try:
            second_started.set()
            _insert_reversal(
                second,
                row_id="r6dc-race-reversal-b",
                project_id=PROJECT_A,
                original_id=POSTED_A,
            )
            second.commit()
        except BaseException as exc:  # pragma: no cover - asserted in main thread
            failures.append(exc)
            second.rollback()
        finally:
            second.close()
            second_finished.set()

    contender = Thread(target=contend, daemon=True)
    contender.start()
    assert second_started.wait(timeout=2)
    assert not second_finished.wait(timeout=0.2)
    first.commit()
    first.close()

    assert second_finished.wait(timeout=5)
    contender.join(timeout=1)
    assert len(failures) == 1
    assert isinstance(failures[0], DBAPIError)

    check = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    try:
        assert check.scalar(
            text(
                "SELECT count(*) FROM project_cost_entries "
                "WHERE reverses_entry_id=:original"
            ),
            {"original": POSTED_A},
        ) == 1
    finally:
        check.close()
