from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialSubmitChangeCommand:
    change_id: str
    expected_version: int


__all__ = ['FinancialSubmitChangeCommand']
