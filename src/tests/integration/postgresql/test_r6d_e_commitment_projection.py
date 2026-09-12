from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.commitments.commitment_service import (
    ProjectCommitmentService,
)
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import (
    ProjectCostEntryService,
)
from src.core.modules.project_management.application.financials.procurement_consumer import (
    PROCUREMENT_FINANCE_PRINCIPAL_NAME,
    ProcurementFinancialConsumer,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
)
from src.core.platform.application.finance.financial_period_service import FinancialPeriodService
from src.core.platform.application.integration import IntegrationOutboxService
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.security.identity.service_principal import ServicePrincipal
from src.core.platform.finance import DecimalQuantityPayload, MonetaryRatePayload
from src.core.platform.infrastructure.persistence.repositories.integration.procurement_financial_outbox import (
    SqlAlchemyProcurementFinancialOutboxRepository,
)
from src.core.platform.integration import (
    PROCUREMENT_COMMITMENT_EVENT_TYPE,
    PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE,
    IntegrationEventEnvelope,
    ProcurementCommitmentEventPayload,
    ProcurementReceiptAccrualEventPayload,
)
from src.infra.events.in_process_post_commit_event_bus import InProcessPostCommitEventBus
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.integration.procurement_financial_dispatcher import ProcurementFinancialDispatcher
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role


pytestmark = pytest.mark.postgresql_integration

TENANT_A, TENANT_B = "r6de-tenant-a", "r6de-tenant-b"
ORG_A, ORG_B = "r6de-org-a", "r6de-org-b"
PROJECT_A, PROJECT_B = "r6de-project-a", "r6de-project-b"
SITE_A, SUPPLIER_A = "r6de-site-a", "r6de-supplier-a"
COST_CODE_A, PERIOD_A = "r6de-cost-a", "r6de-period-a"
SERVICE_USER_A, SERVICE_PRINCIPAL_A = "r6de-service-user-a", "r6de-service-principal-a"


class _TenantContext:
    def require_active_scope_ids(self, *, operation_label):
        return ActiveScopeIds(TENANT_A, ORG_A)

    def require_organization_context(self, *, operation_label):
        return SimpleNamespace(
            tenant_id=TENANT_A,
            organization_id=ORG_A,
            tenant=SimpleNamespace(id=TENANT_A),
            organization=SimpleNamespace(id=ORG_A, base_currency="USD"),
        )

    def get_active_tenant_id(self):
        return TENANT_A

    def get_active_organization_id(self):
        return ORG_A

    def require_active_organization_id(self, *, operation_label):
        return ORG_A


@pytest.fixture(scope="module", autouse=True)
def seeded_procurement_scope(postgres_test_environment):
    now = datetime(2026, 9, 10, tzinfo=timezone.utc)
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant, org, project, suffix in (
            (TENANT_A, ORG_A, PROJECT_A, "A"),
            (TENANT_B, ORG_B, PROJECT_B, "B"),
        ):
            connection.execute(text(
                "INSERT INTO tenants (id, tenant_code, display_name, tenant_status, is_active, version) "
                "VALUES (:id, :code, :code, 'active', true, 1)"
            ), {"id": tenant, "code": f"R6DE-{suffix}"})
            connection.execute(text(
                "INSERT INTO organizations (id, tenant_id, organization_code, display_name, "
                "timezone_name, base_currency, is_enabled, version) "
                "VALUES (:id, :tenant, :code, :code, 'UTC', 'USD', true, 1)"
            ), {"id": org, "tenant": tenant, "code": f"R6DE-ORG-{suffix}"})
            connection.execute(text(
                "INSERT INTO projects (id, tenant_id, project_code, name, description, status, "
                "organization_id, version) VALUES (:id, :tenant, :code, :code, '', 'ACTIVE', :org, 1)"
            ), {"id": project, "tenant": tenant, "org": org, "code": f"R6DE-P-{suffix}"})
        connection.execute(text(
            "INSERT INTO project_finance_cost_codes (id, tenant_id, organization_id, code, "
            "name, is_active, version, created_at, updated_at) "
            "VALUES (:id, :tenant, :org, 'PROC', 'Procurement', true, 1, :now, :now)"
        ), {"id": COST_CODE_A, "tenant": TENANT_A, "org": ORG_A, "now": now})
        connection.execute(text(
            "INSERT INTO project_finance_profiles (id, tenant_id, organization_id, project_id, "
            "currency_code, status, default_cost_code_id, version, created_at, updated_at) "
            "VALUES ('r6de-profile-a', :tenant, :org, :project, 'USD', 'active', :cost, 1, :now, :now)"
        ), {"tenant": TENANT_A, "org": ORG_A, "project": PROJECT_A, "cost": COST_CODE_A, "now": now})
        connection.execute(text(
            "INSERT INTO sites (id, tenant_id, organization_id, site_code, name, currency_code, "
            "is_active, created_at, updated_at, version) "
            "VALUES (:id, :tenant, :org, 'PROC', 'Procurement site', 'USD', true, :now, :now, 1)"
        ), {"id": SITE_A, "tenant": TENANT_A, "org": ORG_A, "now": now})
        connection.execute(text(
            "INSERT INTO parties (id, tenant_id, organization_id, party_code, party_name, "
            "party_type, is_active, created_at, updated_at, version) "
            "VALUES (:id, :tenant, :org, 'PROC', 'Procurement supplier', 'SUPPLIER', true, :now, :now, 1)"
        ), {"id": SUPPLIER_A, "tenant": TENANT_A, "org": ORG_A, "now": now})
        connection.execute(text(
            "INSERT INTO financial_periods (id, tenant_id, organization_id, code, name, fiscal_year, "
            "period_number, start_date, end_date, status, version, created_by, created_at, "
            "updated_by, updated_at) VALUES (:id, :tenant, :org, 'R6DE-P09', 'September 2026', "
            "2026, 9, :start, :end, 'open', 1, 'seed', :now, 'seed', :now)"
        ), {"id": PERIOD_A, "tenant": TENANT_A, "org": ORG_A,
            "start": date(2026, 9, 1), "end": date(2026, 9, 30), "now": now})
        connection.execute(text(
            "INSERT INTO users (id, username, password_hash, account_type, is_active, created_at, "
            "updated_at, version) VALUES (:id, 'r6de-procurement-worker', 'not-login-capable', "
            "'service', true, :now, :now, 1)"
        ), {"id": SERVICE_USER_A, "now": now})
        connection.execute(text(
            "INSERT INTO service_principals (id, tenant_id, organization_id, user_id, name, "
            "description, status, created_at, updated_at) VALUES "
            "(:id, :tenant, :org, :user, :name, 'Procurement worker', 'active', :now, :now)"
        ), {"id": SERVICE_PRINCIPAL_A, "tenant": TENANT_A, "org": ORG_A,
            "user": SERVICE_USER_A, "name": PROCUREMENT_FINANCE_PRINCIPAL_NAME, "now": now})


def _dispatcher(environment):
    tenant_context = _TenantContext()
    user_session = UserSessionContext()
    user_session.set_active_tenant_id(TENANT_A)
    user_session.set_active_organization_id(ORG_A)
    source_session = environment.runtime_session(tenant_id=TENANT_A, organization_id=ORG_A)
    outbox_repo = SqlAlchemyProcurementFinancialOutboxRepository(source_session)
    outbox_repo._tenant_context_service = tenant_context
    outbox = IntegrationOutboxService(
        repository=outbox_repo, owner_module="inventory_procurement", clock=SystemClock()
    )
    principal = ServicePrincipal(
        id=SERVICE_PRINCIPAL_A, tenant_id=TENANT_A, organization_id=ORG_A,
        user_id=SERVICE_USER_A, name=PROCUREMENT_FINANCE_PRINCIPAL_NAME,
    )
    uow_factory = SqlAlchemyFinanceGovernanceUnitOfWorkFactory(
        session_factory=sessionmaker(bind=environment.runtime_engine, expire_on_commit=False),
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=InProcessPostCommitEventBus(),
        tenant_context_service=tenant_context,
        user_session=user_session,
    )

    def consumer_factory(uow, service_principal):
        cost_service = ProjectCostEntryService(
            session=uow._session, entry_repo=uow.cost_entries, project_repo=uow.projects,
            financial_profile_repo=uow.profiles, cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks, resource_repo=uow.resources,
            financial_period_service=FinancialPeriodService(
                session=uow._session, period_repo=uow.financial_periods,
                tenant_context_service=tenant_context, user_session=user_session,
                enterprise_audit_service=uow._enterprise_audit_service,
            ),
            clock=SystemClock(), user_session=user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            tenant_context_service=tenant_context,
        )
        commitment_service = ProjectCommitmentService(
            session=uow._session, commitment_repo=uow.commitments,
            cost_entry_repo=uow.cost_entries, project_repo=uow.projects,
            financial_profile_repo=uow.profiles, cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks, party_repo=uow.parties, site_repo=uow.sites,
            clock=SystemClock(), user_session=user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            tenant_context_service=tenant_context,
        )
        return ProcurementFinancialConsumer(
            commitment_service=commitment_service, cost_entry_service=cost_service,
            task_repo=uow.tasks, service_principal=service_principal,
        )

    return source_session, outbox, ProcurementFinancialDispatcher(
        session=source_session, outbox_service=outbox, uow_factory=uow_factory,
        consumer_factory=consumer_factory, principal_resolver=lambda: principal,
    )


def _event(event_type, payload, *, event_id, aggregate_id, revision=1):
    return IntegrationEventEnvelope(
        event_id=event_id, event_type=event_type, schema_version=1,
        tenant_id=TENANT_A, organization_id=ORG_A,
        aggregate_type="purchase_order_line" if event_type == PROCUREMENT_COMMITMENT_EVENT_TYPE else "receipt_line",
        aggregate_id=aggregate_id, aggregate_version=revision,
        occurred_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
        correlation_id="r6de-correlation", payload=payload.model_dump(mode="json"),
    )


def test_runtime_worker_and_child_rls(postgres_test_environment):
    source_session, outbox, dispatcher = _dispatcher(postgres_test_environment)
    try:
        validate_postgresql_execution_role(source_session)
        commitment = ProcurementCommitmentEventPayload(
            project_id=PROJECT_A, purchase_order_id="r6de-po", purchase_order_line_id="r6de-line",
            purchase_order_number="R6DE-PO", supplier_party_id=SUPPLIER_A, site_id=SITE_A,
            state="SENT", source_revision=1, source_content_hash="a" * 64,
            ordered_quantity=DecimalQuantityPayload(value="10", unit="EA"),
            unit_price=MonetaryRatePayload(amount="10", currency="USD", per_unit="EA"),
            order_date=date(2026, 9, 10),
        )
        outbox.enqueue(_event(
            PROCUREMENT_COMMITMENT_EVENT_TYPE, commitment,
            event_id="r6de-commit-event", aggregate_id="r6de-line",
        ))
        source_session.commit()
        assert dispatcher.dispatch_pending(limit=1) == 1
        receipt = ProcurementReceiptAccrualEventPayload(
            project_id=PROJECT_A, receipt_id="r6de-receipt", receipt_line_id="r6de-receipt-line",
            receipt_number="R6DE-REC", purchase_order_id="r6de-po",
            purchase_order_line_id="r6de-line", supplier_party_id=SUPPLIER_A,
            site_id=SITE_A, source_revision=1, source_content_hash="b" * 64,
            posted_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
            accepted_quantity=DecimalQuantityPayload(value="4", unit="EA"),
            unit_cost=MonetaryRatePayload(amount="10", currency="USD", per_unit="EA"),
        )
        outbox.enqueue(_event(
            PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE, receipt,
            event_id="r6de-receipt-event", aggregate_id="r6de-receipt-line",
        ))
        source_session.commit()
        assert dispatcher.dispatch_pending(limit=1) == 1
    finally:
        source_session.close()

    with postgres_test_environment.admin_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT matched_amount FROM project_commitment_lines "
            "WHERE purchase_order_line_id='r6de-line'"
        )) == 40
        assert connection.scalar(text(
            "SELECT count(*) FROM project_cost_entries WHERE project_id=:project"
        ), {"project": PROJECT_A}) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM project_commitment_matches WHERE project_id=:project"
        ), {"project": PROJECT_A}) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM project_finance_inbox_receipts "
            "WHERE event_id IN ('r6de-commit-event', 'r6de-receipt-event') AND status='processed'"
        )) == 2
        for table in (
            "project_commitments", "project_commitment_lines",
            "project_commitment_source_revisions", "project_commitment_matches",
            "project_cost_entries", "project_finance_inbox_receipts",
        ):
            row = connection.execute(text(
                "SELECT pg_get_userbyid(c.relowner) AS tableowner, c.relrowsecurity, "
                "c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relname=:table"
            ), {"table": table}).one()
            assert row.tableowner != "app_runtime"
            assert row.relrowsecurity and row.relforcerowsecurity

    foreign = postgres_test_environment.runtime_session(tenant_id=TENANT_B, organization_id=ORG_B)
    try:
        validate_postgresql_execution_role(foreign)
        for table in (
            "project_commitments", "project_commitment_lines",
            "project_commitment_source_revisions", "project_commitment_matches",
            "project_cost_entries", "project_finance_inbox_receipts",
        ):
            assert foreign.scalar(text(f"SELECT count(*) FROM {table}")) == 0
            assert foreign.execute(text(f"DELETE FROM {table} WHERE tenant_id=:local"),
                                   {"local": TENANT_A}).rowcount == 0
        foreign.rollback()
    finally:
        foreign.close()

    local = postgres_test_environment.runtime_session(tenant_id=TENANT_A, organization_id=ORG_A)
    try:
        for table in (
            "project_commitments", "project_commitment_lines",
            "project_commitment_source_revisions", "project_commitment_matches",
            "project_cost_entries", "project_finance_inbox_receipts",
        ):
            with pytest.raises(DBAPIError):
                local.execute(text(f"UPDATE {table} SET tenant_id=:foreign WHERE tenant_id=:local"),
                              {"foreign": TENANT_B, "local": TENANT_A})
            local.rollback()
            with pytest.raises(DBAPIError) as denied:
                local.execute(text(
                    f"INSERT INTO {table} SELECT (jsonb_populate_record(NULL::{table}, "
                    "to_jsonb(source) || jsonb_build_object(" 
                    "'id', CAST(:new_id AS text), 'tenant_id', CAST(:foreign AS text), "
                    "'organization_id', CAST(:foreign_org AS text)))).* "
                    f"FROM {table} AS source LIMIT 1"
                ), {"new_id": f"r6de-forged-{table}", "foreign": TENANT_B, "foreign_org": ORG_B})
            assert denied.value.orig.sqlstate == "42501"
            local.rollback()
    finally:
        local.close()


def test_two_runtime_dispatchers_claim_one_source_event(postgres_test_environment):
    source, outbox, first_dispatcher = _dispatcher(postgres_test_environment)
    second_source, _second_outbox, second_dispatcher = _dispatcher(postgres_test_environment)
    try:
        payload = ProcurementCommitmentEventPayload(
            project_id=PROJECT_A, purchase_order_id="r6de-race-po",
            purchase_order_line_id="r6de-race-line", purchase_order_number="R6DE-RACE",
            supplier_party_id=SUPPLIER_A, site_id=SITE_A, state="SENT",
            source_revision=1, source_content_hash="c" * 64,
            ordered_quantity=DecimalQuantityPayload(value="10", unit="EA"),
            unit_price=MonetaryRatePayload(amount="10", currency="USD", per_unit="EA"),
            order_date=date(2026, 9, 10),
        )
        envelope = _event(
            PROCUREMENT_COMMITMENT_EVENT_TYPE, payload,
            event_id="r6de-race-event", aggregate_id="r6de-race-line",
        )
        outbox.enqueue(envelope)
        source.commit()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = tuple(pool.map(
                lambda dispatcher: dispatcher.dispatch_pending(limit=1),
                (first_dispatcher, second_dispatcher),
            ))
        assert sum(results) == 1
        assert first_dispatcher._consume_under_unit_of_work(envelope).value == "duplicate_processed"
    finally:
        source.close()
        second_source.close()

    with postgres_test_environment.admin_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM project_commitment_lines "
            "WHERE purchase_order_line_id='r6de-race-line'"
        )) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM project_commitment_source_revisions r "
            "JOIN project_commitment_lines l ON l.id=r.commitment_line_id "
            "WHERE l.purchase_order_line_id='r6de-race-line'"
        )) == 1


def test_concurrent_out_of_order_line_revisions_keep_newest_truth(postgres_test_environment):
    source, outbox, first_dispatcher = _dispatcher(postgres_test_environment)
    second_source, _second_outbox, second_dispatcher = _dispatcher(postgres_test_environment)
    try:
        for revision, quantity in ((2, "12"), (1, "10")):
            payload = ProcurementCommitmentEventPayload(
                project_id=PROJECT_A, purchase_order_id="r6de-order-po",
                purchase_order_line_id="r6de-order-line", purchase_order_number="R6DE-ORDER",
                supplier_party_id=SUPPLIER_A, site_id=SITE_A, state="SENT",
                source_revision=revision, source_content_hash=f"{revision:064x}",
                ordered_quantity=DecimalQuantityPayload(value=quantity, unit="EA"),
                unit_price=MonetaryRatePayload(amount="10", currency="USD", per_unit="EA"),
                order_date=date(2026, 9, 10),
            )
            outbox.enqueue(_event(
                PROCUREMENT_COMMITMENT_EVENT_TYPE, payload,
                event_id=f"r6de-order-event-{revision}", aggregate_id="r6de-order-line",
                revision=revision,
            ))
        source.commit()
        with ThreadPoolExecutor(max_workers=2) as pool:
            tuple(pool.map(
                lambda dispatcher: dispatcher.dispatch_pending(limit=1),
                (first_dispatcher, second_dispatcher),
            ))
    finally:
        source.close()
        second_source.close()

    with postgres_test_environment.admin_engine.connect() as connection:
        line = connection.execute(text(
            "SELECT source_revision, amount FROM project_commitment_lines "
            "WHERE purchase_order_line_id='r6de-order-line'"
        )).one()
        assert line.source_revision == 2
        assert line.amount == 120


def test_concurrent_duplicate_receipt_has_one_actual_and_match(postgres_test_environment):
    source, outbox, first_dispatcher = _dispatcher(postgres_test_environment)
    second_source, _second_outbox, second_dispatcher = _dispatcher(postgres_test_environment)
    try:
        commitment = ProcurementCommitmentEventPayload(
            project_id=PROJECT_A, purchase_order_id="r6de-receipt-race-po",
            purchase_order_line_id="r6de-receipt-race-line",
            purchase_order_number="R6DE-RECEIPT-RACE", supplier_party_id=SUPPLIER_A,
            site_id=SITE_A, state="SENT", source_revision=1, source_content_hash="d" * 64,
            ordered_quantity=DecimalQuantityPayload(value="10", unit="EA"),
            unit_price=MonetaryRatePayload(amount="10", currency="USD", per_unit="EA"),
            order_date=date(2026, 9, 10),
        )
        outbox.enqueue(_event(
            PROCUREMENT_COMMITMENT_EVENT_TYPE, commitment,
            event_id="r6de-receipt-race-commit", aggregate_id="r6de-receipt-race-line",
        ))
        source.commit()
        assert first_dispatcher.dispatch_pending(limit=1) == 1

        receipt = ProcurementReceiptAccrualEventPayload(
            project_id=PROJECT_A, receipt_id="r6de-receipt-race",
            receipt_line_id="r6de-receipt-race-source-line",
            receipt_number="R6DE-RECEIPT-RACE", purchase_order_id="r6de-receipt-race-po",
            purchase_order_line_id="r6de-receipt-race-line",
            supplier_party_id=SUPPLIER_A, site_id=SITE_A,
            source_revision=1, source_content_hash="e" * 64,
            posted_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
            accepted_quantity=DecimalQuantityPayload(value="4", unit="EA"),
            unit_cost=MonetaryRatePayload(amount="10", currency="USD", per_unit="EA"),
        )
        for event_id in ("r6de-receipt-race-event-a", "r6de-receipt-race-event-b"):
            outbox.enqueue(_event(
                PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE, receipt,
                event_id=event_id, aggregate_id="r6de-receipt-race-source-line",
            ))
        source.commit()
        with ThreadPoolExecutor(max_workers=2) as pool:
            tuple(pool.map(
                lambda dispatcher: dispatcher.dispatch_pending(limit=1),
                (first_dispatcher, second_dispatcher),
            ))
    finally:
        source.close()
        second_source.close()

    with postgres_test_environment.admin_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM project_cost_entries "
            "WHERE source_id='r6de-receipt-race' AND source_line_id='r6de-receipt-race-source-line'"
        )) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM project_commitment_matches m "
            "JOIN project_commitment_lines l ON l.id=m.commitment_line_id "
            "WHERE l.purchase_order_line_id='r6de-receipt-race-line'"
        )) == 1
        assert connection.scalar(text(
            "SELECT matched_amount FROM project_commitment_lines "
            "WHERE purchase_order_line_id='r6de-receipt-race-line'"
        )) == 40


def test_closure_and_accepted_receipt_race_preserves_both_facts(postgres_test_environment):
    source, outbox, first_dispatcher = _dispatcher(postgres_test_environment)
    second_source, _second_outbox, second_dispatcher = _dispatcher(postgres_test_environment)
    try:
        def commitment_payload(revision, state):
            return ProcurementCommitmentEventPayload(
                project_id=PROJECT_A, purchase_order_id="r6de-close-po",
                purchase_order_line_id="r6de-close-line", purchase_order_number="R6DE-CLOSE",
                supplier_party_id=SUPPLIER_A, site_id=SITE_A, state=state,
                source_revision=revision, source_content_hash=f"{revision + 200:064x}",
                ordered_quantity=DecimalQuantityPayload(value="10", unit="EA"),
                unit_price=MonetaryRatePayload(amount="10", currency="USD", per_unit="EA"),
                order_date=date(2026, 9, 10),
            )

        outbox.enqueue(_event(
            PROCUREMENT_COMMITMENT_EVENT_TYPE, commitment_payload(1, "SENT"),
            event_id="r6de-close-initial", aggregate_id="r6de-close-line",
        ))
        source.commit()
        assert first_dispatcher.dispatch_pending(limit=1) == 1

        outbox.enqueue(_event(
            PROCUREMENT_COMMITMENT_EVENT_TYPE, commitment_payload(2, "CLOSED"),
            event_id="r6de-close-terminal", aggregate_id="r6de-close-line", revision=2,
        ))
        receipt = ProcurementReceiptAccrualEventPayload(
            project_id=PROJECT_A, receipt_id="r6de-close-receipt",
            receipt_line_id="r6de-close-receipt-line", receipt_number="R6DE-CLOSE-REC",
            purchase_order_id="r6de-close-po", purchase_order_line_id="r6de-close-line",
            supplier_party_id=SUPPLIER_A, site_id=SITE_A,
            source_revision=1, source_content_hash="f" * 64,
            posted_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
            accepted_quantity=DecimalQuantityPayload(value="4", unit="EA"),
            unit_cost=MonetaryRatePayload(amount="10", currency="USD", per_unit="EA"),
        )
        outbox.enqueue(_event(
            PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE, receipt,
            event_id="r6de-close-receipt-event", aggregate_id="r6de-close-receipt-line",
        ))
        source.commit()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = tuple(pool.map(
                lambda dispatcher: dispatcher.dispatch_pending(limit=1),
                (first_dispatcher, second_dispatcher),
            ))
        assert sum(results) == 2
    finally:
        source.close()
        second_source.close()

    with postgres_test_environment.admin_engine.connect() as connection:
        line = connection.execute(text(
            "SELECT state, source_revision, matched_amount FROM project_commitment_lines "
            "WHERE purchase_order_line_id='r6de-close-line'"
        )).one()
        assert (line.state, line.source_revision, line.matched_amount) == ("closed", 2, 40)
        assert connection.scalar(text(
            "SELECT count(*) FROM project_cost_entries WHERE source_id='r6de-close-receipt'"
        )) == 1
