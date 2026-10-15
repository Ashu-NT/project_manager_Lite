from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeRequest,
)


@dataclass(frozen=True, slots=True)
class FinancialChangeImpactMutationResult:
    """Parent and impact mutated together in the caller-owned transaction."""

    change: FinancialChangeRequest
    impact: FinancialChangeImpact


__all__ = ["FinancialChangeImpactMutationResult"]
