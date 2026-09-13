"""EVM series builder — monthly earned value time series.

Acquires source facts once and delegates policy/math to their owning engines.
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.application.financials.earned_value.canonical import (
    CanonicalEarnedValueCalculator,
    EvmCalculationInput,
)
from src.core.modules.project_management.contracts.reads.financials.evm_series_reader import (
    EvmSeriesReader,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol

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
        calendar: CalendarProtocol,
        calculator: CanonicalEarnedValueCalculator,
    ) -> None:
        self._reader = reader
        self._tenant_context_service = tenant_context_service
        self._calendar = calendar
        self._calculator = calculator

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
        if facts.baseline_id is None or not facts.baseline_tasks:
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
        working_days_between = self._prepare_working_days(
            starts_on=min(calendar_starts), ends_on=max(calendar_ends)
        )

        out: list[EvmSeriesPoint] = []
        for pe in points:
            posted_actual = sum(
                (
                    entry.amount
                    for entry in facts.finance.ledger_entries
                    if entry.stage == "actual"
                    and entry.occurred_on is not None
                    and entry.occurred_on <= pe
                ),
                start=Decimal("0"),
            )
            approved_forecast_etc = (
                None
                if facts.finance.approved_forecast is None
                or facts.finance.approved_forecast.as_of_date > pe
                else facts.finance.approved_forecast.etc_total
            )
            evm = self._calculator.calculate(
                EvmCalculationInput(
                    project_id=project_id,
                    as_of_date=pe,
                    currency_code=facts.finance.project.currency_code,
                    baseline_id=facts.baseline_id,
                    baseline_tasks=facts.baseline_tasks,
                    task_progress=tuple(
                        (task.task_id, task.percent_complete)
                        for task in facts.finance.tasks
                    ),
                    posted_actual=posted_actual,
                    approved_forecast_etc=approved_forecast_etc,
                ),
                working_days_between=working_days_between,
            )
            out.append(EvmSeriesPoint(
                period_end=pe,
                PV=evm.PV,
                EV=evm.EV,
                AC=evm.AC,
                BAC=evm.BAC,
                CPI=evm.CPI,
                SPI=evm.SPI,
            ))

        return out

    def _prepare_working_days(
        self, *, starts_on: date, ends_on: date
    ):
        loader = getattr(self._calendar, "working_day_dates_between", None)
        if not callable(loader):
            return self._calendar.working_days_between
        working_dates = tuple(loader(starts_on, ends_on))

        def _count(start: date, end: date) -> int:
            if end < start:
                return 0
            return sum(1 for day in working_dates if start <= day <= end)

        return _count


def _month_end(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


__all__ = ["EarnedValueSeriesCalculator"]
