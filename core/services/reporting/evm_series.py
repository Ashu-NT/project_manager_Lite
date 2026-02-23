from __future__ import annotations

import calendar
from datetime import date

from core.interfaces import BaselineRepository, ProjectRepository
from core.services.reporting.models import EvmSeriesPoint


class ReportingEvmSeriesMixin:
    _project_repo: ProjectRepository
    _baseline_repo: BaselineRepository

    def get_evm_series(
        self,
        project_id: str,
        baseline_id: str | None = None,
        as_of: date | None = None,
        freq: str = "M",  # "M" monthly
    ) -> list[EvmSeriesPoint]:
        """
        Returns cumulative PV/EV/AC at each period end (monthly by default).
        Uses get_earned_value() repeatedly (simple + consistent).
        """
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
            evm = self.get_earned_value(project_id, baseline_id=baseline_id, as_of=pe)
            PV = float(getattr(evm, "PV", 0.0) or 0.0)
            EV = float(getattr(evm, "EV", 0.0) or 0.0)
            AC = float(getattr(evm, "AC", 0.0) or 0.0)
            BAC = float(getattr(evm, "BAC", 0.0) or 0.0)
            CPI = float(getattr(evm, "CPI", 0.0) or 0.0)
            SPI = float(getattr(evm, "SPI", 0.0) or 0.0)

            out.append(EvmSeriesPoint(pe, PV, EV, AC, BAC, CPI, SPI))

        return out


def _month_end(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)
