from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.resources.capacity.queries.workload import (
    ResourceWorkloadQueryHandler,
)
from src.core.modules.project_management.application.resources.dto.responses.availability import (
    ResourceWorkloadResponse,
)
from src.core.platform.common.exceptions import ConfigurationError, ValidationError


def build_resource_availability(
    resource_id: str,
    *,
    workload_service: ResourceWorkloadQueryHandler | None,
    start_date: date | None,
    end_date: date | None,
) -> ResourceWorkloadResponse:
    normalized_id = str(resource_id or "").strip()
    if not normalized_id:
        raise ValidationError(
            "Resource ID is required.", code="RESOURCE_WORKLOAD_RESOURCE_REQUIRED"
        )
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise ValidationError(
            "Availability requires valid start and end dates.",
            code="RESOURCE_WORKLOAD_DATE_REQUIRED",
        )
    if workload_service is None:
        raise ConfigurationError("Resource workload service is not configured.")
    return workload_service.read(
        normalized_id,
        start_date=start_date,
        end_date=end_date,
    )


__all__ = ["build_resource_availability"]
