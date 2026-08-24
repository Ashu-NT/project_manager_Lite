from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.formatters.enum_formatter import (
    format_enum_label,
)
from src.core.modules.project_management.api.desktop.resources.models.options import (
    ResourceCategoryDescriptor,
    ResourceKindDescriptor,
    ResourceScopeOptionDescriptor,
    ResourceWorkerTypeDescriptor,
)
from src.core.modules.project_management.domain.enums import CostType, ResourceKind, WorkerType


def build_worker_type_options() -> tuple[ResourceWorkerTypeDescriptor, ...]:
    return tuple(
        ResourceWorkerTypeDescriptor(
            value=worker_type.value,
            label=format_enum_label(worker_type.value),
        )
        for worker_type in WorkerType
    )


def build_category_options() -> tuple[ResourceCategoryDescriptor, ...]:
    return tuple(
        ResourceCategoryDescriptor(
            value=cost_type.value,
            label=format_enum_label(cost_type.value),
        )
        for cost_type in CostType
    )


def build_kind_options() -> tuple[ResourceKindDescriptor, ...]:
    return tuple(
        ResourceKindDescriptor(value=kind.value, label=format_enum_label(kind.value))
        for kind in ResourceKind
    )


def build_department_options(service: object | None) -> tuple[ResourceScopeOptionDescriptor, ...]:
    if service is None:
        return ()
    return tuple(
        ResourceScopeOptionDescriptor(
            value=row.id,
            label=row.name,
            is_active=bool(row.is_active),
            site_id=str(row.site_id or ""),
        )
        for row in service.list_departments(active_only=None)
    )


def build_site_options(service: object | None) -> tuple[ResourceScopeOptionDescriptor, ...]:
    if service is None:
        return ()
    return tuple(
        ResourceScopeOptionDescriptor(
            value=row.id,
            label=row.name,
            is_active=bool(row.is_active),
        )
        for row in service.list_sites(active_only=None)
    )


__all__ = [
    "build_category_options",
    "build_department_options",
    "build_kind_options",
    "build_site_options",
    "build_worker_type_options",
]
