from __future__ import annotations

from typing import Any, Protocol

from src.core.platform.contract.interface.time_management.time.contracts import (
    WorkAllocationRecord,
)


class WorkAllocationHoursEventFactory(Protocol):
    """Builds the owning module's fact for a TimeEntry-driven hours change.

    Platform Time has no assignment-event vocabulary; a module that owns
    assignment tracking (PM) supplies this via composition.
    """

    def __call__(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        work_allocation: WorkAllocationRecord,
    ) -> Any | None: ...


__all__ = ["WorkAllocationHoursEventFactory"]
