from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from src.core.modules.project_management.domain.financials.budget import (
    BudgetLine,
    ProjectBudget,
)


class ProjectBudgetRepository(ABC):
    @abstractmethod
    def add(self, budget: ProjectBudget) -> None: ...

    @abstractmethod
    def get(self, budget_id: str) -> ProjectBudget | None: ...

    @abstractmethod
    def list_for_project(
        self, project_id: str, *, include_superseded: bool = True
    ) -> list[ProjectBudget]: ...

    @abstractmethod
    def get_latest_for_project(self, project_id: str) -> ProjectBudget | None:
        """The highest-``revision`` budget for this project, regardless of
        status — used to compute the next revision number at creation."""
        ...

    @abstractmethod
    def get_approved_for_project(self, project_id: str) -> ProjectBudget | None:
        """The one ``APPROVED`` budget for this project, if any (the
        partial unique index guarantees at most one exists)."""
        ...

    @abstractmethod
    def has_open_for_project(self, project_id: str) -> bool:
        """Whether a DRAFT/SUBMITTED budget already exists for this
        project — checked by the service before ``create_budget`` (the
        partial unique index is the DB-level backstop for the same rule)."""
        ...

    @abstractmethod
    def update(self, budget: ProjectBudget, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def delete(self, budget_id: str, *, expected_row_version: int) -> None:
        """Atomic delete-if-version-matches (see ``delete_with_version_check``)
        — a plain read-check-then-delete would leave a TOCTOU gap where a
        concurrent submit could be silently discarded. The service is
        responsible for confirming DRAFT status from the same freshly-
        fetched budget whose version is passed here. Cascades to lines at
        the database level (``ondelete=CASCADE``)."""
        ...

    @abstractmethod
    def add_line(self, line: BudgetLine) -> None: ...

    @abstractmethod
    def get_line(self, line_id: str) -> BudgetLine | None: ...

    @abstractmethod
    def update_line(self, line: BudgetLine, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def delete_line(self, line_id: str, *, expected_row_version: int) -> None:
        """Atomic delete-if-version-matches — see ``delete``."""
        ...

    @abstractmethod
    def list_lines(self, budget_id: str) -> list[BudgetLine]: ...

    @abstractmethod
    def list_lines_for_project(
        self, project_id: str, *, offset: int = 0, limit: int = 50
    ) -> list[BudgetLine]:
        """Return a stable page of versioned lines for one scoped project."""
        ...

    @abstractmethod
    def summarize_lines_for_project(
        self, project_id: str
    ) -> dict[str, tuple[int, Decimal]]:
        """Map budget id to line count and authorized total."""
        ...

    @abstractmethod
    def flush(self) -> None:
        """Exposes a session-flush point to the application service
        without the service depending on SQLAlchemy directly — needed so
        ``approve_budget`` can supersede the previous approved budget and
        flush it *before* approving the new one (otherwise a mid-
        transaction flush could see two ``APPROVED`` rows at once and trip
        the partial unique index)."""
        ...


__all__ = ["ProjectBudgetRepository"]
