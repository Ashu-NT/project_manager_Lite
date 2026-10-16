"""Map domain state to a neutral response; presentation stays in adapters."""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.risk.dto.responses.entries import (
    RegisterCatalogResponseDto,
    RegisterEntryResponseDto,
)
from src.core.modules.project_management.contracts.reads.register import (
    RegisterCatalogReadPage,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)


def map_register_entry(
    entry: RegisterEntry, *, project_name_by_id: dict[str, str], as_of: date
) -> RegisterEntryResponseDto:
    entry_type = as_register_entry_type(entry.entry_type)
    severity = as_register_entry_severity(entry.severity)
    status = as_register_entry_status(entry.status)
    return RegisterEntryResponseDto(
        id=entry.id,
        project_id=entry.project_id,
        project_name=project_name_by_id.get(entry.project_id, entry.project_id),
        code=str(getattr(entry, "code", "") or ""),
        entry_type=entry_type.value,
        title=entry.title,
        description=entry.description or "",
        severity=severity.value,
        status=status.value,
        owner_name=entry.owner_name,
        due_date=entry.due_date,
        impact_summary=entry.impact_summary or "",
        response_plan=entry.response_plan or "",
        is_overdue=entry.is_overdue_on(as_of),
        version=int(entry.version or 1),
    )


def map_register_catalog(page: RegisterCatalogReadPage, *, as_of: date) -> RegisterCatalogResponseDto:
    return RegisterCatalogResponseDto(
        items=tuple(map_register_entry(item.entry, project_name_by_id={item.entry.project_id: item.project_name}, as_of=as_of) for item in page.items),
        urgent_items=tuple(map_register_entry(item.entry, project_name_by_id={item.entry.project_id: item.project_name}, as_of=as_of) for item in page.urgent_items),
        filtered_total=page.filtered_total, scope_total=page.summary.scope_total,
        scope_risk_total=page.summary.scope_risk_total, open_risks=page.summary.open_risks,
        open_issues=page.summary.open_issues, pending_changes=page.summary.pending_changes,
        active=page.summary.active, critical=page.summary.critical, overdue=page.summary.overdue,
        due_soon=page.summary.due_soon, page=page.page, page_size=page.page_size,
        sort_key=page.sort.key, sort_direction=page.sort.direction.value,
    )
