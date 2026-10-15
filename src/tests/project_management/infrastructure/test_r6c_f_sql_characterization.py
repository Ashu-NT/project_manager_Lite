from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from sqlalchemy import event

from src.core.modules.project_management.application.financials.forecasts.generation_models import (
    ManualEtcEstimate,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpactType,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
)

_OBSERVED_SQL: list[list[str]] = []


def _login(services, username: str, password: str) -> None:
    user = services["authentication"].authenticate(username, password)
    services["user_session"].set_principal(
        services["principal_builder"].build(user)
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
    project = services['project_create'].create_project(
        f"R6C-F SQL Change {suffix}", financial_currency_code="USD"
    )
    code = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(
        code=f"R6CF-CHG-{suffix}", name="Change authority"
    ))
    services['budget_query']
    budget = services['finance_governance_commands'].budget_lifecycle(lambda handler: handler.create_budget(project.id, "Approved Budget"))
    budget_line = services['finance_governance_commands'].budget_lines(lambda handler: handler.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Approved scope",
        amount=Decimal(100),
        expected_budget_version=budget.row_version,
    ))
    budget = services['budget_query'].get_budget(budget.id)
    budget = services['finance_governance_commands'].budget_lifecycle(lambda handler: handler.submit_budget(
        budget.id, submitted_by="admin", expected_version=budget.row_version
    ))
    services['finance_governance_commands'].budget_approval(lambda handler: handler.approve_budget(
        budget.id, approved_by="admin", expected_version=budget.row_version
    ))

    services['forecast_version_query']
    forecast = services['finance_governance_commands'].forecast_lifecycle(lambda handler: handler.create_forecast(
        project.id,
        name="Approved Forecast",
        as_of_date=date(2026, 8, 1),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    ))
    forecast_line = services['finance_governance_commands'].forecast_lines(lambda handler: handler.add_line(
        forecast.id,
        cost_code_id=code.id,
        description="Approved ETC",
        amount=Decimal(80),
        source_kind=ForecastLineSourceKind.MANUAL,
        source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin",
        expected_forecast_version=forecast.row_version,
    ))
    forecast = services['forecast_version_query'].get_forecast(forecast.id)
    forecast = services['finance_governance_commands'].forecast_lifecycle(lambda handler: handler.submit_forecast(
        forecast.id, submitted_by="admin", expected_version=forecast.row_version
    ))
    services['finance_governance_commands'].forecast_approval(lambda handler: handler.approve_forecast(
        forecast.id, approved_by="admin", expected_version=forecast.row_version
    ))
    return project, code, budget, budget_line, forecast, forecast_line


def test_r6c_f_records_representative_write_statement_counts(services, session) -> None:
    _OBSERVED_SQL.clear()
    _login(services, "admin", "ChangeMe123!")
    engine = session.get_bind()
    counts: dict[str, int] = {}

    setup_project = services['project_create'].create_project(
        "R6C-F SQL Setup", financial_currency_code="USD"
    )
    services['financial_configuration_query']
    profile = services['financial_configuration_query'].get_profile(setup_project.id)
    profile, counts["setup.profile_update"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].financial_profile(lambda handler: handler.configure_profile(
            setup_project.id,
            expected_version=profile.version,
            budget_control_mode="warn",
        )),
    )
    setup_code, counts["setup.cost_code_create"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(code="R6CF-SETUP", name="Setup code")),
    )
    setup_code, counts["setup.cost_code_update"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].cost_code(lambda handler: handler.update_cost_code(
            setup_code.id,
            expected_version=setup_code.version,
            name="Setup code updated",
        )),
    )
    _, counts["setup.restriction_add"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].cost_code(lambda handler: handler.add_project_cost_code(
            project_id=setup_project.id, cost_code_id=setup_code.id
        )),
    )
    _, counts["setup.restriction_remove"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].cost_code(lambda handler: handler.remove_project_cost_code(
            project_id=setup_project.id, cost_code_id=setup_code.id
        )),
    )

    budget_project = services['project_create'].create_project(
        "R6C-F SQL Budget", financial_currency_code="USD"
    )
    budget_code = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(code="R6CF-BUD", name="Budget code"))
    services['budget_query']
    budget, counts["budget.create"] = _measure(
        engine, lambda: services['finance_governance_commands'].budget_lifecycle(lambda handler: handler.create_budget(budget_project.id, "SQL Budget"))
    )
    budget_line, counts["budget.line_add"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].budget_lines(lambda handler: handler.add_line(
            budget.id,
            cost_code_id=budget_code.id,
            description="Measured line",
            amount=Decimal(100),
            expected_budget_version=budget.row_version,
        )),
    )
    budget = services['budget_query'].get_budget(budget.id)
    budget_line, counts["budget.line_update"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].budget_lines(lambda handler: handler.update_line(
            budget_line.id,
            expected_line_version=budget_line.row_version,
            expected_budget_version=budget.row_version,
            amount=Decimal(125),
        )),
    )
    budget = services['budget_query'].get_budget(budget.id)
    budget, counts["budget.submit"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].budget_lifecycle(lambda handler: handler.submit_budget(
            budget.id, submitted_by="admin", expected_version=budget.row_version
        )),
    )
    approval_result, counts["budget.approval_request"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].budget_approval(lambda handler: handler.request_budget_approval(
            budget.id, expected_version=budget.row_version
        )),
    )
    services["user_registration"].register_user(
        "r6cf-budget-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "r6cf-budget-reviewer", "StrongPass123")
    _, counts["budget.approval_decision"] = _measure(
        engine,
        lambda: services["approval_commands"].approve_and_apply(
            approval_result.approval_request_id
        ),
    )
    _login(services, "admin", "ChangeMe123!")
    _, counts["budget.successor"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].budget_lifecycle(lambda handler: handler.create_successor(budget.id, name="Measured successor")),
    )

    forecast_project = services['project_create'].create_project(
        "R6C-F SQL Forecast", financial_currency_code="USD"
    )
    forecast_code = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(code="R6CF-FC", name="Forecast code"))
    extra_forecast_code = services['finance_governance_commands'].cost_code(lambda handler: handler.create_cost_code(
        code="R6CF-FC-2", name="Forecast adjustment"
    ))
    generated, counts["forecast.generate"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].forecast_generation(lambda handler: handler.generate_draft(
            forecast_project.id,
            name="Measured Forecast",
            as_of_date=date(2026, 8, 1),
            generated_by="admin",
            manual_estimates=(
                ManualEtcEstimate(
                    cost_code_id=forecast_code.id,
                    description="Measured ETC",
                    amount=Decimal(50),
                ),
            ),
        )),
    )
    services['forecast_version_query']
    forecast = generated.forecast
    _, counts["forecast.input_add"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].forecast_lines(lambda handler: handler.add_line(
            forecast.id,
            cost_code_id=extra_forecast_code.id,
            description="Governed adjustment",
            amount=Decimal(10),
            source_kind=ForecastLineSourceKind.MANUAL,
            source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
            created_by="admin",
            expected_forecast_version=forecast.row_version,
        )),
    )
    forecast = services['forecast_version_query'].get_forecast(forecast.id)
    forecast, counts["forecast.submit"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].forecast_lifecycle(lambda handler: handler.submit_forecast(
            forecast.id, submitted_by="admin", expected_version=forecast.row_version
        )),
    )
    forecast_approval, counts["forecast.approval_request"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].forecast_approval(lambda handler: handler.request_forecast_approval(
            forecast.id, expected_version=forecast.row_version
        )),
    )
    services["user_registration"].register_user(
        "r6cf-forecast-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "r6cf-forecast-reviewer", "StrongPass123")
    _, counts["forecast.approval_decision"] = _measure(
        engine,
        lambda: services["approval_commands"].approve_and_apply(
            forecast_approval.approval_request_id
        ),
    )
    _login(services, "admin", "ChangeMe123!")
    _, counts["forecast.regenerate_successor"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].forecast_generation(lambda handler: handler.generate_draft(
            forecast_project.id,
            name="Measured Forecast successor",
            as_of_date=date(2026, 8, 2),
            generated_by="admin",
            manual_estimates=(
                ManualEtcEstimate(
                    cost_code_id=forecast_code.id,
                    description="Measured successor ETC",
                    amount=Decimal(45),
                ),
            ),
        )),
    )

    change_project, change_code, _budget, budget_line, _forecast, _forecast_line = (
        _seed_approved_bases(services, suffix="A")
    )
    services["user_registration"].register_user(
        "r6cf-change-requester", "StrongPass123", role_names=["planner"]
    )
    _login(services, "r6cf-change-requester", "StrongPass123")
    services['financial_change_query']
    change, counts["change.create"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].financial_change(lambda handler: handler.create_change(
            change_project.id,
            title="Measured Change",
            reason="SQL characterization",
            effective_date=date(2026, 8, 3),
            created_by=services["user_session"].principal.user_id,
        )),
    )
    impact, counts["change.impact_add"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].financial_change(lambda handler: handler.add_impact(
            change.id,
            impact_type=FinancialChangeImpactType.BUDGET,
            description="Measured impact",
            amount=Decimal(5),
            cost_code_id=change_code.id,
            target_line_id=budget_line.id,
            expected_change_version=change.row_version,
        )).impact,
    )
    change = services['financial_change_query'].get_change(change.id)
    _, counts["change.impact_update"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].financial_change(lambda handler: handler.update_impact(
            impact.id,
            impact_type=impact.impact_type,
            description="Measured impact updated",
            amount=impact.amount,
            currency_code=impact.currency_code,
            cost_code_id=impact.cost_code_id,
            target_line_id=impact.target_line_id,
            expected_impact_version=impact.row_version,
            expected_change_version=change.row_version,
        )).impact,
    )
    change = services['financial_change_query'].get_change(change.id)
    change, counts["change.submit"] = _measure(
        engine,
        lambda: services['finance_governance_commands'].financial_change_submission(lambda handler: handler.submit_change(
            change.id,
            submitted_by=services["user_session"].principal.user_id,
            expected_version=change.row_version,
        )),
    )
    approval = services["approval_queries"].list_pending(
        project_id=change_project.id
    )[0]
    _login(services, "admin", "ChangeMe123!")
    services["user_registration"].register_user(
        "sql-change-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "sql-change-reviewer", "StrongPass123")
    _, counts["change.decision_apply"] = _measure(
        engine,
        lambda: services["approval_commands"].approve_and_apply(approval.id),
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
