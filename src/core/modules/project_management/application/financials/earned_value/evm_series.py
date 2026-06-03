"""EVM series builder — monthly earned value time series.

Delegates to EarnedValueCalculator for per-period metrics.
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import Callable, Optional

from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.baseline import BaselineRepository
from src.core.modules.project_management.application.financials.earned_value.evm_calculator import (
    EarnedValueCalculator,
)

from src.core.modules.project_management.application.financials.models.finance_models import (
    EvmSeriesPoint,
)


class EarnedValueSeriesCalculator:
    """
    Build a monthly EVM series for a project by calling EarnedValueCalculator
    at each period-end date.
    """

    def __init__(
        self,
        *,
        project_repo: ProjectRepository,
        baseline_repo: BaselineRepository,
        evm_calculator: EarnedValueCalculator,
    ) -> None:
        self._project_repo = project_repo
        self._baseline_repo = baseline_repo
        self._calculator = evm_calculator

    def build_series(
        self,
        project_id: str,
        *,
        baseline_id: Optional[str] = None,
        as_of: Optional[date] = None,
        freq: str = "M",
    ) -> list[EvmSeriesPoint]:
        """Return cumulative PV/EV/AC at each month-end up to as_of."""
        proj = self._project_repo.get(project_id)
        if not proj:
            return []

        if as_of is None:
            as_of = date.today()

        start = proj.start_date or as_of
        if baseline_id:
            b_tasks = self._baseline_repo.list_tasks(baseline_id)
        else:
            latest = self._baseline_repo.get_latest_for_project(project_id)
            b_tasks = self._baseline_repo.list_tasks(latest.id) if latest else []

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

        out: list[EvmSeriesPoint] = []
        for pe in points:
            evm = self._calculator.calculate(project_id, baseline_id=baseline_id, as_of=pe)
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
