from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialPeriodDto:
    id: str
    organization_id: str
    code: str
    name: str
    fiscal_year: int
    period_number: int
    start_date: str
    end_date: str
    status: str
    accepts_normal_posting: bool
    closed_by: str
    closed_at: str
    locked_by: str
    locked_at: str
    version: int


__all__ = [
    "FinancialPeriodDto",
]
