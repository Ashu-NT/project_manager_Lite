from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialForecastMutationDto:
    forecast_id: str
    project_id: str
    status: str
    row_version: int
    approval_request_id: str = ""
