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
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.financial_changes.models.change_facts import (
    FinanceChangeWorkspaceFacts,
    FinancialChangeDetailFact,
    FinancialChangeImpactFact,
    FinancialChangeImpactQuery,
    FinancialChangeRequestQuery,
    FinancialChangeSummaryFact,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.ui_qml.modules.project_management.presenters.financials.financial_changes.change_workspace_builder import (
    build_change_workspace_views,
)

NOW = datetime(2026, 10, 16, 12, tzinfo=UTC)
DAY = date(2026, 10, 16)
FILTERS = {
    "change_search": "scope",
    "change_status": "pending_approval",
    "change_approval_status": "pending",
    "change_applied_state": "not_applied",
    "impact_search": "task",
    "impact_type": "schedule",
    "impact_applied_state": "applied",
}


def _detail() -> FinancialChangeDetailFact:
    return FinancialChangeDetailFact(
        id="change",
        title="Scope",
        status="pending_approval",
        revision=0,
        row_version=0,
        reason="Reason",
        description="",
        effective_date=DAY,
        currency_code="USD",
        created_by="creator",
        created_at=NOW,
        updated_at=NOW,
        base_budget_id="budget",
        base_budget_revision=0,
        current_budget_id="current",
        current_budget_revision=1,
        base_budget_is_current=False,
        base_forecast_id=None,
        base_forecast_revision=None,
        current_forecast_id=None,
        current_forecast_revision=None,
        base_forecast_is_current=None,
        approval_request_id="approval",
        approval_status="PENDING",
        approval_requested_by="requester",
        approval_requested_at=NOW,
        approval_decided_by="",
        approval_decided_at=None,
        approval_decision_note="",
        submitted_by="submitter",
        submitted_at=NOW,
        applied_by=None,
        applied_at=None,
        applied_budget_id=None,
        applied_budget_revision=None,
        applied_forecast_id=None,
        applied_forecast_revision=None,
        applied_schedule_count=0,
        rejected_by=None,
        rejected_at=None,
        rejection_notes="",
        impact_count=9,
    )


def _impact() -> FinancialChangeImpactFact:
    return FinancialChangeImpactFact(
        id="impact",
        change_request_id="change",
        impact_type="budget",
        description="Increase",
        amount=Decimal("0.0000"),
        currency_code="USD",
        cost_code_id=None,
        cost_code="",
        cost_code_name="",
        task_id=None,
        task_name="",
        wbs_code="",
        target_line_id=None,
        target_task_version=None,
        schedule_start=None,
        schedule_finish=None,
        applied_reference_type=None,
        applied_reference_id=None,
        row_version=0,
        created_at=NOW,
        updated_at=NOW,
    )


def _workspace() -> FinanceChangeWorkspaceFacts:
    summary = FinancialChangeSummaryFact(
        id="change",
        title="Scope",
        status="pending_approval",
        revision=0,
        row_version=0,
        effective_date=DAY,
        currency_code="USD",
        reason="Reason",
        created_by="creator",
        base_budget_id="budget",
        base_budget_revision=0,
        base_forecast_id=None,
        base_forecast_revision=None,
        approval_status="",
        impact_count=9,
        created_at=NOW,
        submitted_at=NOW,
        applied_at=None,
    )
    return FinanceChangeWorkspaceFacts(
        selected_change_id="change",
        selected_change=_detail(),
        changes=FinancePageFacts((summary,), 12, 2, 5, "title", "asc"),
        impacts=FinancePageFacts((_impact(),), 9, 3, 5, "subtitle", "desc"),
        can_create=True,
    )


def test_api_returns_canonical_workspace_identity_and_forwards_queries():
    query = Mock()
    source = _workspace()
    query.get_change_workspace.return_value = source
    api = ProjectManagementFinancialsDesktopApi(finance_workspace_query=query)

    result = api.get_change_workspace(
        "project",
        selected_change_id="change",
        change_page=2,
        impact_page=3,
        page_size=5,
        change_sort_key="title",
        change_sort_direction="asc",
        impact_sort_key="subtitle",
        impact_sort_direction="desc",
        **FILTERS,
    )

    assert result is source
    query.get_change_workspace.assert_called_once_with(
        "project",
        selected_change_id="change",
        change_request=FinancialChangeRequestQuery(
            page=2,
            page_size=5,
            sort_key="title",
            sort_direction="asc",
            search="scope",
            status="pending_approval",
            approval_status="pending",
            applied_state="not_applied",
        ),
        impact_request=FinancialChangeImpactQuery(
            page=3,
            page_size=5,
            sort_key="subtitle",
            sort_direction="desc",
            search="task",
            impact_type="schedule",
            applied_state="applied",
        ),
    )
    assert isinstance(result.impacts.items[0].amount, Decimal)
    assert not hasattr(result.selected_change, "ensure_mutable")


@pytest.mark.parametrize("project_id", ["", "project"])
def test_unconfigured_api_returns_canonical_empty_workspace(project_id):
    source = ProjectManagementFinancialsDesktopApi().get_change_workspace(project_id)
    assert isinstance(source, FinanceChangeWorkspaceFacts)
    assert source.selected_change is None
    views = build_change_workspace_views(source)
    assert views["selected_change"].id == ""
    assert views["financial_changes"].items == ()
    assert views["financial_change_impacts"].page_size == 50
    assert views["financial_change_impacts"].empty_state == "Select a Change Request."
    assert views["can_create_change"] is False


def test_empty_project_skips_query_and_reader_denial_is_not_swallowed():
    query = Mock()
    api = ProjectManagementFinancialsDesktopApi(finance_workspace_query=query)
    api.get_change_workspace("")
    assert query.mock_calls == []
    error = BusinessRuleError("Denied", code="PERMISSION_DENIED")
    query.get_change_workspace.side_effect = error
    with pytest.raises(BusinessRuleError) as raised:
        api.get_change_workspace("hidden")
    assert raised.value is error


def test_presenter_preserves_filters_pages_summary_and_selected_detail():
    source = _workspace()
    views = build_change_workspace_views(source, **FILTERS)
    assert all(views[key] == value for key, value in FILTERS.items())
    assert views["selected_change_id"] == "change"
    assert views["can_create_change"] is True
    changes = views["financial_changes"]
    impacts = views["financial_change_impacts"]
    assert (changes.page, changes.page_size, changes.total) == (2, 5, 12)
    assert (impacts.page, impacts.page_size, impacts.total) == (3, 5, 9)
    assert (views["change_sort_key"], views["impact_sort_direction"]) == (
        "title",
        "desc",
    )
    summary = changes.items[0]
    assert summary.subtitle == "Revision 0 | Effective 2026-10-16"
    assert summary.supporting_text == "9 impacts | Approval: Not requested"
    assert summary.state["budgetBase"] == "Revision 0"
    assert summary.state["forecastBase"] == "Not available"
    assert summary.state["version"] == 0
    assert summary.can_primary_action is summary.can_secondary_action is False
    detail = views["selected_change"]
    assert detail.description == "Reason"
    fields = {field.label: field for field in detail.fields}
    assert fields["Budget base"].value == "Revision 0 | Stale"
    assert fields["Budget base"].supporting_text == "Current approved: revision 1"
    assert fields["Forecast base"].value == "Not captured"
    assert fields["Forecast base"].supporting_text == "No current approved version"
    assert fields["Approval"].supporting_text == "approval"
    assert fields["Decision"].value == "Not decided"
    assert fields["Applied Budget"].value == "Not available"
    assert fields["Schedule applications"].value == "0"
    assert fields["Impacts"].value == "9"
    assert fields["Row version"].value == "0"
    assert detail.state["baseBudgetIsCurrent"] is False
    assert detail.state["baseForecastIsCurrent"] is None


@pytest.mark.parametrize("allowed", [False, True])
def test_presenter_uses_server_capabilities_without_deriving_from_status(allowed):
    source = _workspace()
    selected = replace(
        _detail(),
        can_edit=allowed,
        can_add_impact=allowed,
        can_submit=allowed,
        can_approve=allowed,
        can_reject=allowed,
    )
    impact = replace(_impact(), can_edit=allowed, can_remove=not allowed)
    source = replace(
        source,
        selected_change=selected,
        can_create=not allowed,
        impacts=replace(source.impacts, items=(impact,)),
    )
    views = build_change_workspace_views(source)
    state = views["selected_change"].state
    assert all(
        state[key] is allowed
        for key in ("canEdit", "canAddImpact", "canSubmit", "canApprove", "canReject")
    )
    assert views["can_create_change"] is not allowed
    impact_state = views["financial_change_impacts"].items[0].state
    assert impact_state["canEdit"] is allowed
    assert impact_state["canRemove"] is not allowed


@pytest.mark.parametrize("impact_type", ["budget", "forecast"])
@pytest.mark.parametrize(
    ("amount", "currency", "label"),
    [
        (Decimal("0.0000"), "USD", "USD 0.00"),
        (Decimal("-125.2500"), "USD", "USD -125.25"),
        (Decimal("0"), "JPY", "JPY 0"),
        (Decimal("1.234"), "KWD", "KWD 1.234"),
        (Decimal("0"), None, "0.00"),
    ],
)
def test_monetary_impacts_preserve_decimal_scale_zero_sign_and_currency(
    impact_type,
    amount,
    currency,
    label,
):
    source = _workspace()
    impact = replace(
        _impact(), impact_type=impact_type, amount=amount, currency_code=currency
    )
    source = replace(source, impacts=replace(source.impacts, items=(impact,)))
    view = build_change_workspace_views(source)["financial_change_impacts"].items[0]
    assert view.subtitle == label
    assert view.state["amount"] == str(amount)
    assert view.state["currency"] == (currency or "")
    assert view.state["costCodeId"] == view.state["taskId"] == ""
    assert view.state["targetTaskVersion"] == view.state["version"] == 0
    assert view.meta_text == "Not applied"
    assert view.supporting_text == "New financial line"
    assert source.impacts.items[0].amount is amount


def test_schedule_impacts_keep_none_dates_targets_and_applied_reference():
    source = _workspace()
    impact = replace(
        _impact(),
        impact_type="schedule",
        task_id="task",
        task_name="Commission",
        wbs_code="1.2",
        target_task_version=7,
        schedule_finish=DAY,
        applied_reference_type="task",
        applied_reference_id="task",
    )
    source = replace(source, impacts=replace(source.impacts, items=(impact,)))
    view = build_change_workspace_views(source)["financial_change_impacts"].items[0]
    assert view.subtitle == "Unchanged to 2026-10-16"
    assert view.supporting_text == "1.2 Commission | Task version 7"
    assert view.meta_text == "Task: task"
    assert view.state["scheduleStart"] == ""
    assert view.state["scheduleFinish"] == "2026-10-16"
    assert view.state["targetTaskVersion"] == 7


def test_no_selected_detail_does_not_fabricate_selection_or_capabilities():
    source = replace(
        _workspace(),
        selected_change=None,
        selected_change_id="",
        impacts=FinancePageFacts((), 0, 4, 5, "title", "asc"),
    )
    views = build_change_workspace_views(source)
    assert views["selected_change_id"] == ""
    assert views["selected_change"].fields == ()
    assert views["selected_change"].state == {}
    assert views["financial_change_impacts"].page == 4
