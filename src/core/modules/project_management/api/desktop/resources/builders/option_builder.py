from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.formatters.enum_formatter import (
    format_enum_label,
)
from src.core.modules.project_management.api.desktop.resources.models.options import (
    ResourceCategoryDescriptor,
    ResourceWorkerTypeDescriptor,
)
from src.core.modules.project_management.domain.enums import CostType, WorkerType


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


__all__ = ["build_category_options", "build_worker_type_options"]
