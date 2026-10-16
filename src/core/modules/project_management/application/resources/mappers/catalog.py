from __future__ import annotations

from src.core.modules.project_management.application.resources.dto.responses.catalog import (
    ResourceResponse,
)
from src.core.modules.project_management.domain.resources.resource import Resource


def map_resource(value: Resource) -> ResourceResponse:
    return ResourceResponse(
        id=value.id,
        name=value.name,
        kind=value.kind,
        code=value.code,
        role=value.role,
        hourly_rate=value.hourly_rate,
        is_active=value.is_active,
        cost_type=value.cost_type,
        currency_code=value.currency_code,
        version=value.version,
        capacity_percent=value.capacity_percent,
        address=value.address,
        contact=value.contact,
        worker_type=value.worker_type,
        employee_id=value.employee_id,
        organization_id=value.organization_id,
        department_id=value.department_id,
        site_id=value.site_id,
    )










