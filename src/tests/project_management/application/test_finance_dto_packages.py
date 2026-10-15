"""The Finance DTO package split preserves application payload contracts."""

from dataclasses import FrozenInstanceError, fields
from datetime import date
from decimal import Decimal
from importlib import import_module

import pytest

from src.core.modules.project_management.application.financials.cost.dto.responses.cost_breakdown import (
    CostSourceRow,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.commands.actual_posting import (
    FinancialPostActualCommand,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.commands.manual_actuals import (
    FinancialCreateManualActualCommand,
)
from src.core.modules.project_management.application.financials.financial_changes.dto.commands.change_impacts import (
    FinancialChangeImpactCommand,
    FinancialUpdateChangeImpactCommand,
)
from src.core.modules.project_management.application.financials.invoicing.dto.commands.billing_profile import (
    FinancialCreateBillingProfileCommand,
)


def test_manual_actual_zero_and_posting_zero_exchange_rate_are_preserved():
    today = date(2026, 1, 1)
    command = FinancialCreateManualActualCommand(
        project_id="project", command_id="command", description="Zero actual",
        amount=Decimal(0), currency_code="EUR", transaction_date=today,
        cost_code_id="cost-code",
    )
    assert command.amount == Decimal(0)
    assert command.entry_kind == "actual"
    with pytest.raises(FrozenInstanceError):
        command.description = "Changed"
    posting = FinancialPostActualCommand("entry", 7, today, exchange_rate=Decimal(0))
    assert posting.expected_version == 7
    assert posting.exchange_rate == Decimal(0)


def test_billing_defaults_and_change_impact_inheritance_are_unchanged():
    profile = FinancialCreateBillingProfileCommand("project", "contract", Decimal(0))
    assert profile.cost_plus_markup_percent == Decimal(0)
    assert profile.payment_terms_days == 30
    assert profile.retention_years == 7
    impact = FinancialUpdateChangeImpactCommand(
        change_id="change", expected_change_version=2, impact_type="cost",
        description="Impact", impact_id="impact", expected_impact_version=3,
    )
    assert isinstance(impact, FinancialChangeImpactCommand)
    assert impact.amount == "0"
    assert impact.schedule_start == ""
    assert "expected_change_version" in {field.name for field in fields(impact)}


def test_mutable_response_contract_remains_mutable():
    row = CostSourceRow("source", "Source", Decimal(0), Decimal(0), Decimal(0), Decimal(0))
    row.actual = Decimal("1.25")
    assert row.actual == Decimal("1.25")


@pytest.mark.parametrize("feature", [
    "", "cost", "cost.entries", "invoicing", "financial_changes", "revenue",
    "earned_value", "governance.successors",
])
def test_dto_package_does_not_reexport_old_flat_payloads(feature):
    prefix = "src.core.modules.project_management.application.financials"
    package = import_module(prefix + ("." + feature if feature else "") + ".dto")
    assert not any(isinstance(value, type) for value in vars(package).values())
