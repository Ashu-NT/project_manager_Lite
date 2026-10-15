from __future__ import annotations

from datetime import date
from typing import Protocol

from src.core.modules.project_management.contracts.reads.financials.earned_value.models.series_facts import (
    EvmSeriesFacts,
)


class EvmSeriesReader(Protocol):
    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        baseline_id: str | None,
        as_of: date,
    ) -> EvmSeriesFacts | None: ...


__all__ = ["EvmSeriesReader"]
