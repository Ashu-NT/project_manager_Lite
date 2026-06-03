from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from src.core.platform.site.domain import Site


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


class LocationReference(Protocol):
    id: str
    organization_id: str
    site_id: str
    location_code: str
    name: str
    is_active: bool


class LocationReferenceRepository(Protocol):
    def get(self, location_id: str) -> LocationReference | None: ...

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> list[LocationReference]: ...


__all__ = [
    "LocationReference",
    "LocationReferenceRepository",
    "SiteRepository",
]
