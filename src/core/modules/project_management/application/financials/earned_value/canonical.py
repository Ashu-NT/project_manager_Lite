"""Canonical Decimal earned-value calculation authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

from src.core.modules.project_management.application.financials.models.finance_models import (
    EarnedValueMetrics,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    EvmBaselineTaskFact,
)


@dataclass(frozen=True, slots=True)
class EvmCalculationInput:
    """Immutable, scoped facts needed to calculate one project EVM snapshot."""

    project_id: str
    as_of_date: date
    currency_code: str
    baseline_id: str | None
    baseline_tasks: tuple[EvmBaselineTaskFact, ...]
    task_progress: tuple[tuple[str, Decimal], ...]
    posted_actual: Decimal
    approved_forecast_etc: Decimal | None


class CanonicalEarnedValueCalculator:
    """Pure Decimal EVM formula authority over immutable source facts."""

    def calculate(
        self,
        facts: EvmCalculationInput,
        *,
        working_days_between: Callable[[date, date], int],
    ) -> EarnedValueMetrics:
        if facts.baseline_id is None:
            return self._unavailable(
                facts,
                availability="baseline_unavailable",
                reason="No approved cost-loaded baseline exists for this project.",
            )
        if not facts.baseline_tasks:
            return self._unavailable(
                facts,
                availability="baseline_unavailable",
                reason="The approved baseline contains no task facts.",
            )

        cost_loaded_tasks = tuple(
            task for task in facts.baseline_tasks if task.baseline_planned_cost > 0
        )
        if not cost_loaded_tasks:
            return self._unavailable(
                facts,
                availability="baseline_unavailable",
                reason="The approved baseline has no cost-loaded task facts.",
            )
        if any(task.baseline_start is None or task.baseline_finish is None for task in cost_loaded_tasks):
            return self._unavailable(
                facts,
                availability="baseline_unavailable",
                reason="The approved cost-loaded baseline has incomplete schedule dates.",
            )

        progress_by_task = dict(facts.task_progress)
        if any(task.task_id not in progress_by_task for task in cost_loaded_tasks):
            return self._unavailable(
                facts,
                availability="progress_unavailable",
                reason="Current progress is unavailable for one or more baseline tasks.",
            )

        bac = sum((task.baseline_planned_cost for task in cost_loaded_tasks), Decimal("0"))
        pv = Decimal("0")
        ev = Decimal("0")
        for task in cost_loaded_tasks:
            assert task.baseline_start is not None
            assert task.baseline_finish is not None
            planned_fraction = self._planned_fraction(
                task.baseline_start,
                task.baseline_finish,
                facts.as_of_date,
                working_days_between,
            )
            pv += task.baseline_planned_cost * planned_fraction
            ev += task.baseline_planned_cost * self._clamp_percent(
                progress_by_task[task.task_id]
            )

        ac = facts.posted_actual
        cv = ev - ac
        sv = ev - pv
        cpi = None if ac == 0 else ev / ac
        spi = None if pv == 0 else ev / pv
        etc = facts.approved_forecast_etc
        eac = None if etc is None else ac + etc
        vac = None if eac is None else bac - eac
        tcpi_to_bac = self._ratio_or_none(bac - ev, bac - ac)
        tcpi_to_eac = None if eac is None else self._ratio_or_none(bac - ev, eac - ac)
        notes = []
        if ac == 0:
            notes.append("CPI is unavailable because posted Actual Cost is zero.")
        if pv == 0:
            notes.append("SPI is unavailable because Planned Value is zero.")
        if etc is None:
            notes.append("ETC, EAC, VAC, and TCPI(EAC) are unavailable without an approved Forecast.")
        if tcpi_to_bac is None:
            notes.append("TCPI(BAC) is unavailable because BAC minus AC is zero or negative.")

        return EarnedValueMetrics(
            as_of=facts.as_of_date,
            baseline_id=facts.baseline_id,
            currency_code=facts.currency_code,
            availability="available" if etc is not None else "forecast_unavailable",
            unavailable_reason=(
                None
                if etc is not None
                else "No approved Forecast exists for this as-of date; ETC, EAC, VAC, and TCPI(EAC) are unavailable."
            ),
            BAC=bac,
            PV=pv,
            EV=ev,
            AC=ac,
            CV=cv,
            SV=sv,
            CPI=cpi,
            SPI=spi,
            EAC=eac,
            ETC=etc,
            VAC=vac,
            TCPI_to_BAC=tcpi_to_bac,
            TCPI_to_EAC=tcpi_to_eac,
            notes=" ".join(notes) or None,
        )

    @staticmethod
    def _unavailable(
        facts: EvmCalculationInput, *, availability: str, reason: str
    ) -> EarnedValueMetrics:
        return EarnedValueMetrics(
            as_of=facts.as_of_date,
            baseline_id=facts.baseline_id,
            currency_code=facts.currency_code,
            availability=availability,
            unavailable_reason=reason,
            BAC=None,
            PV=None,
            EV=None,
            AC=None,
            CV=None,
            SV=None,
            CPI=None,
            SPI=None,
            EAC=None,
            ETC=None,
            VAC=None,
            TCPI_to_BAC=None,
            TCPI_to_EAC=None,
            notes=reason,
        )

    @staticmethod
    def _planned_fraction(
        start: date,
        finish: date,
        as_of: date,
        working_days_between: Callable[[date, date], int],
    ) -> Decimal:
        if as_of <= start:
            return Decimal("0")
        if as_of >= finish:
            return Decimal("1")
        total = max(0, working_days_between(start, finish))
        if total == 0:
            return Decimal("0")
        completed = max(0, working_days_between(start, as_of))
        return min(Decimal("1"), max(Decimal("0"), Decimal(completed) / Decimal(total)))

    @staticmethod
    def _clamp_percent(value: Decimal) -> Decimal:
        return min(Decimal("1"), max(Decimal("0"), value / Decimal("100")))

    @staticmethod
    def _ratio_or_none(numerator: Decimal, denominator: Decimal) -> Decimal | None:
        return None if denominator <= 0 else numerator / denominator


__all__ = ["CanonicalEarnedValueCalculator", "EvmCalculationInput"]
