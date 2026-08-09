from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryStatus,
)


class ProjectCostEntryRepository(ABC):
    @abstractmethod
    def add(self, entry: ProjectCostEntry) -> None: ...

    @abstractmethod
    def get(self, entry_id: str, *, for_update: bool = False) -> ProjectCostEntry | None: ...

    @abstractmethod
    def get_by_idempotency_key(self, idempotency_key: str) -> ProjectCostEntry | None: ...

    @abstractmethod
    def list_for_project(
        self,
        project_id: str,
        *,
        status: ProjectCostEntryStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProjectCostEntry], int]:
        """Return a stable database page plus the filtered total."""
        ...

    @abstractmethod
    def update(self, entry: ProjectCostEntry, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def delete_draft(self, entry_id: str, *, expected_row_version: int) -> None:
        """Atomically delete a draft whose version still matches."""
        ...

    @abstractmethod
    def flush(self) -> None: ...


__all__ = ["ProjectCostEntryRepository"]
