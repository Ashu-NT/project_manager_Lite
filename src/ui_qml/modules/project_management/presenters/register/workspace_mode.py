from __future__ import annotations

from typing import Literal

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntryStatus,
    as_register_entry_status,
)

WorkspaceMode = Literal["risk", "register"]

_ACTIVE_STATUSES = {
    RegisterEntryStatus.OPEN,
    RegisterEntryStatus.IN_PROGRESS,
    RegisterEntryStatus.MITIGATED,
}

def is_active(status: str | RegisterEntryStatus) -> bool:
    return as_register_entry_status(status) in _ACTIVE_STATUSES
