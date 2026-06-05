from __future__ import annotations

from src.core.modules.project_management.api.desktop.register.formatters.enum_formatter import (
    format_enum_label,
)
from src.core.modules.project_management.api.desktop.register.models.options import (
    RegisterEntrySeverityDescriptor,
    RegisterEntryStatusDescriptor,
    RegisterEntryTypeDescriptor,
    RegisterProjectOptionDescriptor,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)


def build_project_options(
    project_service: object | None = None,
) -> tuple[RegisterProjectOptionDescriptor, ...]:
    if project_service is None:
        return ()
    projects = sorted(
        project_service.list_projects(),
        key=lambda project: (project.name or "").casefold(),
    )
    return tuple(
        RegisterProjectOptionDescriptor(value=project.id, label=project.name)
        for project in projects
    )


def build_entry_type_options() -> tuple[RegisterEntryTypeDescriptor, ...]:
    return tuple(
        RegisterEntryTypeDescriptor(
            value=entry_type.value,
            label=format_enum_label(entry_type.value),
        )
        for entry_type in RegisterEntryType
    )


def build_status_options() -> tuple[RegisterEntryStatusDescriptor, ...]:
    return tuple(
        RegisterEntryStatusDescriptor(
            value=status.value,
            label=format_enum_label(status.value),
        )
        for status in RegisterEntryStatus
    )


def build_severity_options() -> tuple[RegisterEntrySeverityDescriptor, ...]:
    return tuple(
        RegisterEntrySeverityDescriptor(
            value=severity.value,
            label=format_enum_label(severity.value),
        )
        for severity in RegisterEntrySeverity
    )


__all__ = [
    "build_entry_type_options",
    "build_project_options",
    "build_severity_options",
    "build_status_options",
]
