from __future__ import annotations

from datetime import date
from typing import Protocol

from .models.finance_snapshot_facts import FinanceSnapshotFacts


class FinanceSnapshotReader(Protocol):
    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        as_of: date,
    ) -> FinanceSnapshotFacts | None: ...


__all__ = ["FinanceSnapshotReader"]

