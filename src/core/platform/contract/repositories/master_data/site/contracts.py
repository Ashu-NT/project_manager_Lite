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
