from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialForecastDto:
    project_id: str
    method: str
    bac: float
    bac_label: str
    ac: float
    ac_label: str
    ev: float
    ev_label: str
    etc: float
    etc_label: str
    eac: float
    eac_label: str
    vac: float
    vac_label: str
    cpi: float
    cpi_label: str
    is_over_budget: bool
    exceeds_threshold: bool
    threshold_percent: float


__all__ = ["FinancialForecastDto"]
