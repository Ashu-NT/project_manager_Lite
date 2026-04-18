from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.party.domain import Party


class PartyRepository(ABC):
    @abstractmethod
    def add(self, party: Party) -> None: ...

    @abstractmethod
    def update(self, party: Party) -> None: ...

    @abstractmethod
    def get(self, party_id: str) -> Party | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, party_code: str) -> Party | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Party]: ...


__all__ = ["PartyRepository"]
