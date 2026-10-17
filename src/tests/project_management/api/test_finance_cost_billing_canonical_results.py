from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import Mock, call

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.page import CostEntryPage
from src.core.modules.project_management.application.financials.cost.entries.queries.catalog import ProjectCostEntryQueryHandler
from src.core.modules.project_management.application.financials.cost.entries.capabilities import (
    CostEntryActionCapabilities,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.cost_entry import (
    CostEntryResponse,
)
from src.core.modules.project_management.application.financials.invoicing.dto.responses.billing import (
    FinancialBillingPreparationResponse,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceType,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryKind,
    ProjectCostEntryStatus,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.ui_qml.modules.project_management.presenters.financials.cost.ledger_builder import (
    build_ledger_collection,
)

DAY = date(2026, 10, 17)
NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


def _entry() -> CostEntryResponse:
    return CostEntryResponse(
        id="entry",
        tenant_id="tenant",
        organization_id="org",
        project_id="project",
        description="Expense",
        entry_kind=ProjectCostEntryKind.ACTUAL,
        amount=Decimal("1234.5670"),
        currency_code="KWD",
        transaction_date=DAY,
        cost_code_id="code",
        source_module=FinancialSourceModule.PROJECT_MANAGEMENT,
        source_type=FinancialSourceType.MANUAL_COMMAND,
        source_id="command",
        source_revision="1",
        source_content_hash="hash",
        posting_purpose=FinancialPostingPurpose.MANUAL_ACTUAL,
        idempotency_key="key",
        source_line_id=None,
        task_id=None,
        resource_id=None,
        status=ProjectCostEntryStatus.DRAFT,
        base_amount=None,
        base_currency_code=None,
        exchange_rate=None,
        exchange_rate_date=None,
        exchange_rate_source=None,
        exchange_rate_captured_at=None,
        posting_date=None,
        financial_period_id=None,
        reverses_entry_id=None,
        reversed_by_entry_id=None,
        row_version=0,
        created_by="creator",
        created_at=NOW,
        updated_by="creator",
        updated_at=NOW,
        submitted_by=None,
        submitted_at=None,
        approved_by=None,
        approved_at=None,
        rejected_by=None,
        rejected_at=None,
        rejection_notes="",
        posted_by=None,
        posted_at=None,
        reversed_by=None,
        reversed_at=None,
        is_manual_actual=True,
        capabilities=CostEntryActionCapabilities(),
    )


def _preparation() -> FinancialBillingPreparationResponse:
    return FinancialBillingPreparationResponse(
        id="preparation",
        project_id="project",
        preparation_number="BP-1",
        billing_method="fixed_price",
        status="draft",
        period_start=DAY,
        period_end=DAY,
        line_count=0,
        total_amount="1234.5670",
        currency_code="KWD",
        row_version=0,
    )


CASES = [
    ("create_manual_actual", "cost_entry", "create_manual_entry", _entry),
    ("update_actual_draft", "cost_entry", "update_draft", _entry),
    ("submit_actual", "cost_entry", "submit", _entry),
    ("reject_actual", "cost_entry_review", "reject", _entry),
    ("post_actual", "cost_entry_posting", "post", _entry),
    ("reverse_actual", "cost_entry_posting", "reverse", _entry),
    (
        "create_billing_preparation",
        "billing_preparation",
        "create_preparation",
        _preparation,
    ),
    ("remove_draft_billing_line", "billing_source", "remove_draft_line", _preparation),
    (
        "cancel_draft_billing_preparation",
        "billing_preparation",
        "cancel_draft_preparation",
        _preparation,
    ),
    (
        "submit_billing_preparation",
        "billing_submission",
        "submit_preparation",
        _preparation,
    ),
]


@pytest.mark.parametrize(("api_method", "gate", "operation", "factory"), CASES)
def test_mutations_preserve_canonical_identity_command_and_governance(
    api_method,
    gate,
    operation,
    factory,
):
    result = factory()
    handler = Mock()
    getattr(handler, operation).return_value = result
    boundary = Mock()
    getattr(boundary, gate).side_effect = lambda callback: callback(handler)
    api = ProjectManagementFinancialsDesktopApi(finance_governance_commands=boundary)
    command = object()

    assert getattr(api, api_method)(command) is result
    assert len(boundary.mock_calls) == 1
    getattr(boundary, gate).assert_called_once()
    getattr(handler, operation).assert_called_once_with(command)
    assert getattr(handler, operation).call_args.args[0] is command
    assert result.row_version == 0
    assert not hasattr(result, "ensure_mutable")
    with pytest.raises(FrozenInstanceError):
        result.row_version = 1


@pytest.mark.parametrize(("api_method", "gate", "operation", "factory"), CASES)
def test_mutations_do_not_swallow_governance_denial(
    api_method, gate, operation, factory
):
    boundary = Mock()
    error = BusinessRuleError("Denied", code="PERMISSION_DENIED")
    getattr(boundary, gate).side_effect = error
    api = ProjectManagementFinancialsDesktopApi(finance_governance_commands=boundary)
    with pytest.raises(BusinessRuleError) as raised:
        getattr(api, api_method)(object())
    assert raised.value is error


def test_delivery_returns_canonical_read_after_governed_request():
    boundary = Mock()
    handler = Mock()
    boundary.accounting_handoff.side_effect = lambda callback: callback(handler)
    query = Mock()
    result = _preparation()
    query.get_preparation.return_value = result
    command = Mock(preparation_id="preparation", expected_version=0)
    api = ProjectManagementFinancialsDesktopApi(
        finance_governance_commands=boundary,
        billing_preparation_query=query,
    )
    events = Mock()
    events.attach_mock(handler.request, "request")
    events.attach_mock(query.get_preparation, "read")

    assert api.request_billing_delivery(command) is result
    assert events.mock_calls == [
        call.request("preparation", expected_row_version=0),
        call.read("preparation"),
    ]
    handler.request.side_effect = BusinessRuleError("Denied", code="PERMISSION_DENIED")
    query.reset_mock()
    with pytest.raises(BusinessRuleError):
        api.request_billing_delivery(command)
    query.get_preparation.assert_not_called()


def test_cost_page_preserves_rows_filters_pagination_and_create_capability():
    query = ProjectCostEntryQueryHandler(entry_repo=Mock())
    query.list_for_project = Mock()
    query.can_create_manual_entry = Mock()
    entry = _entry()
    query.list_for_project.side_effect = [([], 6), ([entry], 6)]
    query.can_create_manual_entry.return_value = True
    api = ProjectManagementFinancialsDesktopApi(cost_entry_query=query)
    page = api.list_cost_entries(
        "project",
        status="draft",
        source_module="project_management",
        offset=10,
        limit=5,
        sort_key="title",
        sort_direction="asc",
    )
    assert page.items[0] is entry
    assert page.items[0].amount is entry.amount
    assert (page.total, page.offset, page.limit) == (6, 5, 5)
    assert (page.sort_key, page.sort_direction) == ("title", "asc")
    assert page.can_create_manual_actual is True
    assert query.list_for_project.call_args_list == [
        call(
            "project",
            status="draft",
            source_module="project_management",
            offset=offset,
            limit=5,
            sort_key="title",
            sort_direction="asc",
        )
        for offset in (10, 5)
    ]
    query.can_create_manual_entry.assert_called_once_with("project")


def test_empty_cost_page_and_reader_denial():
    query = Mock()
    api = ProjectManagementFinancialsDesktopApi(cost_entry_query=query)
    page = api.list_cost_entries("", offset=5, limit=5)
    assert query.mock_calls == []
    assert page.items == ()
    assert page.can_create_manual_actual is False
    view = build_ledger_collection(page)
    assert (view.page, view.page_size, view.total) == (2, 5, 0)
    assert (
        build_ledger_collection(
            ProjectManagementFinancialsDesktopApi().list_cost_entries("project")
        ).items
        == ()
    )
    error = BusinessRuleError("Denied", code="PERMISSION_DENIED")
    query.list_page_for_project.side_effect = error
    with pytest.raises(BusinessRuleError) as raised:
        api.list_cost_entries("project")
    assert raised.value is error
    query.can_create_manual_entry.assert_not_called()


@pytest.mark.parametrize(
    ("amount", "currency", "label"),
    [
        ("1234.5670", "KWD", "KWD 1,234.567"),
        ("-125.2500", "USD", "USD -125.25"),
        ("0.0000", "USD", "USD 0.00"),
        ("1234", "JPY", "JPY 1,234"),
    ],
)
def test_ledger_formats_only_labels_and_keeps_exact_edit_amount(
    amount, currency, label
):
    entry = replace(_entry(), amount=Decimal(amount), currency_code=currency)
    page = CostEntryPage(items=(entry,), total=9, offset=5, limit=5)
    view = build_ledger_collection(page)
    row = view.items[0]
    assert (view.page, view.page_size, view.total) == (2, 5, 9)
    assert row.status_label == label
    assert Decimal(row.state["amount"]) == entry.amount
    assert "," not in row.state["amount"]
    assert row.subtitle == "Manual entry | Draft"
    assert row.supporting_text == "Project-level actual"
    assert row.meta_text == DAY.isoformat()
    assert (
        row.state["taskId"] == row.state["resourceId"] == row.state["postingDate"] == ""
    )
    assert row.state["sourceOwned"] is False
    assert row.state["rowVersion"] == 0
    assert isinstance(entry.amount, Decimal)


@pytest.mark.parametrize("allowed", [True, False])
def test_ledger_uses_server_actions_not_status_or_source_heuristics(allowed):
    actions = CostEntryActionCapabilities(
        can_edit=allowed,
        can_delete=allowed,
        can_submit=allowed,
        can_approve=allowed,
        can_reject=allowed,
        can_post=allowed,
        can_reverse=allowed,
        approval_action="request",
        read_only_reason="Server decision",
    )
    entry = replace(
        _entry(),
        capabilities=actions,
        status=ProjectCostEntryStatus.POSTED,
        source_module=FinancialSourceModule.PLATFORM_TIME,
        source_type=FinancialSourceType.TIME_ENTRY,
        is_manual_actual=False,
        posting_date=DAY,
        task_id="task",
        resource_id="resource",
    )
    row = build_ledger_collection(CostEntryPage(items=(entry,))).items[0]
    assert row.subtitle == "Platform Time | Posted"
    assert row.supporting_text == "Task task"
    assert (
        row.can_primary_action
        is row.can_secondary_action
        is row.can_tertiary_action
        is allowed
    )
    for key in (
        "canEdit",
        "canDelete",
        "canSubmit",
        "canApprove",
        "canReject",
        "canPost",
        "canReverse",
    ):
        assert row.state[key] is allowed
    assert row.state["approvalAction"] == "request"
    assert row.state["readOnlyReason"] == "Server decision"
    assert row.state["sourceOwned"] is True
    assert row.state["sourceModule"] == "platform_time"
    assert row.state["sourceType"] == "time_entry"
    assert row.state["transactionDate"] == row.state["postingDate"] == DAY.isoformat()
    assert entry.capabilities is actions
