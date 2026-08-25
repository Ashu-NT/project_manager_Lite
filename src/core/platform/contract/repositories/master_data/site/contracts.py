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


__all__ = [
    "SiteRepository",
]
