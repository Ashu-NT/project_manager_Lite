"""Presentation labels shared by Gantt UI consumers."""

from src.core.modules.project_management.api.desktop.common.constraint_presentation import (
    constraint_presentation,
)
from src.core.modules.project_management.api.desktop.common.dependency_presentation import (
    dependency_type_label,
)
from src.core.modules.project_management.application.scheduling.dto.responses.gantt import (
    GanttTaskRowDto,
)
from src.core.modules.project_management.domain.enums import DependencyType

_DEPENDENCY_LABELS = {
    kind.value: dependency_type_label(kind) for kind in DependencyType
}


def gantt_dependency_label(value: str) -> str:
    return _DEPENDENCY_LABELS.get(value, "Unsupported")


def status_label(row: GanttTaskRowDto) -> str:
    return row.status.replace("_", " ").title()


def constraint_label(row: GanttTaskRowDto) -> str:
    return (
        ""
        if row.is_summary
        else constraint_presentation(row.constraint_type or None).label
    )


__all__ = ["status_label", "constraint_label", "gantt_dependency_label"]
