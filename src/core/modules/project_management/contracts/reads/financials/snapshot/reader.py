from __future__ import annotations

from datetime import date
from typing import Protocol

from src.core.modules.project_management.contracts.reads.financials.snapshot.models.ledger_query import (
    ProjectFinanceLedgerQuery,
)
from src.core.modules.project_management.contracts.reads.financials.snapshot.models.snapshot_facts import (
    FinanceSnapshotFacts,
)


class FinanceSnapshotReader(Protocol):
    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        as_of: date,
        ledger_query: ProjectFinanceLedgerQuery | None = None,
        include_sensitive: bool = True,
    ) -> FinanceSnapshotFacts | None: ...


__all__ = ["FinanceSnapshotReader"]
