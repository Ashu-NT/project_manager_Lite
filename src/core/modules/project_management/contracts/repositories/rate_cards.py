from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from src.core.modules.project_management.domain.financials.rate_cards import (
    ProjectRateCard,
    RateCardLine,
    RateType,
)


class ProjectRateCardRepository(ABC):
    @abstractmethod
    def add(self, rate_card: ProjectRateCard) -> None: ...

    @abstractmethod
    def get(self, rate_card_id: str) -> ProjectRateCard | None: ...

    @abstractmethod
    def list(
        self,
        *,
        project_id: str | None = None,
        include_inactive: bool = False,
    ) -> list[ProjectRateCard]: ...

    @abstractmethod
    def update(self, rate_card: ProjectRateCard) -> None: ...

    @abstractmethod
    def add_line(self, line: RateCardLine) -> None: ...

    @abstractmethod
    def get_line(self, line_id: str) -> RateCardLine | None: ...

    @abstractmethod
    def update_line(self, line: RateCardLine) -> None: ...

    @abstractmethod
    def list_lines(
        self,
        rate_card_id: str,
        *,
        include_inactive: bool = False,
    ) -> list[RateCardLine]: ...

    @abstractmethod
    def list_effective_lines(
        self,
        *,
        project_id: str | None,
        rate_type: RateType,
        unit: str,
        as_of: date,
    ) -> list[tuple[RateCardLine, ProjectRateCard]]:
        """Active, unit-matching, as-of-effective lines visible to a project
        scope (its own project-scoped card plus every organization-wide
        card), each paired with its owning card in the same query — callers
        must not re-fetch the card per line (that was a real N+1)."""
        ...

    @abstractmethod
    def list_lines_in_scope(self, *, project_id: str | None) -> list[RateCardLine]:
        """Active lines from every card whose scope exactly equals
        ``project_id`` (``None`` selects organization-wide cards only, never
        a mix of scopes). Used for overlap detection, which must compare
        lines within the same specificity tier, not across it — unlike
        ``list_effective_lines``, which deliberately spans tiers for
        resolution."""
        ...


__all__ = ["ProjectRateCardRepository"]
