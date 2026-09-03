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
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpactType,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageRequest,
)
from src.core.platform.common.exceptions import ConcurrencyError
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
            "finance.read",
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
            planned_costs=SimpleNamespace(),
            commitments=SimpleNamespace(),
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
    impact = boundary.financial_change(
        lambda service: service.add_impact(
            change.id,
            impact_type=FinancialChangeImpactType.BUDGET,
            description="R6C governed budget impact",
            amount=Decimal("10.25"),
            currency_code="USD",
            cost_code_id=setup.id,
            expected_change_version=change.row_version,
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
        assert session.scalar(
            text("SELECT count(*) FROM project_finance_change_impacts WHERE id=:id"),
            {"id": impact.id},
        ) == 1
    finally:
        session.close()


def test_r6c_e_setup_commands_and_child_rows_are_rls_scoped(postgres_test_environment):
    boundary = _boundary(
        postgres_test_environment,
        scope=_TenantContext(TENANT_A, ORG_A),
    )
    profile = boundary.financial_setup(
        lambda service: service.get_profile(PROJECT_A),
        project_id=PROJECT_A,
    )
    updated = boundary.financial_setup(
        lambda service: service.configure_profile(
            PROJECT_A,
            expected_version=profile.version,
            budget_control_mode="block",
            cost_code_policy="restricted",
        ),
        project_id=PROJECT_A,
    )
    cost_code = boundary.financial_setup(
        lambda service: service.create_cost_code(
            code="R6CE-RUNTIME",
            name="R6C-E runtime code",
        )
    )
    restriction = boundary.financial_setup(
        lambda service: service.add_project_cost_code(
            project_id=PROJECT_A,
            cost_code_id=cost_code.id,
        ),
        project_id=PROJECT_A,
    )

    same_scope = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A,
        organization_id=ORG_A,
    )
    try:
        validate_postgresql_execution_role(same_scope)
        assert updated.version == profile.version + 1
        assert same_scope.scalar(
            text("SELECT count(*) FROM project_finance_profiles WHERE project_id=:id"),
            {"id": PROJECT_A},
        ) == 1
        assert same_scope.scalar(
            text("SELECT count(*) FROM project_finance_cost_codes WHERE id=:id"),
            {"id": cost_code.id},
        ) == 1
        assert same_scope.scalar(
            text("SELECT count(*) FROM project_finance_cost_code_restrictions WHERE id=:id"),
            {"id": restriction.id},
        ) == 1
    finally:
        same_scope.close()

    foreign = postgres_test_environment.runtime_session(
        tenant_id=TENANT_B,
        organization_id=ORG_B,
    )
    try:
        assert foreign.scalar(
            text("SELECT count(*) FROM project_finance_profiles WHERE project_id=:id"),
            {"id": PROJECT_A},
        ) == 0
        profile_update = foreign.execute(
            text(
                "UPDATE project_finance_profiles SET budget_control_mode='none' "
                "WHERE project_id=:id"
            ),
            {"id": PROJECT_A},
        )
        assert profile_update.rowcount == 0
        cost_code_update = foreign.execute(
            text("UPDATE project_finance_cost_codes SET name='attack' WHERE id=:id"),
            {"id": cost_code.id},
        )
        assert cost_code_update.rowcount == 0
        cost_code_delete = foreign.execute(
            text("DELETE FROM project_finance_cost_codes WHERE id=:id"),
            {"id": cost_code.id},
        )
        assert cost_code_delete.rowcount == 0
        restriction_update = foreign.execute(
            text(
                "UPDATE project_finance_cost_code_restrictions "
                "SET created_at=:now WHERE id=:id"
            ),
            {"id": restriction.id, "now": datetime.now(timezone.utc)},
        )
        assert restriction_update.rowcount == 0
        restriction_delete = foreign.execute(
            text("DELETE FROM project_finance_cost_code_restrictions WHERE id=:id"),
            {"id": restriction.id},
        )
        assert restriction_delete.rowcount == 0
        foreign.commit()

        with pytest.raises(DBAPIError):
            foreign.execute(
                text(
                    "INSERT INTO project_finance_cost_codes "
                    "(id, tenant_id, organization_id, code, name, is_active, version, created_at, updated_at) "
                    "VALUES ('r6ce-cost-code-attack', :tenant, :organization, "
                    "'ATTACK', 'Attack', true, 1, :now, :now)"
                ),
                {
                    "tenant": TENANT_A,
                    "organization": ORG_A,
                    "now": datetime.now(timezone.utc),
                },
            )
            foreign.commit()
        foreign.rollback()

        with pytest.raises(DBAPIError):
            foreign.execute(
                text(
                    "INSERT INTO project_finance_cost_code_restrictions "
                    "(id, tenant_id, organization_id, project_id, cost_code_id, created_at) "
                    "VALUES ('r6ce-restriction-attack', :tenant, :organization, "
                    ":project, :cost_code, :now)"
                ),
                {
                    "tenant": TENANT_A,
                    "organization": ORG_A,
                    "project": PROJECT_A,
                    "cost_code": cost_code.id,
                    "now": datetime.now(timezone.utc),
                },
            )
            foreign.commit()
        foreign.rollback()
    finally:
        foreign.rollback()
        foreign.close()

    foreign_org = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A,
        organization_id=ORG_A2,
    )
    try:
        assert foreign_org.scalar(
            text("SELECT count(*) FROM project_finance_profiles WHERE project_id=:id"),
            {"id": PROJECT_A},
        ) == 0
        assert foreign_org.execute(
            text("UPDATE project_finance_cost_codes SET name='org attack' WHERE id=:id"),
            {"id": cost_code.id},
        ).rowcount == 0
        foreign_org.commit()
    finally:
        foreign_org.rollback()
        foreign_org.close()

    boundary.financial_setup(
        lambda service: service.configure_profile(
            PROJECT_A,
            expected_version=updated.version,
            cost_code_policy="all_active",
        ),
        project_id=PROJECT_A,
    )


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


def test_financial_change_impact_child_table_denies_foreign_direct_writes(
    postgres_test_environment,
) -> None:
    with postgres_test_environment.admin_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT i.id AS impact_id, i.change_request_id, i.cost_code_id "
                "FROM project_finance_change_impacts i "
                "WHERE i.tenant_id=:tenant AND i.organization_id=:organization "
                "AND i.description='R6C governed budget impact'"
            ),
            {"tenant": TENANT_A, "organization": ORG_A},
        ).mappings().one()

    foreign = postgres_test_environment.runtime_session(
        tenant_id=TENANT_B,
        organization_id=ORG_B,
    )
    try:
        assert foreign.scalar(
            text("SELECT count(*) FROM project_finance_change_impacts WHERE id=:id"),
            {"id": row["impact_id"]},
        ) == 0
        with pytest.raises(DBAPIError):
            foreign.execute(
                text(
                    "INSERT INTO project_finance_change_impacts "
                    "(id, tenant_id, organization_id, change_request_id, project_id, "
                    "impact_type, description, amount, currency_code, cost_code_id, "
                    "version, created_at, updated_at) VALUES "
                    "('r6c-change-impact-attack', :tenant, :organization, :change, "
                    ":project, 'budget', 'foreign child attack', 1.00, 'USD', "
                    ":cost_code, 1, :now, :now)"
                ),
                {
                    "tenant": TENANT_A,
                    "organization": ORG_A,
                    "change": row["change_request_id"],
                    "project": PROJECT_A,
                    "cost_code": row["cost_code_id"],
                    "now": datetime.now(timezone.utc),
                },
            )
            foreign.commit()
        foreign.rollback()

        updated = foreign.execute(
            text(
                "UPDATE project_finance_change_impacts "
                "SET description='foreign update' WHERE id=:id"
            ),
            {"id": row["impact_id"]},
        )
        assert updated.rowcount == 0
        foreign.commit()

        deleted = foreign.execute(
            text("DELETE FROM project_finance_change_impacts WHERE id=:id"),
            {"id": row["impact_id"]},
        )
        assert deleted.rowcount == 0
        foreign.commit()
    finally:
        foreign.rollback()
        foreign.close()


def test_financial_change_request_and_impact_stale_writes_fail_closed(
    postgres_test_environment,
) -> None:
    boundary = _boundary(
        postgres_test_environment,
        scope=_TenantContext(TENANT_A, ORG_A),
    )
    change = boundary.financial_change(
        lambda service: service.create_change(
            PROJECT_A,
            title="R6C Concurrency Change",
            reason="Live stale-write proof",
            effective_date=date(2026, 9, 2),
            created_by="r6c-runtime-user",
        ),
        project_id=PROJECT_A,
    )
    updated = boundary.financial_change(
        lambda service: service.update_change(
            change.id,
            title="R6C Concurrency Change A",
            reason=change.reason,
            description=change.description,
            effective_date=change.effective_date,
            expected_version=change.row_version,
        )
    )
    with pytest.raises(ConcurrencyError):
        boundary.financial_change(
            lambda service: service.update_change(
                change.id,
                title="R6C Concurrency Change B",
                reason=change.reason,
                description=change.description,
                effective_date=change.effective_date,
                expected_version=change.row_version,
            )
        )

    with postgres_test_environment.admin_engine.connect() as connection:
        cost_code_id = connection.scalar(
            text(
                "SELECT id FROM project_finance_cost_codes "
                "WHERE tenant_id=:tenant AND organization_id=:organization "
                "AND code='R6C-RUNTIME'"
            ),
            {"tenant": TENANT_A, "organization": ORG_A},
        )
    impact = boundary.financial_change(
        lambda service: service.add_impact(
            change.id,
            impact_type=FinancialChangeImpactType.BUDGET,
            description="Concurrent impact",
            amount=Decimal("2.00"),
            currency_code="USD",
            cost_code_id=cost_code_id,
            expected_change_version=updated.row_version,
        )
    )
    first_impact_update = boundary.financial_change(
        lambda service: service.update_impact(
            impact.id,
            impact_type=impact.impact_type,
            description="Concurrent impact A",
            amount=impact.amount,
            currency_code=impact.currency_code,
            cost_code_id=impact.cost_code_id,
            expected_impact_version=impact.row_version,
            expected_change_version=updated.row_version + 1,
        )
    )
    current_change = boundary.financial_change(
        lambda service: service.get_change(change.id)
    )
    assert first_impact_update.row_version == impact.row_version + 1
    with pytest.raises(ConcurrencyError):
        boundary.financial_change(
            lambda service: service.update_impact(
                impact.id,
                impact_type=impact.impact_type,
                description="Concurrent impact B",
                amount=impact.amount,
                currency_code=impact.currency_code,
                cost_code_id=impact.cost_code_id,
                expected_impact_version=impact.row_version,
                expected_change_version=current_change.row_version,
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
