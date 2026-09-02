from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.financials.forecast import ForecastStatus


@dataclass(frozen=True, slots=True)
class ForecastApprovalRequestResult:
    forecast_id: str
    project_id: str
    forecast_status: ForecastStatus
    row_version: int
    approval_request_id: str


__all__ = ["ForecastApprovalRequestResult"]
