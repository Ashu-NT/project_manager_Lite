from __future__ import annotations

from src.core.modules.project_management.api.desktop.register.formatters.enum_formatter import (
    format_enum_label,
)
from src.core.modules.project_management.api.desktop.register.models.entries import (
    RegisterEntryDesktopDto,
)
from src.core.modules.project_management.application.risk.dto.responses.entries import (
    RegisterEntryResponseDto,
)


def serialize_entry(response: RegisterEntryResponseDto, *, project_name_by_id: dict[str, str]) -> RegisterEntryDesktopDto:
    return RegisterEntryDesktopDto(id=response.id, project_id=response.project_id, project_name=project_name_by_id.get(response.project_id, response.project_name or response.project_id), code=response.code, entry_type=response.entry_type, entry_type_label=format_enum_label(response.entry_type), title=response.title, description=response.description, severity=response.severity, severity_label=format_enum_label(response.severity), status=response.status, status_label=format_enum_label(response.status), owner_name=response.owner_name, due_date=response.due_date, due_date_label=response.due_date.isoformat() if response.due_date else 'No due date', impact_summary=response.impact_summary, response_plan=response.response_plan, is_overdue=response.is_overdue, version=response.version)


__all__ = ["serialize_entry"]
