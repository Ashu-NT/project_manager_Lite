from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.resources.models.availability import (
    ResourceAvailabilityDto,
)
from src.core.modules.project_management.api.desktop.resources.serializers.availability_serializer import (
    serialize_resource_availability,
)
from src.core.modules.project_management.application.resources.capacity.queries.workload import (
    ResourceWorkloadQueryHandler,
)
from src.core.platform.common.exceptions import ConfigurationError, ValidationError


def build_resource_availability(
    resource_id: str,
    *,
    workload_service: ResourceWorkloadQueryHandler | None,
    start_date: date | None,
    end_date: date | None,
) -> ResourceAvailabilityDto:
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
    fact = workload_service.read(
        normalized_id,
        start_date=start_date,
        end_date=end_date,
    )
    return serialize_resource_availability(
        normalized_id,
        fact,
    )


__all__ = ["build_resource_availability"]
