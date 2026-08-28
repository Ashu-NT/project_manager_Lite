"""Serialization for the authoritative Finance overview read."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import format_money
from src.core.modules.project_management.api.desktop.financials.models.snapshots import FinancialOverviewDto
from src.core.platform.finance.money import canonical_decimal_text


def serialize_overview(project_id: str, facts) -> FinancialOverviewDto:
    currency = (facts.currency_code or "").strip().upper() or None
    has_approved_budget = bool(facts.approved_budget_id)

    def optional_amount(value):
        return None if value is None else canonical_decimal_text(value)

    def optional_label(value, unavailable: str):
        return unavailable if value is None else format_money(value, currency)

    return FinancialOverviewDto(
        project_id=project_id,
        project_currency=currency,
        as_of=facts.as_of,
        budget=canonical_decimal_text(facts.approved_budget),
        budget_label=format_money(facts.approved_budget, currency) if has_approved_budget else "Not approved",
        actual=canonical_decimal_text(facts.posted_actual),
        actual_label=format_money(facts.posted_actual, currency),
        committed=canonical_decimal_text(facts.open_commitment),
        committed_label=format_money(facts.open_commitment, currency),
        available=canonical_decimal_text(facts.available_after_commitment),
        available_label=format_money(facts.available_after_commitment, currency) if has_approved_budget else "Not available",
        forecast_etc=optional_amount(facts.forecast_etc),
        forecast_etc_label=optional_label(facts.forecast_etc, "Not approved"),
        estimate_at_completion=optional_amount(facts.estimate_at_completion),
        estimate_at_completion_label=optional_label(facts.estimate_at_completion, "Not available"),
        variance_at_completion=optional_amount(facts.variance_at_completion),
        variance_at_completion_label=optional_label(facts.variance_at_completion, "Not available"),
        approved_budget_id=facts.approved_budget_id or "",
        approved_budget_revision=facts.approved_budget_revision,
        approved_budget_at=facts.approved_budget_at,
        approved_forecast_id=facts.approved_forecast_id or "",
        approved_forecast_revision=facts.approved_forecast_revision,
        approved_forecast_as_of=facts.approved_forecast_as_of,
    )


def empty_overview(*, project_id: str) -> FinancialOverviewDto:
    return FinancialOverviewDto(
        project_id=project_id,
        project_currency=None,
        as_of=None,
        budget="0",
        budget_label="0.00",
        actual="0",
        actual_label="0.00",
        committed="0",
        committed_label="0.00",
        available="0",
        available_label="0.00",
        forecast_etc=None,
        forecast_etc_label="Not approved",
        estimate_at_completion=None,
        estimate_at_completion_label="Not available",
        variance_at_completion=None,
        variance_at_completion_label="Not available",
    )


__all__ = ["empty_overview", "serialize_overview"]
