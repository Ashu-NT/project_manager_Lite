from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.api.desktop.common.financial_formatting import format_money
from src.core.modules.project_management.api.desktop.financials.models.performance import (
    FinancialCostPhasingDto,
    FinancialEvmDto,
    FinancialPerformanceMetricDto,
    FinancialReportDefinitionDto,
    FinancialReportsDto,
    FinancialVarianceWorkspaceDto,
)
from src.core.modules.project_management.api.desktop.financials.models.snapshots import FinancialPeriodRowDto
from src.core.modules.project_management.api.desktop.financials.serializers.baseline_variance_serializer import (
    serialize_baseline_version,
    serialize_variance_record,
)
from src.core.platform.finance.money import canonical_decimal_text


def _evm_float_text(value: float | None) -> str | None:
    # Presentation-only adaptation of the pre-existing EVM float authority.
    return None if value is None else canonical_decimal_text(Decimal(str(value)))


def _evm_money_metric(code, label, value, currency, supporting_text):
    text = _evm_float_text(value)
    return FinancialPerformanceMetricDto(
        code=code,
        label=label,
        value=text,
        value_label="Not available" if text is None else format_money(Decimal(text), currency),
        supporting_text=supporting_text,
        availability="unavailable" if text is None else "available",
    )


def _evm_ratio_metric(code, label, value, supporting_text):
    text = _evm_float_text(value)
    return FinancialPerformanceMetricDto(
        code=code,
        label=label,
        value=text,
        value_label="Not available" if text is None else text,
        supporting_text=supporting_text,
        availability="unavailable" if text is None else "available",
    )


def serialize_performance_evm(fact) -> FinancialEvmDto:
    currency = str(fact.currency_code or "").strip().upper()
    return FinancialEvmDto(
        project_id=fact.project_id,
        as_of_date=fact.as_of_date,
        availability=fact.availability,
        unavailable_reason=fact.unavailable_reason,
        baseline_id=fact.baseline_id or "",
        budget_revision=fact.budget_revision,
        forecast_revision=fact.forecast_revision,
        forecast_as_of=fact.forecast_as_of,
        currency_code=currency,
        calculation_precision=fact.calculation_precision,
        metrics=(
            _evm_money_metric("bac", "Budget at Completion (BAC)", fact.bac, currency, "Cost-loaded baseline authority."),
            _evm_money_metric("pv", "Planned Value (PV)", fact.pv, currency, "Baseline cost by planned completion at the as-of date."),
            _evm_money_metric("ev", "Earned Value (EV)", fact.ev, currency, "Baseline cost weighted by authoritative task progress."),
            _evm_money_metric("ac", "Actual Cost (AC)", fact.ac, currency, "Canonical posted Project Cost Entry authority."),
            _evm_ratio_metric("cpi", "Cost Performance Index (CPI)", fact.cpi, "EV / AC; unavailable when AC is zero."),
            _evm_ratio_metric("spi", "Schedule Performance Index (SPI)", fact.spi, "EV / PV; unavailable when PV is zero."),
            _evm_money_metric("etc", "Estimate to Complete (ETC)", fact.etc, currency, "Approved Forecast ETC authority."),
            _evm_money_metric("eac", "Estimate at Completion (EAC)", fact.eac, currency, "Existing authority: AC + approved Forecast ETC."),
            _evm_money_metric("vac", "Variance at Completion (VAC)", fact.vac, currency, "Existing authority: BAC - EAC; positive is favorable."),
            _evm_ratio_metric("tcpi_bac", "TCPI to BAC", fact.tcpi_bac, "Required cost efficiency to meet BAC."),
            _evm_ratio_metric("tcpi_eac", "TCPI to EAC", fact.tcpi_eac, "Required cost efficiency to meet EAC."),
        ),
        notes=fact.notes,
    )


def serialize_performance_variance(facts) -> FinancialVarianceWorkspaceDto:
    metrics = tuple(
        FinancialPerformanceMetricDto(
            code=item.metric_code,
            label=item.display_name,
            value=None if item.value is None else canonical_decimal_text(item.value),
            value_label="Not available" if item.value is None else format_money(item.value, item.currency_code),
            supporting_text=" | ".join(part for part in (item.sign_convention, item.source_revision, item.unavailable_reason) if part),
            availability=item.availability,
            tone=(
                "danger" if item.metric_code == "budget_pressure" and (item.value or 0) > 0
                else "success" if item.metric_code == "vac" and (item.value or 0) > 0
                else "default"
            ),
        )
        for item in facts.metrics
    )
    return FinancialVarianceWorkspaceDto(
        project_id=facts.project_id,
        as_of_date=facts.as_of_date,
        currency_code=facts.currency_code,
        budget_revision=facts.budget_revision,
        forecast_revision=facts.forecast_revision,
        forecast_as_of=facts.forecast_as_of,
        selected_baseline_id=facts.selected_baseline_id,
        selected_baseline_label=facts.selected_baseline_label,
        compared_baseline_id=facts.compared_baseline_id,
        baselines=tuple(serialize_baseline_version(item) for item in facts.baseline_versions),
        records=tuple(serialize_variance_record(item) for item in facts.baseline_records),
        metrics=metrics,
    )


def serialize_cost_phasing(facts) -> FinancialCostPhasingDto:
    return FinancialCostPhasingDto(
        project_id=facts.project_id,
        as_of_date=facts.as_of_date,
        date_from=facts.date_from,
        date_to=facts.date_to,
        granularity=facts.granularity,
        currency_code=facts.currency_code,
        approved_budget_id=facts.approved_budget_id or "",
        approved_budget_revision=facts.approved_budget_revision,
        approved_forecast_id=facts.approved_forecast_id or "",
        approved_forecast_revision=facts.approved_forecast_revision,
        approved_forecast_as_of=facts.approved_forecast_as_of,
        periods=tuple(
            FinancialPeriodRowDto(
                period_key=item.period_key,
                planned=canonical_decimal_text(item.planned_cost),
                planned_label=format_money(item.planned_cost, item.currency_code),
                committed=canonical_decimal_text(item.open_commitment),
                committed_label=format_money(item.open_commitment, item.currency_code),
                actual=canonical_decimal_text(item.posted_actual),
                actual_label=format_money(item.posted_actual, item.currency_code),
                forecast=canonical_decimal_text(item.forecast_cost),
                forecast_label=format_money(item.forecast_cost, item.currency_code),
                exposure=canonical_decimal_text(item.exposure),
                exposure_label=format_money(item.exposure, item.currency_code),
            )
            for item in facts.periods
        ),
    )


def serialize_performance_reports(facts) -> FinancialReportsDto:
    return FinancialReportsDto(
        project_id=facts.project_id,
        as_of_date=facts.as_of_date,
        currency_code=facts.currency_code,
        budget_revision=facts.budget_revision,
        forecast_revision=facts.forecast_revision,
        forecast_as_of=facts.forecast_as_of,
        definitions=tuple(
            FinancialReportDefinitionDto(
                report_code=item.report_code,
                display_name=item.display_name,
                formats=item.formats,
                authority_label=item.authority_label,
                requires_sensitive_finance=item.requires_sensitive_finance,
                requires_profitability=item.requires_profitability,
            )
            for item in facts.definitions
        ),
    )


__all__ = ["serialize_cost_phasing", "serialize_performance_evm", "serialize_performance_reports", "serialize_performance_variance"]
