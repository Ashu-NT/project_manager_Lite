from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.project_management.domain.financials.commitment import (
    ProjectCommitment,
    ProjectCommitmentLine,
    ProjectCommitmentMatch,
    ProjectCommitmentSourceRevision,
)
from src.core.modules.project_management.contracts.reads import ReadSort


class ProjectCommitmentRepository(ABC):
    @abstractmethod
    def add(self, commitment: ProjectCommitment) -> None: ...

    @abstractmethod
    def get(self, commitment_id: str) -> ProjectCommitment | None: ...

    @abstractmethod
    def get_by_purchase_order(self, purchase_order_id: str) -> ProjectCommitment | None: ...

    @abstractmethod
    def add_line(self, line: ProjectCommitmentLine) -> None: ...

    @abstractmethod
    def get_line(
        self, line_id: str, *, for_update: bool = False
    ) -> ProjectCommitmentLine | None: ...

    @abstractmethod
    def get_line_by_source(
        self, purchase_order_id: str, purchase_order_line_id: str, *, for_update: bool = False
    ) -> ProjectCommitmentLine | None: ...

    @abstractmethod
    def list_lines_for_project(
        self,
        project_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        sort: ReadSort | None = None,
    ) -> tuple[list[ProjectCommitmentLine], int]: ...

    @abstractmethod
    def update_line(self, line: ProjectCommitmentLine, *, expected_row_version: int) -> None: ...

    @abstractmethod
    def add_source_revision(self, revision: ProjectCommitmentSourceRevision) -> None: ...

    @abstractmethod
    def get_source_revision(
        self, line_id: str, source_revision: int
    ) -> ProjectCommitmentSourceRevision | None: ...

    @abstractmethod
    def add_match(self, match: ProjectCommitmentMatch) -> None: ...

    @abstractmethod
    def get_match(self, match_id: str) -> ProjectCommitmentMatch | None: ...

    @abstractmethod
    def get_match_by_idempotency_key(
        self, idempotency_key: str
    ) -> ProjectCommitmentMatch | None: ...

    @abstractmethod
    def get_original_match_for_cost_entry(
        self, cost_entry_id: str
    ) -> ProjectCommitmentMatch | None: ...

    @abstractmethod
    def has_reversal_for_match(self, match_id: str) -> bool: ...

    @abstractmethod
    def list_matches_for_line(self, line_id: str) -> list[ProjectCommitmentMatch]: ...

    @abstractmethod
    def flush(self) -> None: ...


__all__ = ["ProjectCommitmentRepository"]
