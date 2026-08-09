from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.domain.enums import CostType

from .models import ResourceCatalogReadPage


class ResourceCatalogReader(Protocol):
    def read_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        search_text: str,
        active: bool | None,
        category: CostType | None,
        page: int,
        page_size: int,
    ) -> ResourceCatalogReadPage: ...


__all__ = ["ResourceCatalogReader"]
