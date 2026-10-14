from __future__ import annotations

from typing import Protocol

from src.core.platform.contract.interface.time_management.time.contracts import (
    WorkAllocationRecord,
    WorkOwnerRecord,
)
from src.core.platform.domain.time_management.time import TimeEntry


class TimeAccessPolicy(Protocol):
    """Authorization rules applied by the Time handlers.

    Platform supplies the global capability policy; a module that owns a scope
    model (e.g. PM projects) supplies its own implementation via composition.
    """

    def require_read_permission(self, operation_label: str) -> None: ...

    def require_manage_permission(self, operation_label: str) -> None: ...

    def require_project_scope(
        self,
        *,
        work_allocation: WorkAllocationRecord | None,
        work_owner: WorkOwnerRecord | None,
        operation_label: str,
    ) -> None: ...

    def require_review_scope(self, permission_code: str, entries: list[TimeEntry]) -> None: ...


__all__ = ["TimeAccessPolicy"]
