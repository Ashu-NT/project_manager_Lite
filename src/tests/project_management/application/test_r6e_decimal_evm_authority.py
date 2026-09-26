from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.core.modules.project_management.application.financials.earned_value.canonical import (
    CanonicalEarnedValueCalculator,
    EvmCalculationInput,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    EvmBaselineTaskFact,
)


def _working_days(start: date, end: date) -> int:
    return (end - start).days + 1


def _input(*, baseline_id: str | None = "baseline-1", forecast: Decimal | None = Decimal("0.30"), actual: Decimal = Decimal("0.30")) -> EvmCalculationInput:
    return EvmCalculationInput(
        project_id="project-1",
        as_of_date=date(2026, 1, 2),
        currency_code="XAF",
        baseline_id=baseline_id,
        baseline_tasks=(
            EvmBaselineTaskFact(
                task_id="task-1",
                baseline_start=date(2026, 1, 1),
                baseline_finish=date(2026, 1, 3),
                baseline_duration_days=3,
                baseline_planned_cost=Decimal("0.30"),
            ),
        ),
        task_progress=(("task-1", Decimal(50)),),
        posted_actual=actual,
        approved_forecast_etc=forecast,
    )


def test_canonical_evm_uses_exact_decimal_money_and_ratios() -> None:
    result = CanonicalEarnedValueCalculator().calculate(
        _input(), working_days_between=_working_days
    )

    assert result.availability == "available"
    assert result.BAC == Decimal("0.30")
    assert result.PV == Decimal("0.20")
    assert result.EV == Decimal("0.150")
    assert result.AC == Decimal("0.30")
    assert result.CV == Decimal("-0.150")
    assert result.SV == Decimal("-0.050")
    assert result.CPI == Decimal("0.5")
    assert result.SPI == Decimal("0.75")
    assert result.ETC == Decimal("0.30")
    assert result.EAC == Decimal("0.60")
    assert result.VAC == Decimal("-0.30")
    assert result.TCPI_to_BAC is None
    assert result.TCPI_to_EAC == Decimal("0.5")


def test_canonical_evm_distinguishes_missing_baseline_from_zero_actual() -> None:
    calculator = CanonicalEarnedValueCalculator()
    unavailable = calculator.calculate(
        _input(baseline_id=None), working_days_between=_working_days
    )
    zero_actual = calculator.calculate(
        _input(actual=Decimal(0)), working_days_between=_working_days
    )

    assert unavailable.availability == "baseline_unavailable"
    assert unavailable.BAC is None
    assert zero_actual.availability == "available"
    assert zero_actual.AC == Decimal(0)
    assert zero_actual.CPI is None


def test_canonical_evm_keeps_baseline_metrics_when_forecast_is_unavailable() -> None:
    result = CanonicalEarnedValueCalculator().calculate(
        _input(forecast=None), working_days_between=_working_days
    )

    assert result.availability == "forecast_unavailable"
    assert result.BAC == Decimal("0.30")
    assert result.EAC is None
    assert result.VAC is None
    assert result.TCPI_to_EAC is None


def test_canonical_evm_actual_is_independent_of_rate_configuration() -> None:
    result = CanonicalEarnedValueCalculator().calculate(
        _input(actual=Decimal("12.34")), working_days_between=_working_days
    )

    # The immutable input has only posted Actual truth; no rate lookup exists in EVM.
    assert result.AC == Decimal("12.34")
