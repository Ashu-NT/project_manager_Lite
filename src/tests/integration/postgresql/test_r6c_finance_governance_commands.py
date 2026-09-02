from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.budgets.budget_service import (
    BudgetService,
)
from src.core.modules.project_management.application.financials.configuration_service import (
    FinancialConfigurationService,
)
from src.core.modules.project_management.application.financials.financial_changes.service import (
    FinancialChangeService,
)
from src.core.modules.project_management.application.financials.forecasts.generation_service import (
    ForecastGenerationService,
    ManualEtcEstimate,
)
from src.core.modules.project_management.application.financials.forecasts.version_service import (
    ForecastVersionService,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_service import (
    ProjectRateCardService,
)
from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceCommandBoundary,
    FinanceGovernanceOperations,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageRequest,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.sqlalchemy_finance_budget_reader import (
    SqlAlchemyFinanceBudgetReader,
)
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds
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
TENANT_A = "r6c-command-tenant-a"
TENANT_B = "r6c-command-tenant-b"
ORG_A = "r6c-command-org-a"
ORG_A2 = "r6c-command-org-a2"
ORG_B = "r6c-command-org-b"
PROJECT_A = "r6c-command-project-a"


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
        )

    def get_active_tenant_id(self):
        return self.tenant_id

    def get_active_organization_id(self):
        return self.organization_id


class _SchedulePort:
    @staticmethod
    def _validate_approved_schedule_changes(_commands):
        return None


@pytest.fixture(scope="module", autouse=True)
def seeded_r6c_scopes(postgres_test_environment):
    now = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant_id, org_id, suffix in (
            (TENANT_A, ORG_A, "A"),
            (TENANT_B, ORG_B, "B"),
        ):
            connection.execute(
                text(
                    "INSERT INTO tenants "
                    "(id, tenant_code, display_name, tenant_status, is_active, version) "
                    "VALUES (:tenant, :code, :code, 'active', true, 1)"
                ),
                {"tenant": tenant_id, "code": f"R6C-CMD-{suffix}"},
            )
            connection.execute(
                text(
                    "INSERT INTO organizations "
                    "(id, tenant_id, organization_code, display_name, timezone_name, "
                    "base_currency, is_enabled, version) "
                    "VALUES (:org, :tenant, :code, :code, 'UTC', 'USD', true, 1)"
                ),
                {"org": org_id, "tenant": tenant_id, "code": f"R6C-ORG-{suffix}"},
            )
        connection.execute(
            text(
                "INSERT INTO organizations "
                "(id, tenant_id, organization_code, display_name, timezone_name, "
                "base_currency, is_enabled, version) "
                "VALUES (:org, :tenant, 'R6C-ORG-A2', 'R6C Org A2', "
                "'UTC', 'USD', true, 1)"
            ),
            {"org": ORG_A2, "tenant": TENANT_A},
        )
        connection.execute(
            text(
                "INSERT INTO projects "
                "(id, tenant_id, project_code, name, description, status, "
                "organization_id, version) "
                "VALUES (:project, :tenant, 'R6C-P-A', 'R6C Command Project', '', "
                "'ACTIVE', :org, 1)"
            ),
            {"project": PROJECT_A, "tenant": TENANT_A, "org": ORG_A},
        )
        connection.execute(
            text(
                "INSERT INTO project_finance_profiles "
                "(id, tenant_id, organization_id, project_id, currency_code, "
                "version, created_at, updated_at) "
                "VALUES ('r6c-command-profile-a', :tenant, :org, :project, 'USD', "
                "1, :now, :now)"
            ),
            {"tenant": TENANT_A, "org": ORG_A, "project": PROJECT_A, "now": now},
        )


def _user_session() -> UserSessionContext:
    permissions = frozenset(
        {
            "finance.manage",
            "budget.manage",
            "forecast.manage",
            "financial_change.manage",
        }
    )
    session = UserSessionContext()
    session.set_principal(
        UserSessionPrincipal(
            user_id="r6c-runtime-user",
            username="r6c-runtime-user",
            display_name="R6C Runtime User",
            role_names=frozenset(),
            permissions=permissions,
            scoped_access={"project": {PROJECT_A: permissions}},
            active_tenant_id=TENANT_A,
            active_organization_id=ORG_A,
        )
    )
    session.set_active_tenant_id(TENANT_A)
    session.set_active_organization_id(ORG_A)
    return session


def _boundary(postgres_test_environment, *, scope: _TenantContext):
    user_session = _user_session()
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
    clock = SystemClock()

    def operations(uow):
        common = {
            "session": uow._session,
            "clock": clock,
            "user_session": user_session,
            "enterprise_audit_service": uow._enterprise_audit_service,
            "tenant_context_service": scope,
        }
        return FinanceGovernanceOperations(
            budgets=BudgetService(
                budget_repo=uow.budgets,
                project_repo=uow.projects,
                financial_profile_repo=uow.profiles,
                cost_code_repo=uow.cost_codes,
                task_repo=uow.tasks,
                approval_service=None,
                **common,
            ),
            forecast_versions=ForecastVersionService(
                forecast_repo=uow.forecasts,
                project_repo=uow.projects,
                financial_profile_repo=uow.profiles,
                cost_code_repo=uow.cost_codes,
                task_repo=uow.tasks,
                **common,
            ),
            forecast_generation=ForecastGenerationService(
                forecast_repo=uow.forecasts,
                project_repo=uow.projects,
                financial_profile_repo=uow.profiles,
                cost_code_repo=uow.cost_codes,
                task_repo=uow.tasks,
                planned_cost_repo=uow.planned_costs,
                commitment_repo=uow.commitments,
                cost_entry_repo=uow.cost_entries,
                register_repo=uow.register_entries,
                **common,
            ),
            financial_changes=FinancialChangeService(
                change_repo=uow.changes,
                budget_repo=uow.budgets,
                forecast_repo=uow.forecasts,
                project_repo=uow.projects,
                financial_profile_repo=uow.profiles,
                cost_code_repo=uow.cost_codes,
                task_repo=uow.tasks,
                task_service=_SchedulePort(),
                approval_service=None,
                **common,
            ),
            financial_setup=FinancialConfigurationService(
                session=uow._session,
                profile_repo=uow.profiles,
                cost_code_repo=uow.cost_codes,
                project_repo=uow.projects,
                user_session=user_session,
                enterprise_audit_service=uow._enterprise_audit_service,
                tenant_context_service=scope,
            ),
            rate_cards=ProjectRateCardService(
                session=uow._session,
                rate_card_repo=uow.rate_cards,
                project_repo=uow.projects,
                user_session=user_session,
                enterprise_audit_service=uow._enterprise_audit_service,
                tenant_context_service=scope,
                record_event=uow.record_event,
            ),
        )

    return FinanceGovernanceCommandBoundary(
        uow_factory=factory,
        operations_factory=operations,
    )


def test_r6c_commands_use_app_runtime_and_preserve_rls_scope(postgres_test_environment):
    boundary = _boundary(
        postgres_test_environment,
        scope=_TenantContext(TENANT_A, ORG_A),
    )
    setup = boundary.financial_setup(
        lambda service: service.create_cost_code(code="R6C-RUNTIME", name="Runtime"),
    )
    budget = boundary.budget(
        lambda service: service.create_budget(PROJECT_A, "R6C Budget"),
        project_id=PROJECT_A,
    )
    budget_line = boundary.budget(
        lambda service: service.add_line(
            budget.id,
            cost_code_id=setup.id,
            description="R6C runtime line",
            amount=Decimal("125.50"),
            expected_budget_version=budget.row_version,
        )
    )
    forecast_result = boundary.forecast_generation(
        lambda service: service.generate_draft(
            PROJECT_A,
            name="R6C Forecast",
            as_of_date=date(2026, 9, 1),
            generated_by="r6c-runtime-user",
            manual_estimates=(
                ManualEtcEstimate(
                    cost_code_id=setup.id,
                    description="R6C governed manual ETC",
                    amount=Decimal("75.25"),
                ),
            ),
        ),
        project_id=PROJECT_A,
    )
    forecast = forecast_result.forecast
    change = boundary.financial_change(
        lambda service: service.create_change(
            PROJECT_A,
            title="R6C Change",
            reason="Runtime role proof",
            effective_date=date(2026, 9, 1),
            created_by="r6c-runtime-user",
        ),
        project_id=PROJECT_A,
    )

    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A,
        organization_id=ORG_A,
    )
    try:
        validate_postgresql_execution_role(session)
        assert session.scalar(
            text("SELECT count(*) FROM project_finance_cost_codes WHERE id=:id"),
            {"id": setup.id},
        ) == 1
        assert session.scalar(
            text("SELECT count(*) FROM project_finance_budgets WHERE id=:id"),
            {"id": budget.id},
        ) == 1
        assert session.scalar(
            text("SELECT count(*) FROM project_finance_budget_lines WHERE id=:id"),
            {"id": budget_line.id},
        ) == 1
        budget_page = SqlAlchemyFinanceBudgetReader(session=session).list_versions(
            tenant_id=TENANT_A,
            organization_id=ORG_A,
            project_id=PROJECT_A,
            request=FinancePageRequest(sort_key="revision", sort_direction="desc"),
        )
        assert budget_page.has_open_version is True
        assert budget_page.items[0].id == budget.id
        assert budget_page.items[0].total_amount == Decimal("125.50")
        assert session.scalar(
            text("SELECT count(*) FROM project_finance_forecasts WHERE id=:id"),
            {"id": forecast.id},
        ) == 1
        assert session.scalar(
            text(
                "SELECT count(*) FROM project_finance_forecast_lines "
                "WHERE forecast_id=:id AND amount=75.25"
            ),
            {"id": forecast.id},
        ) == 1
        assert session.scalar(
            text("SELECT count(*) FROM project_finance_change_requests WHERE id=:id"),
            {"id": change.id},
        ) == 1
    finally:
        session.close()


def test_r6c_command_foreign_scope_insert_is_denied(postgres_test_environment):
    boundary = _boundary(
        postgres_test_environment,
        scope=_TenantContext(TENANT_B, ORG_B),
    )
    with pytest.raises(DBAPIError):
        boundary.financial_setup(
            lambda service: service.create_cost_code(
                code="R6C-FOREIGN",
                name="Must be denied",
            )
        )


def test_r6c_command_same_tenant_foreign_organization_is_denied(
    postgres_test_environment,
) -> None:
    boundary = _boundary(
        postgres_test_environment,
        scope=_TenantContext(TENANT_A, ORG_A2),
    )
    with pytest.raises(DBAPIError):
        boundary.financial_setup(
            lambda service: service.create_cost_code(
                code="R6C-FOREIGN-ORG",
                name="Must be denied",
            )
        )


@pytest.mark.parametrize(
    ("table", "insert_sql"),
    (
        (
            "project_finance_forecast_lines",
            "INSERT INTO project_finance_forecast_lines "
            "(id, tenant_id, organization_id, forecast_id, project_id, cost_code_id, "
            "description, amount, currency_code, source_kind, source_type, created_by, "
            "version, created_at, updated_at) VALUES "
            "(:id, :tenant, :organization, :forecast, :project, :cost_code, "
            "'foreign child attack', 1.00, 'USD', 'manual', 'manual_estimate', "
            "'attacker', 1, :now, :now)",
        ),
        (
            "project_finance_forecast_source_decisions",
            "INSERT INTO project_finance_forecast_source_decisions "
            "(id, tenant_id, organization_id, forecast_id, project_id, cost_code_id, "
            "source_type, source_reference_type, source_reference_id, action, reason, "
            "source_amount, included_amount, excluded_amount, currency_code, "
            "source_snapshot_at, created_at) VALUES "
            "(:id, :tenant, :organization, :forecast, :project, :cost_code, "
            "'manual_estimate', 'manual_estimate', 'attack', 'included', "
            "'manual_override', 1.00, 1.00, 0.00, 'USD', :now, :now)",
        ),
    ),
)
def test_forecast_child_tables_deny_foreign_scope_inserts(
    postgres_test_environment, table: str, insert_sql: str
) -> None:
    with postgres_test_environment.admin_engine.connect() as connection:
        parent = connection.execute(
            text(
                "SELECT f.id AS forecast_id, l.cost_code_id "
                "FROM project_finance_forecasts f "
                "JOIN project_finance_forecast_lines l ON l.forecast_id=f.id "
                "WHERE f.tenant_id=:tenant AND f.organization_id=:organization "
                "AND f.project_id=:project LIMIT 1"
            ),
            {"tenant": TENANT_A, "organization": ORG_A, "project": PROJECT_A},
        ).mappings().one()

    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_B,
        organization_id=ORG_B,
    )
    try:
        with pytest.raises(DBAPIError):
            session.execute(
                text(insert_sql),
                {
                    "id": f"r6c-{table}-attack",
                    "tenant": TENANT_A,
                    "organization": ORG_A,
                    "forecast": parent["forecast_id"],
                    "project": PROJECT_A,
                    "cost_code": parent["cost_code_id"],
                    "now": datetime.now(timezone.utc),
                },
            )
            session.commit()
    finally:
        session.rollback()
        session.close()
