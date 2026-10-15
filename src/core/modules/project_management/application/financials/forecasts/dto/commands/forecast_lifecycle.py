from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialVersionedForecastCommand:
    forecast_id: str
    expected_version: int
    notes: str = ""
