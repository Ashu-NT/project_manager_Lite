from __future__ import annotations

from datetime import date

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    as_register_entry_severity,
    as_register_entry_status,
)


def severity_rank(value: RegisterEntrySeverity | str) -> int:
    resolved = as_register_entry_severity(value)
    order = {
        RegisterEntrySeverity.CRITICAL: 0,
        RegisterEntrySeverity.HIGH: 1,
        RegisterEntrySeverity.MEDIUM: 2,
        RegisterEntrySeverity.LOW: 3,
    }
    return order.get(resolved, 99)


def is_overdue(
    due_date: date | None,
    status: RegisterEntryStatus | str,
) -> bool:
    if due_date is None:
        return False
    resolved_status = as_register_entry_status(status)
    if resolved_status in {
        RegisterEntryStatus.APPROVED,
        RegisterEntryStatus.REJECTED,
        RegisterEntryStatus.CLOSED,
    }:
        return False
    return due_date < date.today()


__all__ = ["is_overdue", "severity_rank"]
