from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import format_money
from src.core.modules.project_management.api.desktop.resources.formatters.enum_formatter import (
    format_enum_label,
)
from src.core.modules.project_management.api.desktop.resources.models.options import (
    ResourceEmployeeOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.resources.models.resources import (
    ResourceCatalogItemDesktopDto,
    ResourceDesktopDto,
    ResourceInspectorDesktopDto,
    ResourceSummaryDesktopDto,
)
from src.core.modules.project_management.api.desktop.resources.utils.resource_enum_utils import (
    coerce_cost_type,
    coerce_worker_type,
)
from src.core.modules.project_management.contracts.reads.resources import (
    ResourceCatalogReadItem,
    ResourceInspectorFact,
    ResourceSummaryFact,
)
from src.core.platform.finance.money import canonical_decimal_text


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
    employee_context = employee_option.context if employee_option is not None else "-"
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
        hourly_rate=canonical_decimal_text(resource.hourly_rate),
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


def serialize_resource_catalog_item(
    fact: ResourceCatalogReadItem,
) -> ResourceCatalogItemDesktopDto:
    worker_type = coerce_worker_type(fact.worker_type)
    cost_type = coerce_cost_type(fact.cost_type)
    capacity_percent = float(fact.capacity_percent)
    return ResourceCatalogItemDesktopDto(
        id=fact.resource_id,
        code=fact.code,
        name=fact.name,
        role=fact.role,
        worker_type=worker_type.value,
        worker_type_label=format_enum_label(worker_type.value),
        cost_type=cost_type.value,
        cost_type_label=format_enum_label(cost_type.value),
        organization_id=fact.organization_id,
        organization_label=fact.organization_label,
        department_id=fact.department_id,
        department=fact.department_label,
        site_id=fact.site_id,
        site=fact.site_label,
        employee_id=fact.employee_id,
        employee_name=fact.employee_name,
        is_active=fact.is_active,
        active_label="Active" if fact.is_active else "Inactive",
        capacity_percent=capacity_percent,
        capacity_label=f"{capacity_percent:.1f}%",
        version=fact.version,
    )


def serialize_resource_inspector(
    fact: ResourceInspectorFact,
) -> ResourceInspectorDesktopDto:
    worker_type = coerce_worker_type(fact.worker_type)
    capacity_percent = float(fact.capacity_percent)
    return ResourceInspectorDesktopDto(
        id=fact.resource_id,
        code=fact.code,
        name=fact.name,
        role=fact.role,
        worker_type=worker_type.value,
        worker_type_label=format_enum_label(worker_type.value),
        organization_id=fact.organization_id,
        organization_label=fact.organization_label,
        department_id=fact.department_id,
        department=fact.department_label,
        site_id=fact.site_id,
        site=fact.site_label,
        employee_id=fact.employee_id,
        employee_name=fact.employee_name,
        is_active=fact.is_active,
        active_label="Active" if fact.is_active else "Inactive",
        capacity_percent=capacity_percent,
        capacity_label=f"{capacity_percent:.1f}%",
        project_count=fact.project_count,
        assignment_count=fact.assignment_count,
        version=fact.version,
        can_read=fact.can_read,
        can_manage=fact.can_manage,
        can_deactivate=fact.can_deactivate,
        can_reactivate=fact.can_reactivate,
    )


def serialize_resource_summary(fact: ResourceSummaryFact) -> ResourceSummaryDesktopDto:
    worker_type = coerce_worker_type(fact.worker_type)
    cost_type = coerce_cost_type(fact.cost_type)
    capacity_percent = float(fact.capacity_percent)
    context = " | ".join(
        value for value in (fact.department_label, fact.site_label) if value
    ) or "-"
    return ResourceSummaryDesktopDto(
        id=fact.resource_id,
        code=fact.code,
        name=fact.name,
        role=fact.role,
        worker_type=worker_type.value,
        worker_type_label=format_enum_label(worker_type.value),
        cost_type=cost_type.value,
        cost_type_label=format_enum_label(cost_type.value),
        hourly_rate=canonical_decimal_text(fact.hourly_rate),
        hourly_rate_label=format_money(fact.hourly_rate, fact.currency_code),
        currency_code=fact.currency_code,
        capacity_percent=capacity_percent,
        capacity_label=f"{capacity_percent:.1f}%",
        address=fact.address,
        contact=fact.contact,
        organization_id=fact.organization_id,
        organization_label=fact.organization_label,
        department_id=fact.department_id,
        department=fact.department_label,
        site_id=fact.site_id,
        site=fact.site_label,
        employee_id=fact.employee_id,
        employee_name=fact.employee_name,
        employee_title=fact.employee_title,
        employee_context=context,
        is_active=fact.is_active,
        active_label="Active" if fact.is_active else "Inactive",
        version=fact.version,
        can_read=fact.can_read,
        can_manage=fact.can_manage,
    )


__all__ = [
    "serialize_resource",
    "serialize_resource_catalog_item",
    "serialize_resource_inspector",
    "serialize_resource_summary",
]
