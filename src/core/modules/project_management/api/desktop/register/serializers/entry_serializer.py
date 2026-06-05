from __future__ import annotations

from src.core.modules.project_management.api.desktop.register.formatters.enum_formatter import (
    format_enum_label,
)
from src.core.modules.project_management.api.desktop.register.models.entries import (
    RegisterEntryDesktopDto,
)
from src.core.modules.project_management.api.desktop.register.utils.register_status_utils import (
    is_overdue,
)
from src.core.modules.project_management.domain.risk.register import (
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)


def serialize_entry(
    entry,
    *,
    project_name_by_id: dict[str, str],
) -> RegisterEntryDesktopDto:
    entry_type = as_register_entry_type(entry.entry_type)
    severity = as_register_entry_severity(entry.severity)
    status = as_register_entry_status(entry.status)
    return RegisterEntryDesktopDto(
        id=entry.id,
        project_id=entry.project_id,
        project_name=project_name_by_id.get(entry.project_id, entry.project_id),
        code=str(getattr(entry, "code", "") or ""),
        entry_type=entry_type.value,
        entry_type_label=format_enum_label(entry_type.value),
        title=entry.title,
        description=entry.description or "",
        severity=severity.value,
        severity_label=format_enum_label(severity.value),
        status=status.value,
        status_label=format_enum_label(status.value),
        owner_name=entry.owner_name,
        due_date=entry.due_date,
        due_date_label=entry.due_date.isoformat() if entry.due_date else "No due date",
        impact_summary=entry.impact_summary or "",
        response_plan=entry.response_plan or "",
        is_overdue=is_overdue(entry.due_date, status),
        version=int(entry.version or 1),
    )


__all__ = ["serialize_entry"]
