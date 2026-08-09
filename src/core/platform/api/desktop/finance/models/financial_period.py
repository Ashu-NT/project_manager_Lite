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


@dataclass(frozen=True)
class FinancialPeriodCreateCommand:
    code: str
    name: str
    fiscal_year: int
    period_number: int
    start_date: str
    end_date: str


@dataclass(frozen=True)
class FinancialPeriodUpdateCommand:
    period_id: str
    expected_version: int
    code: str | None = None
    name: str | None = None
    fiscal_year: int | None = None
    period_number: int | None = None
    start_date: str | None = None
    end_date: str | None = None


@dataclass(frozen=True)
class FinancialPeriodTransitionCommand:
    period_id: str
    expected_version: int


__all__ = [
    "FinancialPeriodCreateCommand",
    "FinancialPeriodDto",
    "FinancialPeriodTransitionCommand",
    "FinancialPeriodUpdateCommand",
]
