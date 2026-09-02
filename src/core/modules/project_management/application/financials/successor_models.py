from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovedFinancialLineAdjustment:
    impact_id: str
    description: str
    amount: Decimal
    cost_code_id: str
    task_id: str | None
    target_line_id: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovedFinancialSuccessorResult:
    version_id: str
    line_references: tuple[tuple[str, str], ...]


__all__ = ["ApprovedFinancialLineAdjustment", "ApprovedFinancialSuccessorResult"]
