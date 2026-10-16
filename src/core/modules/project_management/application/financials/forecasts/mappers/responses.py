from __future__ import annotations

from src.core.modules.project_management.application.financials.forecasts.dto.responses.forecast_approval import (
    ForecastApprovalRequestResult,
)
from src.core.modules.project_management.application.financials.forecasts.dto.responses.mutations import (
    FinancialForecastMutationDto,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ProjectForecast,
)


def map_forecast(forecast: ProjectForecast) -> FinancialForecastMutationDto:
    return FinancialForecastMutationDto(
        forecast_id=forecast.id, project_id=forecast.project_id,
        status=forecast.status.value, row_version=forecast.row_version,
    )


def map_forecast_approval(result: ForecastApprovalRequestResult) -> FinancialForecastMutationDto:
    return FinancialForecastMutationDto(
        forecast_id=result.forecast_id, project_id=result.project_id,
        status=result.forecast_status.value, row_version=result.row_version,
        approval_request_id=result.approval_request_id,
    )
