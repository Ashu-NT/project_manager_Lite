"""EVM series mixin — thin reporting delegate.

Business logic lives in financials/earned_value/evm_series.py.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.baseline import BaselineRepository
from src.core.modules.project_management.application.financials.earned_value.evm_series import (
    EarnedValueSeriesCalculator,
)
from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    EvmSeriesPoint,
)


class ReportingEvmSeriesMixin:
    _project_repo: ProjectRepository
    _baseline_repo: BaselineRepository

    def _make_evm_series_calculator(self) -> EarnedValueSeriesCalculator:
        return EarnedValueSeriesCalculator(
            project_repo=self._project_repo,
            baseline_repo=self._baseline_repo,
            evm_calculator=self._make_evm_calculator(),
        )

    def get_evm_series(
        self,
        project_id: str,
        baseline_id: Optional[str] = None,
        as_of: Optional[date] = None,
        freq: str = "M",
    ) -> list[EvmSeriesPoint]:
        self._require_view("view earned value trend", project_id=project_id)
        return self._make_evm_series_calculator().build_series(
            project_id, baseline_id=baseline_id, as_of=as_of
        )
