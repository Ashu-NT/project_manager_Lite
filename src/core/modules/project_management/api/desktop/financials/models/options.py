from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class FinancialTaskOptionDescriptor:
    value: str
    label: str


__all__ = [
    "FinancialProjectOptionDescriptor",
    "FinancialTaskOptionDescriptor",
]
