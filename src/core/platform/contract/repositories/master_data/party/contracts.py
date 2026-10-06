from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.domain.master_data.party import Party


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

    @abstractmethod
    def list_page_for_organization_in_tenant(
        self,
        organization_id: str,
        tenant_id: str,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        active_only: bool | None = None,
        party_type: str | None = None,
        role: str | None = None,
    ) -> tuple[list[Party], int, int]:
        """Tenant-scoped (not ambient-active-organization-scoped) paginated
        read -- mirrors DocumentRepository/EmployeeRepository's own
        established list_page_for_organization_in_tenant pattern. Returns
        (page_items, total_count, filtered_total_count). `role` matches
        against the comma-separated `roles` column (a Party may hold
        several roles at once)."""
        ...


__all__ = ["PartyRepository"]
