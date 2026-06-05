from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.register.utils.register_enum_utils import (
    coerce_entry_severity,
    coerce_entry_status,
    coerce_entry_type,
)
from src.core.modules.project_management.api.desktop.register.utils.register_status_utils import (
    is_overdue,
    severity_rank,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)

_ALL_FILTER_VALUES = (None, "", "all", "ALL")


def build_entry_list(
    *,
    register_service: object | None,
    project_id: str | None = None,
    entry_type: str | RegisterEntryType | None = None,
    status: str | RegisterEntryStatus | None = None,
    severity: str | RegisterEntrySeverity | None = None,
) -> tuple[object, ...]:
    if register_service is None:
        return ()
    entries = register_service.list_entries(
        project_id=(project_id or None),
        entry_type=(
            coerce_entry_type(entry_type)
            if entry_type not in _ALL_FILTER_VALUES
            else None
        ),
        status=(
            coerce_entry_status(status)
            if status not in _ALL_FILTER_VALUES
            else None
        ),
        severity=(
            coerce_entry_severity(severity)
            if severity not in _ALL_FILTER_VALUES
            else None
        ),
    )
    return tuple(
        sorted(
            entries,
            key=lambda entry: (
                severity_rank(entry.severity),
                0 if is_overdue(entry.due_date, entry.status) else 1,
                entry.due_date or date.max,
                (entry.title or "").casefold(),
            ),
        )
    )


__all__ = ["build_entry_list"]
