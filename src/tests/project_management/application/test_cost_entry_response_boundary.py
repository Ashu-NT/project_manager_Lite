"""Actual Cost use cases expose detached evidence, not lifecycle aggregates."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest
from sqlalchemy import event

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.financials.cost.entries.dto.commands.manual_actuals import (
    FinancialVersionedActualCommand,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.cost_entry import (
    CostEntryResponse,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryStatus,
)
from src.tests.project_management.application.test_p37_finance_cost_entry_full_modernization import (
    _create_draft,
    _setup,
)


def test_cost_commands_and_queries_return_detached_immutable_results(services):
    _, project, cost_code, _ = _setup(services)
    draft = _create_draft(services, project, cost_code, amount="123.45")
    assert isinstance(draft, CostEntryResponse)
    assert draft.amount == Decimal("123.45")
    assert draft.base_amount is None
    assert draft.capabilities.can_edit
    assert not hasattr(draft, "post")
    with pytest.raises(FrozenInstanceError):
        draft.description = "Cannot mutate cost evidence"

    submitted = services["finance_governance_commands"].cost_entry(
        lambda handler: handler.submit(FinancialVersionedActualCommand(
            entry_id=draft.id, expected_version=draft.row_version,
        ))
    )
    assert isinstance(submitted, CostEntryResponse)
    assert submitted.status is ProjectCostEntryStatus.SUBMITTED
    assert draft.status is ProjectCostEntryStatus.DRAFT
    assert not submitted.capabilities.can_edit
    query = services["cost_entry_query"]
    assert query.get_entry(draft.id) == submitted
    rows, total = query.list_for_project(project.id)
    assert total == 1 and rows == [submitted]
    replay = _create_draft(services, project, cost_code, amount="123.45")
    assert replay == submitted


def test_cost_desktop_consumes_authorized_response_without_rebuilding_capabilities(services):
    _, project, cost_code, _ = _setup(services)
    draft = _create_draft(services, project, cost_code)
    desktop = build_desktop_api_registry(services).project_management_financials
    row = desktop.list_cost_entries(project.id).items[0]
    assert row.id == draft.id
    assert row.amount == "100.00"
    assert row.row_version == draft.row_version
    assert row.can_edit == draft.capabilities.can_edit
    assert row.can_submit == draft.capabilities.can_submit
    assert row.source_owned is False


def test_cost_response_mapping_does_not_add_per_row_queries(services, session):
    _, project, cost_code, _ = _setup(services)
    for index in range(10):
        _create_draft(services, project, cost_code, command_id=f"response-volume-{index}")
    statements = []

    def record(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(session.bind, "before_cursor_execute", record)
    try:
        query = services["cost_entry_query"]
        query.list_for_project(project.id, limit=1)
        single_count = len(statements)
        statements.clear()
        rows, total = query.list_for_project(project.id, limit=10)
        assert len(rows) == total == 10
        assert len(statements) == single_count
    finally:
        event.remove(session.bind, "before_cursor_execute", record)
