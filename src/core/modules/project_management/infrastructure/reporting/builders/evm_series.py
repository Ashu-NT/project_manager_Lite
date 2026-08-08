"""EVM series mixin — thin reporting delegate.

Business logic lives in financials/earned_value/evm_series.py.
"""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.contracts.reads.financials.evm_series_reader import (
    EvmSeriesReader,
)
from src.core.modules.project_management.application.financials.earned_value.evm_series import (
    EarnedValueSeriesCalculator,
)
from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    EvmSeriesPoint,
)

class ReportingEvmSeriesMixin:
    _evm_series_reader: EvmSeriesReader

    def _make_evm_series_calculator(self) -> EarnedValueSeriesCalculator:
        return EarnedValueSeriesCalculator(
            reader=self._evm_series_reader,
            tenant_context_service=self._tenant_context_service,
            labor_engine=self._make_labor_engine(),
            cost_policy_engine=self._make_cost_policy_engine(),
            evm_calculator=self._make_evm_calculator(),
        )

    def get_evm_series(
        self,
        project_id: str,
        baseline_id: str | None = None,
        as_of: date | None = None,
        freq: str = "M",
    ) -> list[EvmSeriesPoint]:
        self._require_view("view earned value trend", project_id=project_id)
        return self._make_evm_series_calculator().build_series(
            project_id, baseline_id=baseline_id, as_of=as_of
        )
