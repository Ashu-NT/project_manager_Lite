from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.financials import (
    FinancialBillingSourceOptionDto,
    FinancialBillingSourcePageDto,
)
from src.ui_qml.modules.project_management.controllers.financials.financials_lookup_mixin import (
    FinancialsLookupMixin,
)
from src.ui_qml.modules.project_management.presenters.financials.financials_workspace_presenter import (
    ProjectFinancialsWorkspacePresenter,
)


@pytest.mark.parametrize(
    ("source_type", "method", "source_field"),
    [
        ("schedule_line", "add_fixed_price_billing_source", "schedule_line_id"),
        ("approved_time", "add_approved_time_billing_source", "time_entry_id"),
        ("posted_cost", "add_cost_plus_billing_source", "cost_entry_id"),
    ],
)
def test_reader_source_identity_reaches_matching_command(source_type, method, source_field):
    api = Mock()
    api.list_eligible_billing_sources.return_value = FinancialBillingSourcePageDto(
        items=(FinancialBillingSourceOptionDto(
            source_id="evidence-id", source_type=source_type, label="Evidence",
            source_date="2026-09-01", amount="12.3456", currency_code="XAF",
        ),), total=51, page=2, page_size=25,
    )
    presenter = ProjectFinancialsWorkspacePresenter(desktop_api=api)
    host = SimpleNamespace(_financials_workspace_presenter=presenter)
    result = FinancialsLookupMixin._search_eligible_billing_sources(
        host, "project-id", "preparation-id", "Evidence", 2, 25,
    )
    assert result["ok"] is True
    assert result["hasMore"] is True
    assert result["total"] == 51
    api.list_eligible_billing_sources.assert_called_once_with(
        "project-id", "preparation-id", search="Evidence", page=2, page_size=25,
    )
    option = result["items"][0]
    assert option["amount"] == "12.3456"
    presenter.add_billing_source({
        "preparationId": "preparation-id", "version": 7,
        "sourceId": option["value"], "sourceType": option["sourceType"],
    })
    command = getattr(api, method).call_args.args[0]
    assert command.preparation_id == "preparation-id"
    assert command.expected_version == 7
    assert getattr(command, source_field) == "evidence-id"


def test_failed_lookup_is_safe_and_contains_no_stale_items():
    api = Mock()
    api.list_eligible_billing_sources.side_effect = RuntimeError("private SQL details")
    presenter = ProjectFinancialsWorkspacePresenter(desktop_api=api)
    result = FinancialsLookupMixin._search_eligible_billing_sources(
        SimpleNamespace(_financials_workspace_presenter=presenter),
        "project-id", "preparation-id", "", 1, 25,
    )
    assert result["ok"] is False
    assert "private SQL" not in result["message"]
    assert not result.get("items")


@pytest.mark.parametrize("approve", [True, False])
def test_billing_decision_reason_reaches_platform_approval(approve):
    approval = Mock()
    approval.approve_and_apply.return_value = SimpleNamespace(ok=True)
    approval.reject.return_value = SimpleNamespace(ok=True)
    presenter = ProjectFinancialsWorkspacePresenter(desktop_api=Mock(), approval_api=approval)
    presenter.decide_billing_approval("request-id", approve, "  Reviewed evidence  ")
    method = approval.approve_and_apply if approve else approval.reject
    command = method.call_args.args[0]
    assert command.request_id == "request-id"
    assert command.note == "Reviewed evidence"
