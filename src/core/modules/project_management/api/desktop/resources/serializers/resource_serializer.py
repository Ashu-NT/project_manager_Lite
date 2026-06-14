from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.formatters.enum_formatter import (
    format_enum_label,
)
from src.core.modules.project_management.api.desktop.resources.formatters.money_formatter import (
    format_money,
)
from src.core.modules.project_management.api.desktop.resources.models.options import (
    ResourceEmployeeOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.resources.models.resources import (
    ResourceDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.utils.resource_enum_utils import (
    coerce_cost_type,
    coerce_worker_type,
)


def serialize_resource(
    resource,
    *,
    employee_lookup: dict[str, ResourceEmployeeOptionDescriptor],
) -> ResourceDesktopDto:
    employee_id = str(getattr(resource, "employee_id", "") or "").strip() or None
    employee_option = employee_lookup.get(employee_id or "")
    resolved_currency = (
        (getattr(resource, "currency_code", None) or "").strip().upper() or None
    )
    worker_type = coerce_worker_type(getattr(resource, "worker_type", None))
    cost_type = coerce_cost_type(getattr(resource, "cost_type", None))
    employee_context = (
        employee_option.context if employee_option is not None else "-"
    )
    capacity_percent = float(getattr(resource, "capacity_percent", 100.0) or 100.0)
    is_active = bool(getattr(resource, "is_active", True))
    return ResourceDesktopDto(
        id=resource.id,
        name=resource.name,
        code=getattr(resource, "code", "") or "",
        role=getattr(resource, "role", "") or "",
        worker_type=worker_type.value,
        worker_type_label=format_enum_label(worker_type.value),
        cost_type=cost_type.value,
        cost_type_label=format_enum_label(cost_type.value),
        hourly_rate=float(getattr(resource, "hourly_rate", 0.0) or 0.0),
        hourly_rate_label=format_money(
            getattr(resource, "hourly_rate", 0.0),
            resolved_currency,
        ),
        currency_code=resolved_currency,
        capacity_percent=capacity_percent,
        capacity_label=f"{capacity_percent:.1f}%",
        address=(getattr(resource, "address", "") or "").strip(),
        contact=(getattr(resource, "contact", "") or "").strip(),
        employee_id=employee_id,
        employee_context=employee_context,
        department=employee_option.department if employee_option is not None else "",
        site=employee_option.site if employee_option is not None else "",
        is_active=is_active,
        active_label="Active" if is_active else "Inactive",
        version=int(getattr(resource, "version", 1) or 1),
    )


__all__ = ["serialize_resource"]
