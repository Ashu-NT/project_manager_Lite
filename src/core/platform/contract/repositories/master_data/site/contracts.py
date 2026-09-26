from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.domain.master_data.site import Site


class SiteRepository(ABC):
    @abstractmethod
    def add(self, site: Site) -> None: ...

    @abstractmethod
    def update(self, site: Site) -> None: ...

    @abstractmethod
    def get(self, site_id: str) -> Site | None: ...

    @abstractmethod
    def get_for_tenant(self, site_id: str, tenant_id: str) -> Site | None:
        """Tenant-scoped only -- unlike `get()`, NOT filtered to the ambient active
        organization. For cross-organization governance reads (e.g. RoleGovernance resolving a
        site-scoped role assignment against a non-active organization) where `get()`'s
        active-organization filter would incorrectly return `None`."""
        ...

    @abstractmethod
    def get_by_code(self, organization_id: str, site_code: str) -> Site | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Site]: ...

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
    ) -> tuple[list[Site], int, int]:
        """Tenant-scoped only -- like `get_for_tenant`, NOT filtered to the ambient
        active organization. For an admin viewing ANY organization's sites (e.g.
        Organization Detail's Sites tab) regardless of which organization is
        currently active in the caller's session. Returns
        (page_items, total_count, filtered_total_count)."""
        ...


__all__ = [
    "SiteRepository",
]
