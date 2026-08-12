"""EVM series builder — monthly earned value time series.

Acquires source facts once and delegates policy/math to their owning engines.
"""

from __future__ import annotations

import calendar
from datetime import date

from src.core.modules.project_management.application.financials.costs.cost_policy_engine import (
    CostPolicyEngine,
)
from src.core.modules.project_management.application.financials.costs.labor_cost import (
    LaborCostEngine,
)
from src.core.modules.project_management.application.financials.earned_value.evm_calculator import (
    EarnedValueCalculator,
)
from src.core.modules.project_management.contracts.reads.financials.evm_series_reader import (
    EvmSeriesReader,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService

from src.core.modules.project_management.application.financials.models.finance_models import (
    EvmSeriesPoint,
)


class EarnedValueSeriesCalculator:
    """
    Build a monthly EVM series from one scoped source-fact graph.
    """

    def __init__(
        self,
        *,
        reader: EvmSeriesReader,
        tenant_context_service: TenantContextService,
        labor_engine: LaborCostEngine,
        cost_policy_engine: CostPolicyEngine,
        evm_calculator: EarnedValueCalculator,
    ) -> None:
        self._reader = reader
        self._tenant_context_service = tenant_context_service
        self._labor_engine = labor_engine
        self._cost_policy_engine = cost_policy_engine
        self._calculator = evm_calculator

    def build_series(
        self,
        project_id: str,
        *,
        baseline_id: str | None = None,
        as_of: date | None = None,
        freq: str = "M",
    ) -> list[EvmSeriesPoint]:
        """Return cumulative PV/EV/AC at each month-end up to as_of."""
        if as_of is None:
            as_of = date.today()

        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="build earned value series"
        )
        facts = self._reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            baseline_id=baseline_id,
            as_of=as_of,
        )
        if facts is None:
            return []

        start = facts.finance.project.start_date or as_of
        b_tasks = facts.baseline_tasks

        if b_tasks:
            starts = [bt.baseline_start for bt in b_tasks if bt.baseline_start]
            if starts:
                start = min(starts)

        points: list[date] = []
        cur = _month_end(start)
        end = _month_end(as_of)
        while cur <= end:
            points.append(cur)
            cur = _month_end(_add_months(cur, 1))

        calendar_starts = [start]
        calendar_ends = [end]
        if facts.finance.project.start_date:
            calendar_starts.append(facts.finance.project.start_date)
        if facts.finance.project.end_date:
            calendar_ends.append(facts.finance.project.end_date)
        calendar_starts.extend(
            task.baseline_start for task in b_tasks if task.baseline_start is not None
        )
        calendar_ends.extend(
            task.baseline_finish for task in b_tasks if task.baseline_finish is not None
        )
        working_days_between = self._calculator.prepare_working_days(
            starts_on=min(calendar_starts),
            ends_on=max(calendar_ends),
        )

        labor_by_date = dict(
            self._labor_engine.calculate_project_labor_series(
                project_id,
                as_of_dates=tuple(points),
                facts=facts.finance,
            )
        )
        out: list[EvmSeriesPoint] = []
        for pe in points:
            policy = self._cost_policy_engine.compose_from_facts_at(
                facts.finance,
                labor_by_date[pe],
                as_of=pe,
            )
            evm = self._calculator.calculate(
                project_id,
                as_of=pe,
                prepared_facts=facts,
                actual_cost=policy.totals.actual,
                approved_forecast_etc=policy.totals.forecast_etc,
                working_days_between=working_days_between,
            )
            out.append(EvmSeriesPoint(
                period_end=pe,
                PV=float(getattr(evm, "PV", 0.0) or 0.0),
                EV=float(getattr(evm, "EV", 0.0) or 0.0),
                AC=float(getattr(evm, "AC", 0.0) or 0.0),
                BAC=float(getattr(evm, "BAC", 0.0) or 0.0),
                CPI=float(getattr(evm, "CPI", 0.0) or 0.0),
                SPI=float(getattr(evm, "SPI", 0.0) or 0.0),
            ))

        return out


def _month_end(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


__all__ = ["EarnedValueSeriesCalculator"]
