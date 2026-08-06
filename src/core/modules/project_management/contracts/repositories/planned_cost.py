from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.financials.planned_cost import (
    ProjectPlannedCostLine,
    ProjectPlannedCostVersion,
)


class ProjectPlannedCostVersionRepository(ABC):
    @abstractmethod
    def add(self, version: ProjectPlannedCostVersion) -> None: ...

    @abstractmethod
    def get(self, version_id: str) -> ProjectPlannedCostVersion | None: ...

    @abstractmethod
    def list_for_project(self, project_id: str) -> list[ProjectPlannedCostVersion]: ...

    @abstractmethod
    def get_current_for_project(
        self, project_id: str
    ) -> ProjectPlannedCostVersion | None:
        """The one ``CURRENT`` version for this project, if any (the
        partial unique index guarantees at most one exists)."""
        ...

    @abstractmethod
    def update(
        self, version: ProjectPlannedCostVersion, *, expected_row_version: int
    ) -> None:
        """Used only to flip a previously-``CURRENT`` version to
        ``SUPERSEDED`` — there is no other mutation path for an existing
        version's own fields."""
        ...

    @abstractmethod
    def add_lines(self, lines: list[ProjectPlannedCostLine]) -> None:
        """Persists a whole snapshot's lines together — lines are always
        created as one batch alongside their version, never one at a
        time."""
        ...

    @abstractmethod
    def list_lines(self, version_id: str) -> list[ProjectPlannedCostLine]: ...

    @abstractmethod
    def flush(self) -> None:
        """Exposes a session-flush point to the application service so the
        previous ``CURRENT`` version can be superseded and flushed before
        the new one is inserted (otherwise a mid-transaction flush could
        see two ``CURRENT`` rows at once and trip the partial unique
        index)."""
        ...


__all__ = ["ProjectPlannedCostVersionRepository"]
