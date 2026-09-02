from __future__ import annotations

from typing import Protocol

from .models.finance_setup_facts import FinanceSetupFacts


class FinanceSetupReader(Protocol):
    def get_setup(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
    ) -> FinanceSetupFacts | None: ...


__all__ = ["FinanceSetupReader"]
