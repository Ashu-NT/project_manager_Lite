from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FinancialCostItemDto:
    id: str
    project_id: str
    task_id: str | None
    task_name: str
    code: str
    description: str
    planned_amount: float
    planned_amount_label: str
    committed_amount: float
    committed_amount_label: str
    actual_amount: float
    actual_amount_label: str
    forecast_amount: float
    forecast_amount_label: str
    commitment_status: str
    commitment_status_label: str
    vendor_reference: str | None
    cost_type: str
    cost_type_label: str
    incurred_date: date | None
    incurred_date_label: str
    currency_code: str | None
    version: int


__all__ = ["FinancialCostItemDto"]
