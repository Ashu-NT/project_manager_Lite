"""Project status option builder."""

from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.api.desktop.projects.models.project import ProjectStatusDescriptor


def build_status_options() -> tuple[ProjectStatusDescriptor, ...]:
    return tuple(
        ProjectStatusDescriptor(
            value=status.value,
            label=status.value.replace("_", " ").title(),
        )
        for status in ProjectStatus
    )


__all__ = ["build_status_options"]
