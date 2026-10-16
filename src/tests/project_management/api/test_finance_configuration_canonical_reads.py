from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.contracts.reads.financials.budgets.models.budget_facts import (
    BudgetLineFact,
    BudgetVersionFact,
    BudgetVersionPageFacts,
    FinanceBudgetWorkspaceFacts,
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.configuration.models.setup_facts import (
    FinanceSetupFacts,
    FinanceSetupWorkspaceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.planned_costs.models.planned_cost_facts import (
    FinancePlannedCostWorkspaceFacts,
    PlannedCostLineFact,
    PlannedCostVersionFact,
)
from src.ui_qml.modules.project_management.presenters.financials.governance.configuration_builder import (
    build_finance_configuration_views,
)


def _setup() -> FinanceSetupWorkspaceFacts:
    return FinanceSetupWorkspaceFacts(
        profile=FinanceSetupFacts(
            "project",
            "USD",
            "draft",
            "time_and_materials",
            "warn",
            "open",
            None,
            None,
            False,
            True,
            None,
            "",
            0,
        ),
        cost_codes=FinancePageFacts((), 9, 2, 5, "name", "desc"),
        restrictions=FinancePageFacts((), 0, 1, 5, "code", "asc"),
        can_edit_profile=True,
        can_transition_profile=False,
        can_create_cost_code=True,
    )


def _budget() -> FinanceBudgetWorkspaceFacts:
    return FinanceBudgetWorkspaceFacts(
        selected_budget_id="budget",
        versions=BudgetVersionPageFacts(
            (
                BudgetVersionFact(
                    "budget",
                    "Initial",
                    "draft",
                    1,
                    0,
                    None,
                    "USD",
                    1,
                    Decimal("0.00"),
                    None,
                    None,
                    None,
                    None,
                    "",
                    can_edit=True,
                ),
            ),
            8,
            2,
            5,
            "name",
            "asc",
        ),
        lines=FinancePageFacts(
            (
                BudgetLineFact(
                    "line",
                    "budget",
                    "Initial",
                    1,
                    "draft",
                    0,
                    "",
                    "CODE",
                    "",
                    "code",
                    None,
                    "Project",
                    "",
                    Decimal("0.00"),
                    "USD",
                    can_edit=True,
                    can_delete=False,
                ),
            ),
            12,
            3,
            5,
            "amount",
            "asc",
        ),
        show_create_version=True,
        create_version_disabled_reason="An open version exists.",
    )


def _planned() -> FinancePlannedCostWorkspaceFacts:
    return FinancePlannedCostWorkspaceFacts(
        selected_version_id="snapshot",
        versions=FinancePageFacts(
            (
                PlannedCostVersionFact(
                    "snapshot",
                    0,
                    "draft",
                    "USD",
                    date(2026, 10, 16),
                    "user",
                    datetime(2026, 10, 16, tzinfo=UTC),
                    1,
                    Decimal("0"),
                    Decimal("0.00"),
                    False,
                    True,
                    False,
                    1,
                    0,
                    1,
                ),
            ),
            7,
            2,
            5,
            "asOf",
            "asc",
        ),
        lines=FinancePageFacts(
            (
                PlannedCostLineFact(
                    "line",
                    "snapshot",
                    0,
                    "draft",
                    "Task",
                    "",
                    "Resource",
                    "R01",
                    "CODE",
                    "",
                    Decimal("0"),
                    Decimal("0.00"),
                    Decimal("0.00"),
                    "USD",
                    "rate",
                    0,
                ),
            ),
            11,
            3,
            5,
            "amount",
            "desc",
        ),
    )


@pytest.mark.parametrize(
    ("method", "query_method", "source", "kwargs"),
    [
        (
            "get_financial_setup_workspace",
            "get_setup_workspace",
            _setup(),
            {"cost_code_page": 2, "restriction_page": 3},
        ),
        (
            "get_budget_workspace",
            "get_budget_workspace",
            _budget(),
            {"selected_budget_id": "budget", "version_page": 2, "line_page": 3},
        ),
        (
            "get_planned_cost_workspace",
            "get_planned_cost_workspace",
            _planned(),
            {"selected_version_id": "snapshot", "version_page": 2, "line_page": 3},
        ),
    ],
)
def test_api_returns_reader_result_without_cloning(
    method, query_method, source, kwargs
):
    query = Mock()
    reader = getattr(query, query_method)
    reader.return_value = source
    api = ProjectManagementFinancialsDesktopApi(finance_workspace_query=query)

    assert getattr(api, method)("project", page_size=5, **kwargs) is source
    assert reader.call_args.args == ("project",)
    requests = reader.call_args.kwargs
    first, second = (
        ("cost_code_request", "restriction_request")
        if query_method == "get_setup_workspace"
        else ("version_request", "line_request")
    )
    assert requests[first].page == 2
    assert requests[second].page == 3
    assert requests[first].page_size == requests[second].page_size == 5


def test_setup_presenter_keeps_profile_none_dates_zero_version_and_capabilities():
    views = build_finance_configuration_views(_setup())
    fields = {field.label: field.value for field in views["profile"].fields}
    assert fields["Financial period"] == "Not set to Not set"
    assert fields["Default cost code"] == "Not set"
    assert fields["Version"] == "0"
    assert fields["Funding"] == "Not funded"
    assert views["profile"].state["canEdit"] is True
    assert views["profile"].state["canTransition"] is False
    assert views["profile"].state["defaultCostCodeId"] == ""
    assert views["can_create_cost_code"] is True
    assert (
        views["cost_codes"].page,
        views["cost_codes"].page_size,
        views["cost_codes"].total,
    ) == (2, 5, 9)
    assert views["cost_code_sort_key"] == "name"


def test_budget_presenter_keeps_decimal_zero_none_ids_and_capabilities():
    source = _budget()
    views = build_finance_configuration_views(source)
    line = views["budget_lines"].items[0]
    assert line.state["amount"] == "0.00"
    assert line.state["amountLabel"] == "USD 0.00"
    assert line.state["taskId"] == ""
    assert line.state["rowVersion"] == 0
    assert line.state["canEdit"] is True
    assert line.state["canDelete"] is False
    assert line.can_primary_action is False
    assert views["budget_versions"].items[0].state["predecessorBudgetId"] == ""
    assert views["budget_lines"].total == 12
    assert views["budget_lines"].page == 3
    assert views["show_create_budget_version"] is True
    assert views["can_create_budget_version"] is False
    assert views["create_budget_version_disabled_reason"] == "An open version exists."
    assert source.lines.items[0].amount == Decimal("0.00")


def test_planned_presenter_keeps_zero_rates_hours_and_completeness():
    views = build_finance_configuration_views(_planned())
    version = views["planned_cost_versions"].items[0]
    line = views["planned_cost_lines"].items[0]
    assert version.state["totalAmountLabel"] == "USD 0.00"
    assert version.state["totalHoursLabel"] == "0.0 h"
    assert version.state["ratesComplete"] is False
    assert version.state["allocationsComplete"] is True
    assert line.supporting_text == "0.0 h x USD 0.00 = USD 0.00"
    assert line.state["resourceCode"] == "R01"
    assert views["selected_planned_cost_version_id"] == "snapshot"
    assert views["planned_cost_lines"].total == 11
    assert views["planned_cost_line_sort_key"] == "amount"


@pytest.mark.parametrize(
    ("currency", "amount", "label"),
    [("JPY", Decimal("0"), "JPY 0"), ("KWD", Decimal("1.234"), "KWD 1.234")],
)
def test_budget_presenter_preserves_currency_minor_units(currency, amount, label):
    source = _budget()
    line = replace(source.lines.items[0], amount=amount, currency_code=currency)
    source = replace(source, lines=replace(source.lines, items=(line,)))

    view = build_finance_configuration_views(source)["budget_lines"].items[0]

    assert view.state["amountLabel"] == label
    assert source.lines.items[0].amount is amount


@pytest.mark.parametrize(
    ("method", "query_method"),
    [("get_financial_setup_workspace", "get_setup_workspace"),
     ("get_budget_workspace", "get_budget_workspace"),
     ("get_planned_cost_workspace", "get_planned_cost_workspace")],
)
def test_api_does_not_swallow_reader_authorization_errors(method, query_method):
    query = Mock()
    error = PermissionError("reader denied access")
    getattr(query, query_method).side_effect = error
    api = ProjectManagementFinancialsDesktopApi(finance_workspace_query=query)

    with pytest.raises(PermissionError) as raised:
        getattr(api, method)("hidden-project")

    assert raised.value is error


@pytest.mark.parametrize("with_query", [False, True])
def test_empty_api_reads_render_existing_empty_views_without_query(with_query):
    query = Mock() if with_query else None
    api = ProjectManagementFinancialsDesktopApi(finance_workspace_query=query)
    for method in (
        "get_financial_setup_workspace",
        "get_budget_workspace",
        "get_planned_cost_workspace",
    ):
        views = build_finance_configuration_views(getattr(api, method)(""))
        assert views["profile"].status_label == "Not configured"
        assert views["budget_versions"].items == ()
        assert views["planned_cost_lines"].page_size == 50
        assert views["can_create_cost_code"] is False
    if query is not None:
        assert query.mock_calls == []
