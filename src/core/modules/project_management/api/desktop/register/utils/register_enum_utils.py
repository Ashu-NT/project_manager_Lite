from __future__ import annotations

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)


def coerce_entry_type(value: str | RegisterEntryType | None) -> RegisterEntryType:
    if isinstance(value, RegisterEntryType):
        return value
    return as_register_entry_type(value or RegisterEntryType.RISK.value)


def coerce_entry_status(
    value: str | RegisterEntryStatus | None,
) -> RegisterEntryStatus:
    if isinstance(value, RegisterEntryStatus):
        return value
    return as_register_entry_status(value or RegisterEntryStatus.OPEN.value)


def coerce_entry_severity(
    value: str | RegisterEntrySeverity | None,
) -> RegisterEntrySeverity:
    if isinstance(value, RegisterEntrySeverity):
        return value
    return as_register_entry_severity(value or RegisterEntrySeverity.MEDIUM.value)


__all__ = [
    "coerce_entry_severity",
    "coerce_entry_status",
    "coerce_entry_type",
]
