from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class FinancialCommitmentSummaryDto:
    project_id: str
    planned_total: float
    planned_label: str
    uncommitted_total: float
    uncommitted_label: str
    committed_total: float
    committed_label: str
    invoiced_total: float
    invoiced_label: str
    paid_total: float
    paid_label: str
    exposure: float
    exposure_label: str
    commitment_rate_pct: float


__all__ = ["FinancialCommitmentSummaryDto"]
