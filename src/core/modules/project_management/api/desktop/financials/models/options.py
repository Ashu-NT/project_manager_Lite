from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialLookupOptionDto:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class FinancialLookupPageDto:
    items: tuple[FinancialLookupOptionDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25
    has_more: bool = False


__all__ = [
    "FinancialLookupOptionDto",
    "FinancialLookupPageDto",
]
