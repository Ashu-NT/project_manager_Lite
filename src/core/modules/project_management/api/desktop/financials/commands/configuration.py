from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialCreateCostCodeCommand:
    project_id: str
    code: str
    name: str
    description: str = ""


__all__ = ["FinancialCreateCostCodeCommand"]
