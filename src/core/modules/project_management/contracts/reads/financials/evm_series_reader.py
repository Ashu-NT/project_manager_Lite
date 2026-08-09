from __future__ import annotations

from datetime import date
from typing import Protocol

from .models.finance_snapshot_facts import EvmSeriesFacts


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
