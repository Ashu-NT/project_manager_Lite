from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.domain.master_data.org import Organization


class OrganizationRepository(ABC):
    @abstractmethod
    def add(self, organization: Organization) -> None: ...

    @abstractmethod
    def update(self, organization: Organization) -> None: ...

    # --- bootstrap/admin paths (no tenant filter) ---

    @abstractmethod
    def get(self, organization_id: str) -> Organization | None: ...

    @abstractmethod
    def get_by_code(self, organization_code: str) -> Organization | None: ...

    @abstractmethod
    def list_all(self, *, enabled_only: bool | None = None) -> list[Organization]: ...

    # --- tenant-scoped runtime paths ---

    @abstractmethod
    def get_for_tenant(self, organization_id: str, tenant_id: str) -> Organization | None: ...

    @abstractmethod
    def get_by_code_for_tenant(self, organization_code: str, tenant_id: str) -> Organization | None: ...

    @abstractmethod
    def list_for_tenant(self, tenant_id: str, *, enabled_only: bool | None = None) -> list[Organization]: ...

    @abstractmethod
    def list_page_for_tenant(
        self,
        tenant_id: str,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        enabled_only: bool | None = None,
    ) -> tuple[list[Organization], int, int]:
        """Return (items, total, filtered_total) for one page.

        `total` is the tenant's unfiltered organization count; `filtered_total`
        is the count matching `search`/`enabled_only`. The two differ only
        when a search term or availability filter is active -- callers use
        that difference to distinguish a genuinely empty dataset from a
        search/filter that matched nothing.
        """
        ...


__all__ = [
    "OrganizationRepository",
]
