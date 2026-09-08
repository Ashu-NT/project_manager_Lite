from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from sqlalchemy import event

from src.core.modules.project_management.application.financials.forecasts.generation_service import (
    ManualEtcEstimate,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpactType,
)


_OBSERVED_SQL: list[list[str]] = []


def _login(services, username: str, password: str) -> None:
    user = services["auth_service"].authenticate(username, password)
    services["user_session"].set_principal(
        services["auth_service"].build_principal(user)
    )


def _measure(engine, operation: Callable[[], object]) -> tuple[object, int]:
    statements: list[str] = []

    def before_cursor_execute(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        result = operation()
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
    _OBSERVED_SQL.append(statements)
    return result, len(statements)


def _seed_approved_bases(services, *, suffix: str):
    project = services["project_service"].create_project(
        f"R6C-F SQL Change {suffix}", financial_currency_code="USD"
    )
    code = services["financial_configuration_service"].create_cost_code(
        code=f"R6CF-CHG-{suffix}", name="Change authority"
    )
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "Approved Budget")
    budget_line = budgets.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Approved scope",
        amount=Decimal("100"),
        expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(
        budget.id, submitted_by="admin", expected_version=budget.row_version
    )
    budgets.approve_budget(
        budget.id, approved_by="admin", expected_version=budget.row_version
    )

    forecasts = services["forecast_version_service"]
    forecast = forecasts.create_forecast(
        project.id,
        name="Approved Forecast",
        as_of_date=date(2026, 8, 1),
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
    forecasts.approve_forecast(
        forecast.id, approved_by="admin", expected_version=forecast.row_version
    )
    return project, code, budget, budget_line, forecast, forecast_line


def test_r6c_f_records_representative_write_statement_counts(services, session) -> None:
    _OBSERVED_SQL.clear()
    _login(services, "admin", "ChangeMe123!")
    engine = session.get_bind()
    counts: dict[str, int] = {}

    setup_project = services["project_service"].create_project(
        "R6C-F SQL Setup", financial_currency_code="USD"
    )
    setup = services["financial_configuration_service"]
    profile = setup.get_profile(setup_project.id)
    profile, counts["setup.profile_update"] = _measure(
        engine,
        lambda: setup.configure_profile(
            setup_project.id,
            expected_version=profile.version,
            budget_control_mode="warn",
        ),
    )
    setup_code, counts["setup.cost_code_create"] = _measure(
        engine,
        lambda: setup.create_cost_code(code="R6CF-SETUP", name="Setup code"),
    )
    setup_code, counts["setup.cost_code_update"] = _measure(
        engine,
        lambda: setup.update_cost_code(
            setup_code.id,
            expected_version=setup_code.version,
            name="Setup code updated",
        ),
    )
    _, counts["setup.restriction_add"] = _measure(
        engine,
        lambda: setup.add_project_cost_code(
            project_id=setup_project.id, cost_code_id=setup_code.id
        ),
    )
    _, counts["setup.restriction_remove"] = _measure(
        engine,
        lambda: setup.remove_project_cost_code(
            project_id=setup_project.id, cost_code_id=setup_code.id
        ),
    )

    budget_project = services["project_service"].create_project(
        "R6C-F SQL Budget", financial_currency_code="USD"
    )
    budget_code = setup.create_cost_code(code="R6CF-BUD", name="Budget code")
    budgets = services["budget_service"]
    budget, counts["budget.create"] = _measure(
        engine, lambda: budgets.create_budget(budget_project.id, "SQL Budget")
    )
    budget_line, counts["budget.line_add"] = _measure(
        engine,
        lambda: budgets.add_line(
            budget.id,
            cost_code_id=budget_code.id,
            description="Measured line",
            amount=Decimal("100"),
            expected_budget_version=budget.row_version,
        ),
    )
    budget = budgets.get_budget(budget.id)
    budget_line, counts["budget.line_update"] = _measure(
        engine,
        lambda: budgets.update_line(
            budget_line.id,
            expected_line_version=budget_line.row_version,
            expected_budget_version=budget.row_version,
            amount=Decimal("125"),
        ),
    )
    budget = budgets.get_budget(budget.id)
    budget, counts["budget.submit"] = _measure(
        engine,
        lambda: budgets.submit_budget(
            budget.id, submitted_by="admin", expected_version=budget.row_version
        ),
    )
    approval_result, counts["budget.approval_request"] = _measure(
        engine,
        lambda: budgets.request_budget_approval(
            budget.id, expected_version=budget.row_version
        ),
    )
    services["auth_service"].register_user(
        "r6cf-budget-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "r6cf-budget-reviewer", "StrongPass123")
    _, counts["budget.approval_decision"] = _measure(
        engine,
        lambda: services["approval_service"].approve_and_apply(
            approval_result.approval_request_id
        ),
    )
    _login(services, "admin", "ChangeMe123!")
    _, counts["budget.successor"] = _measure(
        engine,
        lambda: budgets.create_successor(budget.id, name="Measured successor"),
    )

    forecast_project = services["project_service"].create_project(
        "R6C-F SQL Forecast", financial_currency_code="USD"
    )
    forecast_code = setup.create_cost_code(code="R6CF-FC", name="Forecast code")
    extra_forecast_code = setup.create_cost_code(
        code="R6CF-FC-2", name="Forecast adjustment"
    )
    generated, counts["forecast.generate"] = _measure(
        engine,
        lambda: services["forecast_generation_service"].generate_draft(
            forecast_project.id,
            name="Measured Forecast",
            as_of_date=date(2026, 8, 1),
            generated_by="admin",
            manual_estimates=(
                ManualEtcEstimate(
                    cost_code_id=forecast_code.id,
                    description="Measured ETC",
                    amount=Decimal("50"),
                ),
            ),
        ),
    )
    forecasts = services["forecast_version_service"]
    forecast = generated.forecast
    _, counts["forecast.input_add"] = _measure(
        engine,
        lambda: forecasts.add_line(
            forecast.id,
            cost_code_id=extra_forecast_code.id,
            description="Governed adjustment",
            amount=Decimal("10"),
            source_kind=ForecastLineSourceKind.MANUAL,
            source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
            created_by="admin",
            expected_forecast_version=forecast.row_version,
        ),
    )
    forecast = forecasts.get_forecast(forecast.id)
    forecast, counts["forecast.submit"] = _measure(
        engine,
        lambda: forecasts.submit_forecast(
            forecast.id, submitted_by="admin", expected_version=forecast.row_version
        ),
    )
    forecast_approval, counts["forecast.approval_request"] = _measure(
        engine,
        lambda: forecasts.request_forecast_approval(
            forecast.id, expected_version=forecast.row_version
        ),
    )
    services["auth_service"].register_user(
        "r6cf-forecast-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "r6cf-forecast-reviewer", "StrongPass123")
    _, counts["forecast.approval_decision"] = _measure(
        engine,
        lambda: services["approval_service"].approve_and_apply(
            forecast_approval.approval_request_id
        ),
    )
    _login(services, "admin", "ChangeMe123!")
    _, counts["forecast.regenerate_successor"] = _measure(
        engine,
        lambda: services["forecast_generation_service"].generate_draft(
            forecast_project.id,
            name="Measured Forecast successor",
            as_of_date=date(2026, 8, 2),
            generated_by="admin",
            manual_estimates=(
                ManualEtcEstimate(
                    cost_code_id=forecast_code.id,
                    description="Measured successor ETC",
                    amount=Decimal("45"),
                ),
            ),
        ),
    )

    change_project, change_code, _budget, budget_line, _forecast, _forecast_line = (
        _seed_approved_bases(services, suffix="A")
    )
    services["auth_service"].register_user(
        "r6cf-change-requester", "StrongPass123", role_names=["planner"]
    )
    _login(services, "r6cf-change-requester", "StrongPass123")
    changes = services["financial_change_service"]
    change, counts["change.create"] = _measure(
        engine,
        lambda: changes.create_change(
            change_project.id,
            title="Measured Change",
            reason="SQL characterization",
            effective_date=date(2026, 8, 3),
            created_by=services["user_session"].principal.user_id,
        ),
    )
    impact, counts["change.impact_add"] = _measure(
        engine,
        lambda: changes.add_impact(
            change.id,
            impact_type=FinancialChangeImpactType.BUDGET,
            description="Measured impact",
            amount=Decimal("5"),
            cost_code_id=change_code.id,
            target_line_id=budget_line.id,
            expected_change_version=change.row_version,
        ),
    )
    change = changes.get_change(change.id)
    _, counts["change.impact_update"] = _measure(
        engine,
        lambda: changes.update_impact(
            impact.id,
            impact_type=impact.impact_type,
            description="Measured impact updated",
            amount=impact.amount,
            currency_code=impact.currency_code,
            cost_code_id=impact.cost_code_id,
            target_line_id=impact.target_line_id,
            expected_impact_version=impact.row_version,
            expected_change_version=change.row_version,
        ),
    )
    change = changes.get_change(change.id)
    change, counts["change.submit"] = _measure(
        engine,
        lambda: changes.submit_change(
            change.id,
            submitted_by=services["user_session"].principal.user_id,
            expected_version=change.row_version,
        ),
    )
    approval = services["approval_service"].list_pending(
        project_id=change_project.id
    )[0]
    _login(services, "admin", "ChangeMe123!")
    _, counts["change.decision_apply"] = _measure(
        engine,
        lambda: services["approval_service"].approve_and_apply(approval.id),
    )

    print("R6C-F SQL statement counts:", dict(sorted(counts.items())))
    for label, statements in zip(counts, _OBSERVED_SQL, strict=True):
        if len(statements) < 30:
            continue
        repeated = Counter(" ".join(statement.split()) for statement in statements)
        print(
            f"R6C-F repeated SQL shapes for {label}:",
            [(count, statement[:220]) for statement, count in repeated.most_common(5)],
        )
    assert counts
    assert all(count > 0 for count in counts.values())
