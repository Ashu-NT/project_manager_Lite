from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FinancialCostCodeOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class FinancialManualActualOptionsDto:
    currency_code: str = ""
    entry_kinds: tuple[FinancialCostCodeOptionDescriptor, ...] = field(
        default_factory=lambda: (
            FinancialCostCodeOptionDescriptor("actual", "Actual"),
            FinancialCostCodeOptionDescriptor("adjustment", "Adjustment"),
        )
    )


__all__ = [
    "FinancialCostCodeOptionDescriptor",
    "FinancialManualActualOptionsDto",
]
