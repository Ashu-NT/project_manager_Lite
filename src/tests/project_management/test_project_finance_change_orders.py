from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from src.core.modules.project_management.domain.financials.budget import BudgetStatus
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeImpactType,
    FinancialChangeStatus,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
    ForecastStatus,
)
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError


def _login(services, username: str, password: str) -> None:
    user = services["auth_service"].authenticate(username, password)
    services["user_session"].set_principal(
        services["auth_service"].build_principal(user)
    )


def _seed_approved_finance(services):
    project = services["project_service"].create_project(
        "Controlled Change Project", financial_currency_code="USD"
    )
    code = services["financial_configuration_service"].create_cost_code(
        code="CHG-001", name="Change control"
    )

    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "Approved control budget")
    budget_line = budgets.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Approved scope",
        amount=Decimal("100"),
        expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(
        budget.id, "admin", expected_version=budget.row_version
    )
    result = budgets.approve_budget(
        budget.id, approved_by="admin", expected_version=budget.row_version
    )
    budget = budgets.get_budget(result.budget_id)

    forecasts = services["forecast_version_service"]
    forecast = forecasts.create_forecast(
        project.id,
        name="Approved forecast",
        as_of_date=date(2026, 8, 11),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )
    forecast_line = forecasts.add_line(
        forecast.id,
        cost_code_id=code.id,
        description="Approved ETC",
        amount=Decimal("80"),
        source_kind=ForecastLineSourceKind.MANUAL,
        source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin",
        expected_forecast_version=forecast.row_version,
    )
    forecast = forecasts.get_forecast(forecast.id)
    forecast = forecasts.submit_forecast(
        forecast.id, submitted_by="admin", expected_version=forecast.row_version
    )
    forecast = forecasts.approve_forecast(
        forecast.id, approved_by="admin", expected_version=forecast.row_version
    )
    return project, code, budget, budget_line, forecast, forecast_line


def _draft_change(services, project):
    principal = services["user_session"].principal
    return services["financial_change_service"].create_change(
        project.id,
        title="Approved scope adjustment",
        reason="Customer-approved engineering change",
        effective_date=date(2026, 8, 11),
        created_by=principal.user_id,
    )


def test_negative_financial_delta_requires_an_exact_target() -> None:
    with pytest.raises(ValidationError):
        FinancialChangeImpact.create(
            tenant_id="tenant-a",
            organization_id="org-a",
            change_request_id="change-a",
            project_id="project-a",
            impact_type=FinancialChangeImpactType.BUDGET,
            description="Unscoped reduction",
            amount=Decimal("-10"),
            currency_code="USD",
            cost_code_id="code-a",
        )


def test_approved_change_atomically_creates_budget_and_forecast_successors(
    services,
) -> None:
    _login(services, "admin", "ChangeMe123!")
    project, code, budget, budget_line, forecast, forecast_line = (
        _seed_approved_finance(services)
    )
    services["auth_service"].register_user(
        "change-requester", "StrongPass123", role_names=["planner"]
    )
    _login(services, "change-requester", "StrongPass123")

    changes = services["financial_change_service"]
    change = _draft_change(services, project)
    budget_impact = changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.BUDGET,
        description="Increase approved scope",
        amount=Decimal("25"),
        cost_code_id=code.id,
        target_line_id=budget_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    forecast_impact = changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.FORECAST,
        description="Reduce remaining ETC",
        amount=Decimal("-15"),
        cost_code_id=code.id,
        target_line_id=forecast_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    change = changes.submit_change(
        change.id,
        submitted_by=services["user_session"].principal.user_id,
        expected_version=change.row_version,
    )
    assert change.status is FinancialChangeStatus.PENDING_APPROVAL
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    assert request.request_type == "financial_change.apply"

    _login(services, "admin", "ChangeMe123!")
    admin_id = services["user_session"].principal.user_id
    services["approval_service"].approve_and_apply(
        request.id, note="Authorized change"
    )

    applied = changes.get_change(change.id)
    assert applied.status is FinancialChangeStatus.APPLIED
    assert applied.applied_by == admin_id
    assert applied.applied_budget_id and applied.applied_budget_id != budget.id
    assert applied.applied_forecast_id and applied.applied_forecast_id != forecast.id

    budgets = services["budget_service"]
    assert budgets.get_budget(budget.id).status is BudgetStatus.SUPERSEDED
    successor_budget = budgets.get_budget(applied.applied_budget_id)
    assert successor_budget.status is BudgetStatus.APPROVED
    assert budgets.list_lines(successor_budget.id)[0].amount == Decimal("125")

    forecasts = services["forecast_version_service"]
    assert forecasts.get_forecast(forecast.id).status is ForecastStatus.SUPERSEDED
    successor_forecast = forecasts.get_forecast(applied.applied_forecast_id)
    assert successor_forecast.status is ForecastStatus.APPROVED
    assert forecasts.list_lines(successor_forecast.id)[0].amount == Decimal("65")
    assert {
        row.source_type for row in forecasts.list_source_decisions(successor_forecast.id)
    } == {ForecastLineSourceType.FINANCIAL_CHANGE}

    impacts = {row.id: row for row in changes.list_impacts(applied.id)}
    assert impacts[budget_impact.id].applied_line_id
    assert impacts[forecast_impact.id].applied_line_id


def test_owner_command_impacts_are_blocked_until_authoritative_adapters_exist(
    services,
) -> None:
    _login(services, "admin", "ChangeMe123!")
    project, code, *_ = _seed_approved_finance(services)
    changes = services["financial_change_service"]
    change = _draft_change(services, project)
    changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.CONTRACT,
        description="Contract value adjustment",
        amount=Decimal("10"),
        cost_code_id=code.id,
        source_reference_type="project_commitment",
        source_reference_id="commitment-a",
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)

    with pytest.raises(
        BusinessRuleError, match="authoritative owner-command adapters"
    ):
        changes.submit_change(
            change.id, submitted_by="admin", expected_version=change.row_version
        )
    assert changes.get_change(change.id).status is FinancialChangeStatus.DRAFT


def test_impact_write_rolls_back_when_financial_audit_fails(
    services, monkeypatch
) -> None:
    _login(services, "admin", "ChangeMe123!")
    project, code, _, budget_line, *_ = _seed_approved_finance(services)
    changes = services["financial_change_service"]
    change = _draft_change(services, project)
    monkeypatch.setattr(
        changes,
        "_audit_impact",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("audit unavailable")
        ),
    )

    with pytest.raises(RuntimeError, match="audit unavailable"):
        changes.add_impact(
            change.id,
            impact_type=FinancialChangeImpactType.BUDGET,
            description="Must be atomic",
            amount=Decimal("5"),
            cost_code_id=code.id,
            target_line_id=budget_line.id,
            expected_change_version=change.row_version,
        )

    assert changes.list_impacts(change.id) == []
    assert changes.get_change(change.id).row_version == change.row_version


def test_approval_rolls_back_all_successors_when_financial_audit_fails(
    services, monkeypatch
) -> None:
    _login(services, "admin", "ChangeMe123!")
    project, code, budget, budget_line, *_ = _seed_approved_finance(services)
    services["auth_service"].register_user(
        "rollback-requester", "StrongPass123", role_names=["planner"]
    )
    _login(services, "rollback-requester", "StrongPass123")
    changes = services["financial_change_service"]
    change = _draft_change(services, project)
    changes.add_impact(
        change.id,
        impact_type=FinancialChangeImpactType.BUDGET,
        description="Audited increase",
        amount=Decimal("5"),
        cost_code_id=code.id,
        target_line_id=budget_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    changes.submit_change(
        change.id,
        submitted_by=services["user_session"].principal.user_id,
        expected_version=change.row_version,
    )
    request = services["approval_service"].list_pending(project_id=project.id)[0]

    _login(services, "admin", "ChangeMe123!")
    monkeypatch.setattr(
        changes,
        "_audit_change",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("audit unavailable")
        ),
    )
    with pytest.raises(RuntimeError, match="audit unavailable"):
        services["approval_service"].approve_and_apply(request.id)

    assert changes.get_change(change.id).status is FinancialChangeStatus.PENDING_APPROVAL
    assert services["budget_service"].get_budget(budget.id).status is BudgetStatus.APPROVED
    assert len(services["budget_service"].list_budgets_for_project(project.id)) == 1
    assert services["approval_service"].list_pending(project_id=project.id)[0].id == request.id


def test_financial_change_migration_is_reversible_and_constrained(tmp_path) -> None:
    database_path = tmp_path / "financial-change-migration.db"
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    inspector = sa.inspect(engine)

    assert {
        "project_finance_change_requests",
        "project_finance_change_impacts",
    } <= set(inspector.get_table_names())
    request_checks = {
        row["name"] for row in inspector.get_check_constraints(
            "project_finance_change_requests"
        )
    }
    impact_checks = {
        row["name"] for row in inspector.get_check_constraints(
            "project_finance_change_impacts"
        )
    }
    request_constraints = {
        row["name"] for row in inspector.get_unique_constraints(
            "project_finance_change_requests"
        )
    }
    assert "ck_pf_changes_status" in request_checks
    assert "ck_pf_change_impacts_monetary_shape" in impact_checks
    assert "uq_pf_change_project_revision" in request_constraints
    engine.dispose()

    command.downgrade(config, "w0x1y2z3a4b5")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    tables = set(sa.inspect(engine).get_table_names())
    assert "project_finance_change_requests" not in tables
    assert "project_finance_change_impacts" not in tables
    engine.dispose()
