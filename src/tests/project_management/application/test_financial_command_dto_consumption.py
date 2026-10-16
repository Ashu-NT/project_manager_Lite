from __future__ import annotations

import inspect
from dataclasses import MISSING, fields
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.application.financials.budgets._command_values import (
    command_amount as budget_amount,
)
from src.core.modules.project_management.application.financials.budgets.commands.lifecycle import (
    BudgetLifecycleCommands,
)
from src.core.modules.project_management.application.financials.budgets.commands.lines import (
    BudgetLineCommands,
)
from src.core.modules.project_management.application.financials.budgets.dto.commands.budget_lifecycle import (
    FinancialCreateBudgetSuccessorCommand,
    FinancialCreateBudgetVersionCommand,
    FinancialUpdateBudgetCommand,
    FinancialVersionedBudgetCommand,
)
from src.core.modules.project_management.application.financials.budgets.dto.commands.budget_lines import (
    FinancialAddBudgetLineCommand,
    FinancialDeleteBudgetLineCommand,
    FinancialUpdateBudgetLineCommand,
)
from src.core.modules.project_management.application.financials.configuration.dto.commands.cost_codes import (
    FinancialChangeCostCodeStatusCommand,
    FinancialCostCodeRestrictionCommand,
    FinancialCreateCostCodeCommand,
    FinancialUpdateCostCodeCommand,
)
from src.core.modules.project_management.application.financials.configuration.dto.commands.financial_profile import (
    FinancialTransitionProfileCommand,
    FinancialUpdateProfileCommand,
)
from src.core.modules.project_management.application.financials.forecasts._command_values import (
    command_amount as forecast_amount,
)
from src.core.modules.project_management.application.financials.forecasts._command_values import (
    command_date,
)
from src.core.modules.project_management.application.financials.forecasts.dto.commands.forecast_generation import (
    FinancialGenerateForecastCommand,
)
from src.core.modules.project_management.application.financials.forecasts.dto.commands.forecast_lifecycle import (
    FinancialVersionedForecastCommand,
)
from src.core.modules.project_management.application.financials.rate_cards._command_values import (
    command_amount as rate_amount,
)
from src.core.modules.project_management.application.financials.rate_cards._command_values import (
    optional_command_amount,
)
from src.core.modules.project_management.application.financials.rate_cards.commands.lines import (
    RateCardLineCommandHandler,
)
from src.core.modules.project_management.application.financials.rate_cards.dto.commands.rate_cards import (
    FinancialCreateRateCardCommand,
    FinancialUpdateRateCardCommand,
    FinancialVersionedRateCardCommand,
)
from src.core.modules.project_management.application.financials.rate_cards.dto.commands.rate_lines import (
    FinancialAddRateLineCommand,
    FinancialUpdateRateLineCommand,
    FinancialVersionedRateLineCommand,
)
from src.core.modules.project_management.domain.financials.budget import (
    BudgetLine,
    ProjectBudget,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    ValidationError,
)
from src.core.platform.domain.security.auth.session import (
    UserSessionContext,
    UserSessionPrincipal,
)

CASES = [
    ("create_cost_code", "create_cost_code", FinancialCreateCostCodeCommand),
    ("update_financial_profile", "configure_profile", FinancialUpdateProfileCommand),
    ("transition_financial_profile", "transition_profile", FinancialTransitionProfileCommand),
    ("update_cost_code", "update_cost_code", FinancialUpdateCostCodeCommand),
    ("change_cost_code_status", "activate_cost_code", FinancialChangeCostCodeStatusCommand),
    ("add_cost_code_restriction", "add_project_cost_code", FinancialCostCodeRestrictionCommand),
    ("remove_cost_code_restriction", "remove_project_cost_code", FinancialCostCodeRestrictionCommand),
    ("generate_forecast", "generate_draft", FinancialGenerateForecastCommand),
    ("submit_forecast", "submit_forecast", FinancialVersionedForecastCommand),
    ("request_forecast_approval", "request_forecast_approval", FinancialVersionedForecastCommand),
    ("create_rate_card", "create_rate_card", FinancialCreateRateCardCommand),
    ("update_rate_card", "update_rate_card", FinancialUpdateRateCardCommand),
    ("deactivate_rate_card", "deactivate_rate_card", FinancialVersionedRateCardCommand),
    ("add_rate_line", "create_line", FinancialAddRateLineCommand),
    ("update_rate_line", "update_line", FinancialUpdateRateLineCommand),
    ("deactivate_rate_line", "deactivate_line", FinancialVersionedRateLineCommand),
    ("create_budget_version", "create_budget", FinancialCreateBudgetVersionCommand),
    ("create_budget_successor", "create_successor", FinancialCreateBudgetSuccessorCommand),
    ("update_budget", "update_budget_header", FinancialUpdateBudgetCommand),
    ("delete_budget", "delete_budget", FinancialVersionedBudgetCommand),
    ("add_budget_line", "add_line", FinancialAddBudgetLineCommand),
    ("update_budget_line", "update_line", FinancialUpdateBudgetLineCommand),
    ("delete_budget_line", "delete_line", FinancialDeleteBudgetLineCommand),
    ("submit_budget", "submit_budget", FinancialVersionedBudgetCommand),
    ("request_budget_approval", "request_budget_approval", FinancialVersionedBudgetCommand),
    ("close_budget", "close_budget", FinancialVersionedBudgetCommand),
]


def _make_command(dto):
    values = {
        "amount": "0.00", "rate_amount": "0.00", "activate": True,
        "currency_code": "USD", "rate_currency": "USD", "rate_type": "cost",
        "unit": "HOUR", "as_of_date": "2026-09-01",
        "is_funded": False, "is_billable": False,
        "financial_start_date": None, "financial_end_date": None,
        "effective_from": None, "effective_to": None,
        "parent_id": None, "external_system": None, "external_reference": None,
        "default_cost_code_id": None,
    }
    return dto(**{
        field.name: values.get(field.name, 1 if field.name.startswith("expected_") else field.name)
        for field in fields(dto)
        if field.default is MISSING and field.default_factory is MISSING
    })


@pytest.mark.parametrize(("api_method", "handler_method", "dto"), CASES)
def test_desktop_callback_passes_exact_command_to_injected_handler(api_method, handler_method, dto):
    command = _make_command(dto)
    result = SimpleNamespace(
        id="entity-1", project_id="project-1", budget_id="budget-1",
        rate_card_id="card-1", row_version=2, version=2,
        status=SimpleNamespace(value="draft"),
        budget_status=SimpleNamespace(value="submitted"),
        forecast_id="forecast-1", forecast_status=SimpleNamespace(value="submitted"),
        approval_request_id="approval-1", code="CC", name="Cost code",
    )
    result.forecast = result
    operation = Mock(return_value=result)
    handler = SimpleNamespace(**{handler_method: operation})
    boundary = SimpleNamespace(**{
        name: (lambda callback: callback(handler))
        for name in (
            "budget_lifecycle", "budget_lines", "budget_approval",
            "forecast_generation", "forecast_lifecycle", "forecast_approval",
            "financial_profile", "cost_code", "rate_card", "rate_line",
        )
    })
    api = ProjectManagementFinancialsDesktopApi(finance_governance_commands=boundary)
    getattr(api, api_method)(command)
    operation.assert_called_once_with(command)
    assert operation.call_args.args[0] is command


@pytest.mark.parametrize(
    ("parser", "code"),
    [
        (budget_amount, "PROJECT_BUDGET_LINE_AMOUNT_INVALID"),
        (forecast_amount, "PROJECT_FORECAST_AMOUNT_INVALID"),
        (lambda value: rate_amount(value, "Rate amount"), "RATE_CARD_DECIMAL_INVALID"),
    ],
)
@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "not-money", ""])
def test_application_money_parsing_preserves_canonical_exceptions(parser, code, value):
    with pytest.raises(ValidationError) as error:
        parser(value)
    assert error.value.code == code


def test_decimal_zero_and_optional_modifiers_are_not_coalesced():
    assert budget_amount("0.00") == Decimal("0.00")
    assert forecast_amount("0.00") == Decimal("0.00")
    assert optional_command_amount("0") == Decimal(0)
    assert optional_command_amount("") is None
    assert optional_command_amount(None) is None
    assert command_date("2026-09-01", "As-of") == date(2026, 9, 1)
    with pytest.raises(ValidationError) as error:
        command_date("invalid", "As-of")
    assert error.value.code == "PROJECT_FORECAST_DATE_INVALID"


def _budget_handler():
    now = datetime(2026, 9, 1, tzinfo=UTC)
    budget = ProjectBudget.create(
        tenant_id="tenant-1", organization_id="org-1", project_id="project-1",
        name="Budget", currency_code="USD", created_at=now,
    )
    repo = Mock()
    repo.get.return_value = budget
    cost_codes = Mock()
    cost_codes.get.return_value = SimpleNamespace(is_effective_on=lambda day: True)
    profiles = Mock()
    profiles.get_by_project.return_value = None
    session = Mock()
    events = []
    user_session = UserSessionContext()
    user_session.set_principal(UserSessionPrincipal(
        user_id="actor-1", username="actor", display_name=None,
        role_names=frozenset(), permissions=frozenset({"budget.manage"}),
        project_access={"project-1": frozenset({"budget.manage"})},
    ))
    handler = BudgetLineCommands(
        session=session, budget_repo=repo, financial_profile_repo=profiles,
        cost_code_repo=cost_codes, task_repo=Mock(),
        clock=SimpleNamespace(now=lambda: now, today=lambda: now.date()),
        record_event=events.append,
        user_session=user_session,
    )
    handler._record_line_audit = Mock()
    return handler, budget, repo, session, events


def test_budget_line_consumes_zero_and_parent_version_without_committing():
    handler, budget, repo, session, events = _budget_handler()
    command = FinancialAddBudgetLineCommand(
        budget_id=budget.id, expected_parent_version=1, cost_code_id="cc-1",
        description="Zero estimate", amount="0.00", currency_code="USD",
    )
    response = handler.add_line(command)
    line = repo.add_line.call_args.args[0]
    assert response.budget_line_id == line.id
    assert response.budget_id == budget.id
    assert response.row_version == line.row_version
    assert line.amount == Decimal("0.00")
    assert (line.tenant_id, line.organization_id, line.project_id) == (
        "tenant-1", "org-1", "project-1",
    )
    repo.update.assert_called_once_with(budget, expected_row_version=1)
    session.flush.assert_called_once()
    session.commit.assert_not_called()
    handler._record_line_audit.assert_called_once()
    assert len(events) == 1


def test_budget_line_update_accepts_zero_and_explicitly_clears_task():
    handler, budget, repo, session, events = _budget_handler()
    line = BudgetLine.create(
        tenant_id=budget.tenant_id, organization_id=budget.organization_id,
        project_id=budget.project_id, budget_id=budget.id, cost_code_id="cc-1",
        description="Original", amount=Decimal(100), currency_code="USD",
        task_id="task-1",
    )
    repo.get_line.return_value = line
    result = handler.update_line(FinancialUpdateBudgetLineCommand(
        budget_line_id=line.id, expected_version=1, expected_parent_version=1,
        cost_code_id="cc-1", description="Zero", amount="0", currency_code="USD",
        task_id=None,
    ))
    assert result.budget_line_id == line.id
    assert result.row_version == line.row_version
    assert line.amount == Decimal(0)
    assert line.task_id is None
    repo.update_line.assert_called_once_with(line, expected_row_version=1)
    repo.update.assert_called_once_with(budget, expected_row_version=1)
    session.commit.assert_not_called()
    assert len(events) == 1


def test_budget_line_stale_parent_fails_before_writes():
    handler, budget, repo, session, events = _budget_handler()
    with pytest.raises(ConcurrencyError) as error:
        handler.add_line(FinancialAddBudgetLineCommand(
            budget_id=budget.id, expected_parent_version=99, cost_code_id="cc-1",
            description="Stale", amount="0", currency_code="USD",
        ))
    assert error.value.code == "STALE_WRITE"
    repo.add_line.assert_not_called()
    session.flush.assert_not_called()
    assert events == []


def test_budget_line_task_must_belong_to_parent_project():
    handler, budget, repo, session, events = _budget_handler()
    handler._task_repo.get.return_value = SimpleNamespace(project_id="other-project")
    with pytest.raises(BusinessRuleError) as error:
        handler.add_line(FinancialAddBudgetLineCommand(
            budget_id=budget.id, expected_parent_version=1, cost_code_id="cc-1",
            description="Wrong scope", amount="0", currency_code="USD",
            task_id="other-task",
        ))
    assert error.value.code == "PROJECT_BUDGET_LINE_TASK_PROJECT_MISMATCH"
    repo.add_line.assert_not_called()
    session.flush.assert_not_called()
    assert events == []


@pytest.mark.parametrize("method", ["submit_budget", "close_budget"])
def test_budget_actor_is_resolved_in_application(method):
    handler = object.__new__(BudgetLifecycleCommands)
    handler._user_session = None
    with pytest.raises(ValidationError) as error:
        getattr(handler, method)(FinancialVersionedBudgetCommand("budget-1", 1))
    assert error.value.code == "BUDGET_ACTOR_REQUIRED"


@pytest.mark.parametrize("value", ["NaN", "Infinity", "invalid"])
def test_rate_handler_owns_amount_validation(value):
    handler = object.__new__(RateCardLineCommandHandler)
    with pytest.raises(ValidationError) as error:
        handler.create_line(FinancialAddRateLineCommand(
            rate_card_id="card-1", expected_card_version=1, rate_type="cost",
            unit="HOUR", rate_amount=value, rate_currency="USD",
        ))
    assert error.value.code == "RATE_CARD_DECIMAL_INVALID"


def test_owned_public_entry_points_have_no_scalar_compatibility():
    from src.core.modules.project_management.application.financials.budgets.commands.approval import (
        BudgetApprovalCommands as Handler2,
    )
    from src.core.modules.project_management.application.financials.budgets.commands.lifecycle import (
        BudgetLifecycleCommands as Handler0,
    )
    from src.core.modules.project_management.application.financials.budgets.commands.lines import (
        BudgetLineCommands as Handler1,
    )
    from src.core.modules.project_management.application.financials.configuration.commands.cost_codes import (
        CostCodeCommandHandler as Handler7,
    )
    from src.core.modules.project_management.application.financials.configuration.commands.profile import (
        FinancialProfileCommandHandler as Handler6,
    )
    from src.core.modules.project_management.application.financials.forecasts.commands.approval import (
        ForecastApprovalCommands as Handler5,
    )
    from src.core.modules.project_management.application.financials.forecasts.commands.generation import (
        ForecastGenerationCommands as Handler3,
    )
    from src.core.modules.project_management.application.financials.forecasts.commands.lifecycle import (
        ForecastLifecycleCommands as Handler4,
    )
    from src.core.modules.project_management.application.financials.rate_cards.commands.cards import (
        ProjectRateCardCommandHandler as Handler8,
    )
    from src.core.modules.project_management.application.financials.rate_cards.commands.lines import (
        RateCardLineCommandHandler as Handler9,
    )
    entries = [
        Handler0.create_budget,
        Handler0.create_successor,
        Handler0.submit_budget,
        Handler0.close_budget,
        Handler0.update_budget_header,
        Handler0.delete_budget,
        Handler1.add_line,
        Handler1.update_line,
        Handler1.delete_line,
        Handler2.request_budget_approval,
        Handler3.generate_draft,
        Handler4.submit_forecast,
        Handler5.request_forecast_approval,
        Handler6.configure_profile,
        Handler6.transition_profile,
        Handler7.create_cost_code,
        Handler7.update_cost_code,
        Handler7.activate_cost_code,
        Handler7.deactivate_cost_code,
        Handler7.add_project_cost_code,
        Handler7.remove_project_cost_code,
        Handler8.create_rate_card,
        Handler8.update_rate_card,
        Handler8.deactivate_rate_card,
        Handler9.create_line,
        Handler9.update_line,
        Handler9.deactivate_line,
    ]
    for entry in entries:
        assert tuple(inspect.signature(entry).parameters) == ("self", "command")


@pytest.mark.parametrize("feature", ["budgets", "forecasts", "configuration", "rate_cards"])
def test_application_dto_packages_have_no_legacy_reexports(feature):
    package = import_module(
        f"src.core.modules.project_management.application.financials.{feature}.dto"
    )
    directory = Path(package.__file__).parent
    assert not directory.with_suffix(".py").exists()
    for kind in ("commands", "queries", "responses"):
        assert (directory / kind / "__init__.py").is_file()
    assert not any(name.endswith(("Command", "Result")) for name in vars(package))


def test_module_guard_runs_before_application_command_parsing():
    handler, budget, repo, session, events = _budget_handler()
    catalog = Mock()
    catalog.get_entitlement.return_value = SimpleNamespace(
        runtime_enabled=False, label="Project Management", lifecycle_status="inactive",
    )
    handler._module_catalog_service = catalog
    with pytest.raises(BusinessRuleError) as error:
        handler.add_line(FinancialAddBudgetLineCommand(
            budget_id=budget.id, expected_parent_version=1, cost_code_id="cc-1",
            description="Disabled", amount="not-money", currency_code="USD",
        ))
    assert error.value.code == "MODULE_DISABLED"
    repo.add_line.assert_not_called()
    session.flush.assert_not_called()
    assert events == []

