from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialDecideActualCommand:
    entry_id: str
    expected_version: int
    notes: str = ""


__all__ = ['FinancialDecideActualCommand']
