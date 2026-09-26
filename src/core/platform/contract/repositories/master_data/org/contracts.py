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
    def list_all(self, *, status: str | None = None) -> list[Organization]: ...

    # --- tenant-scoped runtime paths ---

    @abstractmethod
    def get_for_tenant(self, organization_id: str, tenant_id: str) -> Organization | None: ...

    @abstractmethod
    def get_by_code_for_tenant(self, organization_code: str, tenant_id: str) -> Organization | None: ...

    @abstractmethod
    def list_for_tenant(self, tenant_id: str, *, status: str | None = None) -> list[Organization]: ...

    @abstractmethod
    def list_page_for_tenant(
        self,
        tenant_id: str,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Organization], int, int]:
        """Return (items, total, filtered_total) for one page.

        `total` is the tenant's unfiltered organization count; `filtered_total`
        is the count matching `search`/`status`. The two differ only when a
        search term or a status filter is active -- callers use that
        difference to distinguish a genuinely empty dataset from a search/
        filter that matched nothing. `status` is one exact
        ORGANIZATION_STATUS_* value; `None` means all statuses.
        """
        ...


__all__ = [
    "OrganizationRepository",
]
