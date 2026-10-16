from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.contracts.reads.financials.budgets.models.budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.forecasts.models.forecast_facts import (
    FinanceForecastWorkspaceFacts,
    ForecastLineFact,
    ForecastLineRequest,
    ForecastVersionFact,
    ForecastVersionRequest,
)
from src.core.modules.project_management.contracts.reads.financials.rate_cards.models.rate_facts import (
    FinanceRateWorkspaceFacts,
    RateCardFact,
    RateCardRequest,
    RateLineFact,
    RateLineRequest,
)
from src.ui_qml.modules.project_management.presenters.financials.forecasts.forecast_workspace_builder import (
    build_forecast_workspace_views,
)
from src.ui_qml.modules.project_management.presenters.financials.rate_cards.rate_workspace_builder import (
    build_rate_workspace_views,
)

NOW = datetime(2026, 1, 2, 12, tzinfo=UTC)
DAY = date(2026, 1, 2)


def _page(items=(), *, sort_key="title", sort_direction="asc"):
    return FinancePageFacts(tuple(items), 123, 2, 25, sort_key, sort_direction)


def _rates(*, amount=Decimal("0.00"), multiplier=None, can_edit=False):
    card = RateCardFact(
        "card-1",
        "Project rates",
        "project-1",
        "project",
        True,
        7,
        123,
        NOW,
        NOW,
        can_edit=can_edit,
        can_deactivate=False,
        can_add_line=can_edit,
    )
    line = RateLineFact(
        id="line-1",
        rate_card_id=card.id,
        rate_type="cost",
        origin="configured",
        selector_kind="role",
        selector_label="Engineer",
        resource_id=None,
        resource_code="",
        resource_name="",
        worker_type="",
        role="Engineer",
        skill_code="",
        department_id=None,
        department_name="",
        customer_party_id=None,
        contract_reference="",
        effective_from=None,
        effective_to=DAY,
        effective_status="expired",
        is_active=True,
        unit="HOUR",
        rate_amount=amount,
        rate_currency="EUR",
        overtime_multiplier=multiplier,
        weekend_multiplier=None,
        holiday_multiplier=None,
        version=3,
        updated_at=NOW,
        is_consumed=True,
        can_edit=can_edit,
        can_deactivate=False,
    )
    return FinanceRateWorkspaceFacts(
        card.id, card, _page([card]), _page([line]), can_edit
    )


def _forecasts(*, amount=Decimal("0.00")):
    version = ForecastVersionFact(
        id="forecast-1",
        name="Outlook",
        status="submitted",
        revision=2,
        row_version=4,
        currency_code="EUR",
        as_of_date=DAY,
        generation_mode="manual",
        line_count=123,
        total_etc=amount,
        submitted_by="user-1",
        submitted_at=NOW,
        approved_by=None,
        approved_at=None,
        notes="",
        approval_request_id="approval-1",
        can_submit=False,
        can_request_approval=False,
        can_approve=True,
        can_reject=True,
    )
    line = ForecastLineFact(
        id="forecast-line-1",
        forecast_id=version.id,
        description="",
        cost_code="LABOR",
        cost_code_name="Labor",
        task_name="Unassigned",
        wbs_code="",
        amount=amount,
        currency_code="EUR",
        source_kind="manual",
        source_type="risk",
        source_reference_type="risk",
        source_reference_id="risk-1",
        source_snapshot_at=NOW,
        period_start=None,
        period_end=None,
        row_version=5,
    )
    return FinanceForecastWorkspaceFacts(
        version.id,
        version,
        _page([version], sort_key="revision", sort_direction="desc"),
        _page([line]),
        show_generate=True,
        can_generate=False,
        generate_disabled_reason="Complete open workflow.",
    )


def test_rate_api_returns_facts_by_identity_and_passes_reader_requests():
    facts = _rates()
    query = MagicMock()
    query.get_rate_workspace.return_value = facts
    api = ProjectManagementFinancialsDesktopApi(finance_workspace_query=query)
    result = api.get_rate_workspace(
        "project-1",
        selected_rate_card_id="card-1",
        card_page=2,
        line_page=3,
        page_size=25,
        card_search="Project",
        card_scope="project",
        card_status="active",
        line_rate_type="cost",
        line_search="Engineer",
        line_status="active",
        line_effective_status="expired",
        as_of=DAY,
    )
    assert result is facts
    query.get_rate_workspace.assert_called_once_with(
        "project-1",
        selected_rate_card_id="card-1",
        card_request=RateCardRequest(
            2, 25, "title", "asc", "Project", "project", "active"
        ),
        line_request=RateLineRequest(
            3, 25, "title", "asc", "Engineer", "cost", "active", "expired", DAY
        ),
    )


def test_forecast_api_returns_facts_by_identity_and_passes_reader_requests():
    facts = _forecasts()
    query = MagicMock()
    query.get_forecast_workspace.return_value = facts
    api = ProjectManagementFinancialsDesktopApi(finance_workspace_query=query)
    assert (
        api.get_forecast_workspace(
            "project-1",
            selected_forecast_id="forecast-1",
            version_page=2,
            line_page=3,
            page_size=25,
            version_search="Outlook",
            version_status="submitted",
            generation_mode="manual",
            line_search="risk",
            line_source_type="risk",
        )
        is facts
    )
    query.get_forecast_workspace.assert_called_once_with(
        "project-1",
        selected_forecast_id="forecast-1",
        version_request=ForecastVersionRequest(
            2, 25, "revision", "desc", "Outlook", "submitted", "manual"
        ),
        line_request=ForecastLineRequest(3, 25, "title", "asc", "risk", "risk"),
    )


@pytest.mark.parametrize("can_edit", [False, True])
@pytest.mark.parametrize("multiplier", [None, Decimal(0), Decimal("1.50")])
def test_rate_presenter_formats_facts_preserving_zero_optional_values_and_permissions(
    can_edit,
    multiplier,
):
    facts = _rates(multiplier=multiplier, can_edit=can_edit)
    views = build_rate_workspace_views(
        facts, card_search="Project", line_status="active"
    )
    cards = views["rate_cards"]
    lines = views["rate_lines"]
    assert (cards.total, cards.page, cards.page_size) == (123, 2, 25)
    assert (lines.total, lines.page, lines.page_size) == (123, 2, 25)
    assert cards.items[0].can_primary_action is can_edit
    assert lines.items[0].can_primary_action is can_edit
    assert lines.items[0].can_secondary_action is False
    assert views["can_create_rate_card"] is can_edit
    assert lines.items[0].subtitle == "EUR 0.00 / hour"
    assert lines.items[0].state["amount"] == "0.00"
    assert lines.items[0].state["resourceId"] == ""
    assert lines.items[0].state["historicalLockMessage"]
    assert ("OT " in lines.items[0].meta_text) is (multiplier is not None)
    assert facts.lines.items[0].overtime_multiplier is multiplier
    assert views["selected_rate_card"].state["version"] == 7
    assert views["rate_card_search"] == "Project"
    assert views["rate_line_status"] == "active"


@pytest.mark.parametrize("amount", [Decimal("0.00"), Decimal("123456789.123456")])
def test_forecast_presenter_preserves_amount_precision_capabilities_and_filters(amount):
    facts = _forecasts(amount=amount)
    views = build_forecast_workspace_views(
        facts,
        version_search="Outlook",
        version_status="submitted",
        generation_mode="manual",
        line_search="risk",
        line_source_type="risk",
    )
    version = views["forecast_versions"].items[0]
    line = views["forecast_lines"].items[0]
    assert version.state["totalEtc"] == str(amount)
    assert line.state["amount"] == str(amount)
    assert facts.lines.items[0].amount is amount
    assert version.state["canSubmit"] is False
    assert version.state["canApprove"] is True
    assert version.state["canReject"] is True
    assert version.can_primary_action is False
    assert version.can_secondary_action is False
    assert line.can_primary_action is False
    assert line.can_secondary_action is False
    assert line.title == "Risk forecast line"
    assert line.meta_text == "Unphased | risk / risk-1"
    assert views["selected_forecast"].state["approvalRequestId"] == "approval-1"
    assert views["show_generate_forecast"] is True
    assert views["can_generate_forecast"] is False
    assert views["generate_forecast_disabled_reason"] == "Complete open workflow."
    assert views["forecast_version_sort_key"] == "revision"
    assert views["forecast_version_status"] == "submitted"
    assert views["forecast_line_source_type"] == "risk"


@pytest.mark.parametrize("project_id", ["", "project-1"])
def test_disconnected_workspaces_still_render_empty_qml_views(project_id):
    api = ProjectManagementFinancialsDesktopApi()
    rates = build_rate_workspace_views(api.get_rate_workspace(project_id))
    forecasts = build_forecast_workspace_views(api.get_forecast_workspace(project_id))
    assert rates["selected_rate_card"].id == ""
    assert rates["rate_cards"].items == ()
    assert rates["rate_lines"].empty_state == "Select a Rate Card."
    assert rates["can_create_rate_card"] is False
    assert forecasts["selected_forecast"].id == ""
    assert forecasts["forecast_versions"].items == ()
    assert forecasts["forecast_lines"].empty_state == "Select a Forecast Version."
    assert forecasts["can_generate_forecast"] is False
    assert forecasts["forecast_version_sort_key"] == "revision"
    assert forecasts["forecast_version_sort_direction"] == "desc"
