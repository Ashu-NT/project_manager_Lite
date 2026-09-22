from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.cost.entries.approved_time_consumer import (
    APPROVED_TIME_FINANCE_PRINCIPAL_NAME,
    ApprovedTimeLaborCostConsumer,
)
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import (
    ProjectCostEntryService,
)
from src.core.modules.project_management.application.financials.governance.command_boundary import (
    FinanceGovernanceCommandBoundary,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import (
    RateCardResolver,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_service import (
    ProjectRateCardService,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialSourceModule,
    FinancialSourceReference,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_integration_facts import (
    ApprovedTimePostingFailureQuery,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryStatus,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.modules.project_management.infrastructure.persistence.orm.cost_entry import (
    ProjectCostEntryORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.labor_posting import (
    ApprovedTimeLaborPostingORM,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.sqlalchemy_finance_integration_reader import (
    SqlAlchemyFinanceIntegrationReader,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.cost_entries.cost_entry import (
    SqlAlchemyProjectCostEntryRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
)
from src.core.platform.application.finance.financial_period_service import (
    FinancialPeriodService,
)
from src.core.platform.application.integration import IntegrationOutboxService
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth.session import (
    UserSessionContext,
    UserSessionPrincipal,
)
from src.core.platform.domain.security.identity.service_principal import (
    ServicePrincipal,
)
from src.core.platform.finance import DecimalQuantity, DecimalQuantityPayload
from src.core.platform.infrastructure.persistence.repositories.time_management.time_financial_outbox import (
    SqlAlchemyTimeFinancialOutboxRepository,
)
from src.core.platform.integration import (
    APPROVED_TIME_ENTRY_EVENT_TYPE,
    ApprovedTimeEntryEventPayload,
    IntegrationEventEnvelope,
)
from src.core.platform.integration.canonical_json import canonical_json_sha256
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.integration.approved_time_dispatcher import (
    ApprovedTimeFinancialDispatcher,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role

pytestmark = pytest.mark.postgresql_integration

TENANT_A = "r6dd-tenant-a"
TENANT_B = "r6dd-tenant-b"
ORG_A = "r6dd-org-a"
ORG_B = "r6dd-org-b"
PROJECT_A = "r6dd-project-a"
PROJECT_B = "r6dd-project-b"
RESOURCE_A = "r6dd-resource-a"
TASK_A = "r6dd-task-a"
COST_CODE_A = "r6dd-cost-a"
PERIOD_A = "r6dd-period-a"
RATE_CARD_A = "r6dd-rate-card-a"
RATE_LINE_A = "r6dd-rate-line-a"
RESOURCE_RACE = "r6df-resource-rate-race"
RATE_LINE_RACE = "r6df-rate-line-race"
SERVICE_USER_A = "r6dd-service-user-a"
SERVICE_PRINCIPAL_A = "r6dd-service-principal-a"


class _TenantContext:
    def require_active_scope_ids(self, *, operation_label):
        del operation_label
        return ActiveScopeIds(TENANT_A, ORG_A)

    def require_organization_context(self, *, operation_label):
        del operation_label
        return SimpleNamespace(
            tenant_id=TENANT_A,
            organization_id=ORG_A,
            organization=SimpleNamespace(base_currency="USD"),
        )

    def get_active_tenant_id(self):
        return TENANT_A

    def get_active_organization_id(self):
        return ORG_A

    def require_active_organization_id(self, *, operation_label):
        del operation_label
        return ORG_A


def seed_approved_time_scope(postgres_test_environment):
    now = datetime(2026, 9, 10, 9, 0, tzinfo=timezone.utc)
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant_id, code in ((TENANT_A, "R6DD-A"), (TENANT_B, "R6DD-B")):
            connection.execute(
                text(
                    "INSERT INTO tenants "
                    "(id, tenant_code, display_name, tenant_status, is_active, version) "
                    "VALUES (:id, :code, :code, 'active', true, 1)"
                ),
                {"id": tenant_id, "code": code},
            )
        for tenant_id, org_id, code in (
            (TENANT_A, ORG_A, "R6DD-ORG-A"),
            (TENANT_B, ORG_B, "R6DD-ORG-B"),
        ):
            connection.execute(
                text(
                    "INSERT INTO organizations "
                    "(id, tenant_id, organization_code, display_name, timezone_name, "
                    "base_currency, status, version) "
                    "VALUES (:org, :tenant, :code, :code, 'UTC', 'USD', 'active', 1)"
                ),
                {"org": org_id, "tenant": tenant_id, "code": code},
            )
        for project_id, tenant_id, org_id, code in (
            (PROJECT_A, TENANT_A, ORG_A, "R6DD-P-A"),
            (PROJECT_B, TENANT_B, ORG_B, "R6DD-P-B"),
        ):
            connection.execute(
                text(
                    "INSERT INTO projects "
                    "(id, tenant_id, project_code, name, description, status, "
                    "organization_id, version) VALUES "
                    "(:id, :tenant, :code, :code, '', 'ACTIVE', :org, 1)"
                ),
                {
                    "id": project_id,
                    "tenant": tenant_id,
                    "org": org_id,
                    "code": code,
                },
            )
        connection.execute(
            text(
                "INSERT INTO resources "
                "(id, tenant_id, organization_id, resource_code, name, kind, role, "
                "hourly_rate, is_active, capacity_percent, cost_type, worker_type, version) "
                "VALUES (:id, :tenant, :org, 'R6DD-R-A', 'R6D-D Engineer', 'PERSON', "
                "'Engineer', 999, true, 100, 'LABOR', 'EXTERNAL', 1)"
            ),
            {"id": RESOURCE_A, "tenant": TENANT_A, "org": ORG_A},
        )
        connection.execute(
            text(
                "INSERT INTO tasks "
                "(id, project_id, task_code, wbs_code, sort_order, name, description, "
                "status, priority, percent_complete, is_milestone, version) VALUES "
                "(:id, :project, 'R6DD-T-A', '1', 0, 'Approved work', '', "
                "'TODO', 0, 0, false, 1)"
            ),
            {"id": TASK_A, "project": PROJECT_A},
        )
        connection.execute(
            text(
                "INSERT INTO project_finance_cost_codes "
                "(id, tenant_id, organization_id, code, name, is_active, version, "
                "created_at, updated_at) VALUES "
                "(:id, :tenant, :org, 'LABOR', 'Approved labor', true, 1, :now, :now)"
            ),
            {
                "id": COST_CODE_A,
                "tenant": TENANT_A,
                "org": ORG_A,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO project_finance_profiles "
                "(id, tenant_id, organization_id, project_id, currency_code, status, "
                "default_cost_code_id, version, created_at, updated_at) VALUES "
                "('r6dd-profile-a', :tenant, :org, :project, 'USD', 'active', "
                ":cost, 1, :now, :now)"
            ),
            {
                "tenant": TENANT_A,
                "org": ORG_A,
                "project": PROJECT_A,
                "cost": COST_CODE_A,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO financial_periods "
                "(id, tenant_id, organization_id, code, name, fiscal_year, period_number, "
                "start_date, end_date, status, version, created_by, created_at, updated_by, updated_at) "
                "VALUES (:id, :tenant, :org, 'R6DD-P09', 'September 2026', 2026, 9, "
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
        connection.execute(
            text(
                "INSERT INTO project_finance_rate_cards "
                "(id, tenant_id, organization_id, project_id, name, version, is_active, "
                "created_at, updated_at) VALUES "
                "(:id, :tenant, :org, :project, 'Approved labor rates', 1, true, :now, :now)"
            ),
            {
                "id": RATE_CARD_A,
                "tenant": TENANT_A,
                "org": ORG_A,
                "project": PROJECT_A,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO project_finance_rate_card_lines "
                "(id, tenant_id, organization_id, rate_card_id, rate_type, origin, "
                "resource_id, is_active, unit, rate_amount, rate_currency, version, "
                "created_at, updated_at) VALUES "
                "(:id, :tenant, :org, :card, 'cost', 'configured', :resource, true, "
                "'HOUR', 42.12500000, 'USD', 1, :now, :now)"
            ),
            {
                "id": RATE_LINE_A,
                "tenant": TENANT_A,
                "org": ORG_A,
                "card": RATE_CARD_A,
                "resource": RESOURCE_A,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO users "
                "(id, username, password_hash, account_type, is_active, created_at, "
                "updated_at, version) VALUES "
                "(:id, 'r6dd-approved-time-worker', 'not-login-capable', 'service', "
                "true, :now, :now, 1)"
            ),
            {"id": SERVICE_USER_A, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO service_principals "
                "(id, tenant_id, organization_id, user_id, name, description, status, "
                "created_at, updated_at) VALUES "
                "(:id, :tenant, :org, :user, :name, 'Approved Time posting worker', "
                "'active', :now, :now)"
            ),
            {
                "id": SERVICE_PRINCIPAL_A,
                "tenant": TENANT_A,
                "org": ORG_A,
                "user": SERVICE_USER_A,
                "name": APPROVED_TIME_FINANCE_PRINCIPAL_NAME,
                "now": now,
            },
        )


@pytest.fixture(scope="module", autouse=True)
def seeded_approved_time_scope(postgres_test_environment):
    with postgres_test_environment.admin_engine.connect() as connection:
        exists = connection.scalar(
            text("SELECT EXISTS (SELECT 1 FROM tenants WHERE id=:id)"),
            {"id": TENANT_A},
        )
    if not exists:
        seed_approved_time_scope(postgres_test_environment)


def _build_dispatcher(postgres_test_environment):
    tenant_context = _TenantContext()
    user_session = UserSessionContext()
    user_session.set_active_tenant_id(TENANT_A)
    user_session.set_active_organization_id(ORG_A)
    source_session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A,
        organization_id=ORG_A,
    )
    outbox_repo = SqlAlchemyTimeFinancialOutboxRepository(source_session)
    outbox_repo._tenant_context_service = tenant_context
    outbox = IntegrationOutboxService(
        repository=outbox_repo,
        owner_module="platform_time",
        clock=SystemClock(),
    )
    transactional = InProcessTransactionalEventDispatcher()
    post_commit = InProcessPostCommitEventBus()
    uow_factory = SqlAlchemyFinanceGovernanceUnitOfWorkFactory(
        session_factory=sessionmaker(
            bind=postgres_test_environment.runtime_engine,
            expire_on_commit=False,
            future=True,
        ),
        transactional_dispatcher=transactional,
        post_commit_bus=post_commit,
        tenant_context_service=tenant_context,
        user_session=user_session,
    )
    principal = ServicePrincipal(
        id=SERVICE_PRINCIPAL_A,
        tenant_id=TENANT_A,
        organization_id=ORG_A,
        user_id=SERVICE_USER_A,
        name=APPROVED_TIME_FINANCE_PRINCIPAL_NAME,
    )

    def consumer_factory(uow, service_principal):
        resolver = RateCardResolver(
            reader=SqlAlchemyRateResolutionReader(session=uow._session),
            tenant_context_service=tenant_context,
            clock=SystemClock(),
        )
        service = ProjectCostEntryService(
            session=uow._session,
            entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            resource_repo=uow.resources,
            financial_period_service=FinancialPeriodService(
                session=uow._session,
                period_repo=uow.financial_periods,
                tenant_context_service=tenant_context,
                user_session=user_session,
                enterprise_audit_service=uow._enterprise_audit_service,
            ),
            clock=SystemClock(),
            user_session=user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            tenant_context_service=tenant_context,
            rate_resolver=resolver,
            labor_posting_repo=uow.labor_postings,
        )
        return ApprovedTimeLaborCostConsumer(
            service,
            service_principal=service_principal,
        )

    dispatcher = ApprovedTimeFinancialDispatcher(
        session=source_session,
        outbox_service=outbox,
        uow_factory=uow_factory,
        consumer_factory=consumer_factory,
        principal_resolver=lambda: principal,
    )
    return source_session, outbox, dispatcher


def _approved_time_envelope(
    suffix: str = "a", *, resource_id: str = RESOURCE_A
) -> IntegrationEventEnvelope:
    work_date = date(2026, 9, 10)
    approved_at = datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc)
    suffix_token = "" if suffix == "a" else f"-{suffix}"
    time_entry_id = f"r6dd-time-entry-a{suffix_token}"
    facts = {
        "timesheet_period_id": f"r6dd-timesheet-period-a{suffix_token}",
        "time_entry_id": time_entry_id,
        "work_allocation_id": f"r6dd-work-allocation-a{suffix_token}",
        "resource_id": resource_id,
        "project_id": PROJECT_A,
        "organization_id": ORG_A,
        "employee_id": None,
        "assignment_id": f"r6dd-assignment-a{suffix_token}",
        "task_id": TASK_A,
        "work_date": work_date.isoformat(),
        "hours": DecimalQuantityPayload.from_domain(
            DecimalQuantity.of(Decimal("2.3750"), "HOUR")
        ).model_dump(mode="json"),
    }
    payload = ApprovedTimeEntryEventPayload(
        **facts,
        approved_snapshot_id=f"r6dd-approved-snapshot-a{suffix_token}",
        source_revision=1,
        source_content_hash=canonical_json_sha256(facts),
        approved_at=approved_at,
    )
    return IntegrationEventEnvelope(
        event_id=f"r6dd-approved-time-event-a{suffix_token}",
        event_type=APPROVED_TIME_ENTRY_EVENT_TYPE,
        schema_version=1,
        tenant_id=TENANT_A,
        organization_id=ORG_A,
        aggregate_type="time_entry",
        aggregate_id=time_entry_id,
        aggregate_version=1,
        occurred_at=approved_at,
        correlation_id=f"r6dd-timesheet-period-a{suffix_token}",
        payload=payload.model_dump(mode="json"),
    )


def _governed_rate_boundary(environment):
    scope = _TenantContext()
    permissions = frozenset({
        "finance.read", "finance.manage", "project_cost.create",
    })
    user_session = UserSessionContext()
    user_session.set_principal(UserSessionPrincipal(
        user_id="r6df-rate-editor", username="r6df-rate-editor",
        display_name="R6D-F Rate Editor", role_names=frozenset(),
        permissions=permissions,
        scoped_access={"project": {PROJECT_A: permissions}},
        active_tenant_id=TENANT_A, active_organization_id=ORG_A,
    ))
    user_session.set_active_tenant_id(TENANT_A)
    user_session.set_active_organization_id(ORG_A)
    factory = SqlAlchemyFinanceGovernanceUnitOfWorkFactory(
        session_factory=sessionmaker(bind=environment.runtime_engine, expire_on_commit=False),
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=InProcessPostCommitEventBus(),
        tenant_context_service=scope, user_session=user_session,
    )

    def operations(uow):
        period_service = FinancialPeriodService(
            session=uow._session, period_repo=uow.financial_periods,
            tenant_context_service=scope, user_session=user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
        )
        return SimpleNamespace(
            post_commit_actions=(),
            rate_cards=ProjectRateCardService(
                session=uow._session, rate_card_repo=uow.rate_cards,
                project_repo=uow.projects, user_session=user_session,
                enterprise_audit_service=uow._enterprise_audit_service,
                tenant_context_service=scope, record_event=uow.record_event,
            ),
            cost_entries=ProjectCostEntryService(
                session=uow._session, entry_repo=uow.cost_entries,
                project_repo=uow.projects, financial_profile_repo=uow.profiles,
                cost_code_repo=uow.cost_codes, task_repo=uow.tasks,
                resource_repo=uow.resources,
                financial_period_service=period_service,
                clock=SystemClock(), user_session=user_session,
                enterprise_audit_service=uow._enterprise_audit_service,
                tenant_context_service=scope, record_event=uow.record_event,
            ),
        )

    return FinanceGovernanceCommandBoundary(
        uow_factory=factory, operations_factory=operations
    )


def _seed_rate_race_line(environment, *, resource_id: str, line_id: str, code: str):
    now = datetime(2026, 9, 10, 9, 0, tzinfo=timezone.utc)
    with environment.admin_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users (id, username, password_hash, account_type, is_active, "
            "created_at, updated_at, version) VALUES "
            "('r6df-rate-editor', 'r6df-rate-editor', 'not-login-capable', "
            "'human', true, :now, :now, 1) ON CONFLICT (id) DO NOTHING"
        ), {"now": now})
        connection.execute(text(
            "INSERT INTO resources "
            "(id, tenant_id, organization_id, resource_code, name, kind, role, "
            "hourly_rate, is_active, capacity_percent, cost_type, worker_type, version) "
            "VALUES (:id, :tenant, :org, :code, 'Rate race resource', 'PERSON', "
            "'Engineer', 999, true, 100, 'LABOR', 'EXTERNAL', 1)"
        ), {"id": resource_id, "tenant": TENANT_A, "org": ORG_A, "code": code})
        connection.execute(text(
            "INSERT INTO project_finance_rate_card_lines "
            "(id, tenant_id, organization_id, rate_card_id, rate_type, origin, "
            "resource_id, is_active, unit, rate_amount, rate_currency, version, "
            "created_at, updated_at) VALUES "
            "(:id, :tenant, :org, :card, 'cost', 'configured', :resource, true, "
            "'HOUR', 42.12500000, 'USD', 1, :now, :now)"
        ), {"id": line_id, "tenant": TENANT_A, "org": ORG_A,
            "card": RATE_CARD_A, "resource": resource_id, "now": now})


def test_runtime_worker_posts_under_rls_and_denies_hostile_scope_changes(
    postgres_test_environment,
):
    source_session, outbox, dispatcher = _build_dispatcher(postgres_test_environment)
    try:
        validate_postgresql_execution_role(source_session)
        outbox.enqueue(_approved_time_envelope())
        source_session.commit()
        assert dispatcher.dispatch_pending(limit=1) == 1
    finally:
        source_session.close()

    with postgres_test_environment.admin_engine.connect() as connection:
        labor = connection.execute(
            text(
                "SELECT id, actual_cost_entry_id, rate_base_amount, rate_amount, "
                "rate_currency, worker_service_principal_id, source_event_id, "
                "rate_provenance_complete FROM project_approved_time_labor_postings "
                "WHERE time_entry_id='r6dd-time-entry-a'"
            )
        ).one()
        assert labor.rate_base_amount == Decimal("42.12500000")
        assert labor.rate_amount == Decimal("42.12500000")
        assert labor.rate_currency == "USD"
        assert labor.worker_service_principal_id == SERVICE_PRINCIPAL_A
        assert labor.source_event_id == "r6dd-approved-time-event-a"
        assert labor.rate_provenance_complete is True
        assert connection.scalar(
            text(
                "SELECT amount FROM project_cost_entries "
                "WHERE id=:entry"
            ),
            {"entry": labor.actual_cost_entry_id},
        ) == Decimal("100.0500")
        assert connection.scalar(
            text(
                "SELECT count(*) FROM project_finance_inbox_receipts "
                "WHERE event_id='r6dd-approved-time-event-a' AND status='processed'"
            )
        ) == 1
        owner = connection.scalar(
            text(
                "SELECT tableowner FROM pg_tables WHERE schemaname='public' "
                "AND tablename='project_approved_time_labor_postings'"
            )
        )
        assert owner != "app_runtime"

    foreign = postgres_test_environment.runtime_session(
        tenant_id=TENANT_B,
        organization_id=ORG_B,
    )
    try:
        assert foreign.scalar(
            text("SELECT count(*) FROM project_approved_time_labor_postings")
        ) == 0
        assert foreign.scalar(
            text("SELECT count(*) FROM project_finance_inbox_receipts")
        ) == 0
        assert foreign.scalar(text("SELECT count(*) FROM project_cost_entries")) == 0
        with pytest.raises(DBAPIError):
            foreign.execute(
                text(
                    "INSERT INTO project_approved_time_labor_postings "
                    "(id, tenant_id, organization_id, project_id, time_entry_id, "
                    "source_revision, source_content_hash, approved_snapshot_id, "
                    "timesheet_period_id, actual_cost_entry_id, hours, work_date, "
                    "rate_amount, rate_currency, rate_card_id, rate_line_id, "
                    "rate_card_version, rate_line_version, rate_base_amount, rate_origin, "
                    "rate_provenance_complete, rate_precedence_level, rate_effective_date, "
                    "rate_resolved_at, approved_at, resource_id, task_id, "
                    "worker_service_principal_id, source_event_id, created_at) VALUES "
                    "('r6dd-hostile-labor', :tenant, :org, :project, 'hostile-time', 1, "
                    ":hash, 'hostile-snapshot', 'hostile-period', :actual, 1, :day, "
                    "42.125, 'USD', :card, :line, 1, 1, 42.125, 'configured', true, 1, "
                    ":day, :now, :now, :resource, :task, :principal, 'hostile-event', :now)"
                ),
                {
                    "tenant": TENANT_A,
                    "org": ORG_A,
                    "project": PROJECT_A,
                    "hash": "a" * 64,
                    "actual": labor.actual_cost_entry_id,
                    "day": date(2026, 9, 10),
                    "now": datetime.now(timezone.utc),
                    "card": RATE_CARD_A,
                    "line": RATE_LINE_A,
                    "resource": RESOURCE_A,
                    "task": TASK_A,
                    "principal": SERVICE_PRINCIPAL_A,
                },
            )
        foreign.rollback()
    finally:
        foreign.close()


def test_two_runtime_workers_claim_one_event_and_create_one_financial_effect(
    postgres_test_environment,
):
    source_a, outbox, dispatcher_a = _build_dispatcher(postgres_test_environment)
    source_b, _, dispatcher_b = _build_dispatcher(postgres_test_environment)
    envelope = _approved_time_envelope("claim-race")
    try:
        outbox.enqueue(envelope)
        source_a.commit()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda dispatcher: dispatcher.dispatch_pending(limit=1),
                    (dispatcher_a, dispatcher_b),
                )
            )
        assert sum(results) == 1
    finally:
        source_a.close()
        source_b.close()

    with postgres_test_environment.admin_engine.connect() as connection:
        assert connection.scalar(
            text(
                "SELECT count(*) FROM project_approved_time_labor_postings "
                "WHERE time_entry_id=:time_entry_id"
            ),
            {"time_entry_id": envelope.aggregate_id},
        ) == 1
        assert connection.scalar(
            text(
                "SELECT count(*) FROM project_finance_inbox_receipts "
                "WHERE event_id=:event_id AND status='processed'"
            ),
            {"event_id": envelope.event_id},
        ) == 1
        assert connection.scalar(
            text(
                "SELECT count(*) FROM project_cost_entries "
                "WHERE source_module='platform_time' AND source_id=:source_id "
                "AND status='posted'"
            ),
            {"source_id": envelope.aggregate_id},
        ) == 1


def test_labor_and_inbox_rls_are_forced_for_runtime_role(postgres_test_environment):
    with postgres_test_environment.admin_engine.connect() as connection:
        policies = connection.execute(
            text(
                "SELECT c.relname AS tablename, c.relrowsecurity AS rowsecurity, "
                "c.relforcerowsecurity AS forcerowsecurity FROM pg_class c "
                "JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relname IN "
                "('project_approved_time_labor_postings', "
                "'project_finance_inbox_receipts', 'project_cost_entries')"
            )
        ).all()
        assert len(policies) == 3
        assert all(row.rowsecurity and row.forcerowsecurity for row in policies)
        role = connection.execute(
            text(
                "SELECT rolsuper, rolbypassrls FROM pg_roles "
                "WHERE rolname='app_runtime'"
            )
        ).one()
        assert role.rolsuper is False
        assert role.rolbypassrls is False


def test_governed_rate_edit_races_labor_post_without_mixed_provenance(
    postgres_test_environment, monkeypatch
):
    _seed_rate_race_line(
        postgres_test_environment, resource_id=RESOURCE_RACE,
        line_id=RATE_LINE_RACE, code="R6DF-RACE",
    )

    source, outbox, dispatcher = _build_dispatcher(postgres_test_environment)
    boundary = _governed_rate_boundary(postgres_test_environment)
    envelope = _approved_time_envelope("rate-race", resource_id=RESOURCE_RACE)
    outbox.enqueue(envelope)
    source.commit()
    resolved = Event()
    edited = Event()
    original_lock = SqlAlchemyRateResolutionReader.lock_line_for_posting

    def pause_before_lock(reader, **kwargs):
        resolved.set()
        assert edited.wait(timeout=10), "governed Rate edit did not finish"
        return original_lock(reader, **kwargs)

    monkeypatch.setattr(
        SqlAlchemyRateResolutionReader, "lock_line_for_posting", pause_before_lock
    )
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            worker = pool.submit(dispatcher.dispatch_pending, limit=1)
            assert resolved.wait(timeout=10), "worker did not reach Rate resolution"
            try:
                changed = boundary.rate_card(lambda service: service.update_line(
                    RATE_LINE_RACE, expected_version=1, rate_amount=Decimal("52.125")
                ))
                assert changed.version == 2
            finally:
                edited.set()
            assert worker.result(timeout=15) == 1

        session = postgres_test_environment.runtime_session(
            tenant_id=TENANT_A, organization_id=ORG_A
        )
        try:
            posting = session.scalar(select(ApprovedTimeLaborPostingORM).where(
                ApprovedTimeLaborPostingORM.source_event_id == envelope.event_id
            ))
            assert posting is not None
            actual = session.get(ProjectCostEntryORM, posting.actual_cost_entry_id)
            assert actual is not None
            assert posting.rate_card_id == RATE_CARD_A
            assert posting.rate_card_version == 1
            assert posting.rate_line_id == RATE_LINE_RACE
            assert posting.rate_line_version == 2
            assert posting.rate_amount == Decimal("52.125000")
            assert posting.rate_base_amount == Decimal("52.125000")
            assert posting.rate_currency == "USD"
            assert posting.rate_origin == "configured"
            assert posting.rate_provenance_complete is True
            assert posting.rate_resolved_at is not None
            assert actual.amount == Decimal("123.80")
            original_evidence = (
                posting.rate_card_id, posting.rate_card_version,
                posting.rate_line_id, posting.rate_line_version,
                posting.rate_amount, posting.rate_base_amount,
                posting.rate_currency, posting.rate_origin,
                posting.rate_provenance_complete, posting.rate_resolved_at,
                actual.amount,
            )
        finally:
            session.close()

        with pytest.raises(BusinessRuleError):
            boundary.rate_card(lambda service: service.update_line(
                RATE_LINE_RACE, expected_version=2, rate_amount=Decimal("60")
            ))
        boundary.rate_card(lambda service: service.update_line(
            RATE_LINE_RACE, expected_version=2, effective_to=max(date.today(), date(2026, 9, 20))
        ))
        with postgres_test_environment.admin_engine.connect() as connection:
            persisted = connection.execute(text(
                "SELECT p.rate_card_id, p.rate_card_version, p.rate_line_id, "
                "p.rate_line_version, p.rate_amount, p.rate_base_amount, "
                "p.rate_currency, p.rate_origin, p.rate_provenance_complete, "
                "p.rate_resolved_at, c.amount "
                "FROM project_approved_time_labor_postings p "
                "JOIN project_cost_entries c ON c.id = p.actual_cost_entry_id "
                "WHERE p.source_event_id = :event_id"
            ), {"event_id": envelope.event_id}).one()
        assert tuple(persisted) == original_evidence
    finally:
        source.close()


def test_worker_share_lock_blocks_governed_economic_edit_until_posted(
    postgres_test_environment, monkeypatch
):
    resource_id = "r6df-resource-worker-first"
    line_id = "r6df-rate-line-worker-first"
    _seed_rate_race_line(
        postgres_test_environment, resource_id=resource_id,
        line_id=line_id, code="R6DF-WORKER-FIRST",
    )
    source, outbox, dispatcher = _build_dispatcher(postgres_test_environment)
    boundary = _governed_rate_boundary(postgres_test_environment)
    envelope = _approved_time_envelope("worker-first", resource_id=resource_id)
    outbox.enqueue(envelope)
    source.commit()
    locked = Event()
    release = Event()
    editing = Event()
    original_lock = SqlAlchemyRateResolutionReader.lock_line_for_posting

    def pause_with_share_lock(reader, **kwargs):
        line = original_lock(reader, **kwargs)
        locked.set()
        assert release.wait(timeout=10), "posting was not released"
        return line

    monkeypatch.setattr(
        SqlAlchemyRateResolutionReader, "lock_line_for_posting", pause_with_share_lock
    )

    def governed_edit():
        editing.set()
        return boundary.rate_card(lambda service: service.update_line(
            line_id, expected_version=1, rate_amount=Decimal("60")
        ))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            posting = pool.submit(dispatcher.dispatch_pending, limit=1)
            assert locked.wait(timeout=10), "worker did not acquire the Rate share lock"
            mutation = pool.submit(governed_edit)
            assert editing.wait(timeout=10)
            try:
                deadline = monotonic() + 5
                blocked = False
                while monotonic() < deadline:
                    with postgres_test_environment.admin_engine.connect() as connection:
                        blocked = bool(connection.scalar(text(
                            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                            "WHERE wait_event_type='Lock' "
                            "AND query ILIKE '%project_finance_rate_card_lines%')"
                        )))
                    if blocked:
                        break
                    sleep(0.05)
                assert blocked, "governed edit never waited on the worker's Rate lock"
            finally:
                release.set()
            assert posting.result(timeout=15) == 1
            with pytest.raises(BusinessRuleError, match="historical financial use"):
                mutation.result(timeout=15)

        with postgres_test_environment.admin_engine.connect() as connection:
            row = connection.execute(text(
                "SELECT p.rate_amount, p.rate_line_version, c.amount, l.rate_amount "
                "FROM project_approved_time_labor_postings p "
                "JOIN project_cost_entries c ON c.id=p.actual_cost_entry_id "
                "JOIN project_finance_rate_card_lines l ON l.id=p.rate_line_id "
                "WHERE p.source_event_id=:event_id"
            ), {"event_id": envelope.event_id}).one()
            assert row.rate_amount == Decimal("42.125000")
            assert row.rate_line_version == 1
            assert row.amount == Decimal("100.05")
            assert row[3] == Decimal("42.125000")
    finally:
        release.set()
        source.close()


def test_actual_and_posting_failure_read_plans_under_runtime_scope(
    postgres_test_environment,
):
    source, outbox, dispatcher = _build_dispatcher(postgres_test_environment)
    envelope = _approved_time_envelope("read-plan")
    try:
        outbox.enqueue(envelope)
        source.commit()
        assert dispatcher.dispatch_pending(limit=1) == 1
    finally:
        source.close()
    with postgres_test_environment.admin_engine.begin() as connection:
        actual_id = connection.scalar(text(
            "SELECT actual_cost_entry_id FROM project_approved_time_labor_postings "
            "WHERE source_event_id=:event_id"
        ), {"event_id": envelope.event_id})
        inbox_id = connection.scalar(text(
            "SELECT id FROM project_finance_inbox_receipts "
            "WHERE event_id=:event_id"
        ), {"event_id": envelope.event_id})
        assert actual_id and inbox_id
        identity = connection.execute(text(
            "SELECT tenant_id, organization_id, project_id, source_module, "
            "source_type, source_id, source_line_id, source_revision, "
            "source_content_hash, posting_purpose FROM project_cost_entries "
            "WHERE id=:id"
        ), {"id": actual_id}).mappings().one()
        reference = FinancialSourceReference(
            tenant_id=identity["tenant_id"],
            organization_id=identity["organization_id"],
            project_id=identity["project_id"],
            source_module=identity["source_module"],
            source_type=identity["source_type"],
            source_id=identity["source_id"],
            source_line_id=identity["source_line_id"],
            source_revision=identity["source_revision"],
            content_hash=identity["source_content_hash"],
            posting_purpose=identity["posting_purpose"],
        )
        connection.execute(text(
            "INSERT INTO project_cost_entries "
            "SELECT (jsonb_populate_record(NULL::project_cost_entries, to_jsonb(c) || "
            "jsonb_build_object('id', CAST(:id AS text), "
            "'source_id', CAST(:source_id AS text), "
            "'idempotency_key', CAST(:idempotency_key AS text), 'status', 'draft', "
            "'base_amount', NULL, 'base_currency_code', NULL, "
            "'exchange_rate', NULL, 'exchange_rate_date', NULL, "
            "'exchange_rate_source', NULL, 'exchange_rate_captured_at', NULL, "
            "'posting_date', NULL, 'financial_period_id', NULL, "
            "'posted_by', NULL, 'posted_at', NULL))).* "
            "FROM project_cost_entries c "
            "WHERE c.id=:base_id"
        ), [
            {"id": f"r6df-actual-plan-{n}",
             "source_id": f"r6df-actual-source-{n}",
             "idempotency_key": reference.model_copy(update={
                 "source_id": f"r6df-actual-source-{n}"
             }).idempotency_key,
             "base_id": actual_id}
            for n in range(1, 1001)
        ])
        connection.execute(text(
            "INSERT INTO project_finance_inbox_receipts "
            "SELECT (jsonb_populate_record(NULL::project_finance_inbox_receipts, "
            "to_jsonb(i) || jsonb_build_object('id', 'r6df-failure-plan-' || n, "
            "'event_id', 'r6df-failure-event-' || n, "
            "'deduplication_key', 'r6df-failure-dedupe-' || n, "
            "'status', 'retry', 'last_error_code', 'RATE_NOT_FOUND'))).* "
            "FROM project_finance_inbox_receipts i "
            "CROSS JOIN generate_series(1, 1000) n WHERE i.id=:source_id"
        ), {"source_id": inbox_id})
        connection.execute(text("ANALYZE project_cost_entries"))
        connection.execute(text("ANALYZE project_finance_inbox_receipts"))

    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    queries = []

    def capture(_connection, _cursor, statement, parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT") and (
            "project_cost_entries" in statement
            or "project_finance_inbox_receipts" in statement
        ):
            queries.append((statement, parameters))

    try:
        validate_postgresql_execution_role(session)
        actual_reader = SqlAlchemyProjectCostEntryRepository(session)
        actual_reader._tenant_context_service = _TenantContext()
        failure_reader = SqlAlchemyFinanceIntegrationReader(session=session)
        event.listen(postgres_test_environment.runtime_engine, "before_cursor_execute", capture)
        try:
            actuals, actual_total = actual_reader.list_for_project(
                PROJECT_A, status=ProjectCostEntryStatus.DRAFT,
                source_module=FinancialSourceModule.PLATFORM_TIME,
                offset=0, limit=25,
            )
            actual_queries = list(queries)
            queries.clear()
            failures = failure_reader.list_approved_time_failures(
                tenant_id=TENANT_A, organization_id=ORG_A, project_id=PROJECT_A,
                request=ApprovedTimePostingFailureQuery(
                    page=1, page_size=25, status="retry", sort_key="updated",
                    sort_direction="desc",
                ),
            )
            failure_queries = list(queries)
        finally:
            event.remove(postgres_test_environment.runtime_engine, "before_cursor_execute", capture)
        assert actual_total >= 1000 and len(actuals) == 25
        assert failures.total >= 1000 and len(failures.items) == 25
        assert len(actual_queries) == 2
        assert len(failure_queries) == 2
        for label, captured in (("Actual", actual_queries), ("Posting Failures", failure_queries)):
            statement, parameters = captured[1]
            assert "tenant_id" in statement and "organization_id" in statement
            assert "LIMIT" in statement.upper() and "ORDER BY" in statement.upper()
            if label == "Actual":
                assert "source_module" in statement and "status" in statement
            else:
                assert "event_type" in statement and "status" in statement
            plan = "\n".join(session.connection().exec_driver_sql(
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) " + statement, parameters
            ).scalars())
            assert "Execution Time" in plan and "Buffers:" in plan
            print(f"R6D-F {label} page plan:\n{plan}")
    finally:
        session.close()
        with postgres_test_environment.admin_engine.begin() as connection:
            connection.execute(text(
                "DELETE FROM project_finance_inbox_receipts WHERE id LIKE 'r6df-failure-plan-%'"
            ))
            connection.execute(text(
                "DELETE FROM project_cost_entries WHERE id LIKE 'r6df-actual-plan-%'"
            ))


def test_approved_time_rate_candidate_lookup_plan_under_runtime_scope(
    postgres_test_environment,
):
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    candidates = []

    def capture(_connection, _cursor, statement, parameters, _context, _many):
        if "project_finance_rate_card_lines" in statement and "JOIN" in statement:
            candidates.append((statement, parameters))

    try:
        validate_postgresql_execution_role(session)
        reader = SqlAlchemyRateResolutionReader(session=session)
        event.listen(postgres_test_environment.runtime_engine, "before_cursor_execute", capture)
        try:
            result = reader.list_candidates(
                tenant_id=TENANT_A, organization_id=ORG_A,
                project_id=PROJECT_A, rate_type=RateType.COST,
                unit="HOUR", as_of=date(2026, 9, 10),
            )
        finally:
            event.remove(postgres_test_environment.runtime_engine, "before_cursor_execute", capture)
        assert result and len(candidates) == 1
        statement, parameters = candidates[0]
        assert "tenant_id" in statement and "organization_id" in statement
        assert "effective_from" in statement and "effective_to" in statement
        plan = "\n".join(session.connection().exec_driver_sql(
            "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) " + statement, parameters
        ).scalars())
        assert "Execution Time" in plan and "Buffers:" in plan
        print(f"R6D-F approved-Time Rate candidate plan:\n{plan}")
    finally:
        session.close()
