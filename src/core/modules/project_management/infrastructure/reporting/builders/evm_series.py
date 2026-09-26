"""EVM series mixin — thin reporting delegate.

Business logic lives in financials/earned_value/evm_series.py.
"""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.financials.models import (
    EvmSeriesPoint,
)
from src.core.modules.project_management.application.financials.earned_value.evm_series import (
    EarnedValueSeriesCalculator,
)
from src.core.modules.project_management.contracts.reads.financials.evm_series_reader import (
    EvmSeriesReader,
)


class ReportingEvmSeriesMixin:
    _evm_series_reader: EvmSeriesReader

    def _make_evm_series_calculator(self) -> EarnedValueSeriesCalculator:
        return EarnedValueSeriesCalculator(
            reader=self._evm_series_reader,
            tenant_context_service=self._tenant_context_service,
            calendar=self._calendar,
            calculator=self._make_evm_calculator(),
        )

    def get_evm_series(
        self,
        project_id: str,
        baseline_id: str | None = None,
        as_of: date | None = None,
        freq: str = "M",
    ) -> list[EvmSeriesPoint]:
        self._require_finance_view("view earned value trend", project_id=project_id)
        return self._make_evm_series_calculator().build_series(
            project_id, baseline_id=baseline_id, as_of=as_of
        )
