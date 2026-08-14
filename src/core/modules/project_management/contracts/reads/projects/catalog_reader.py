from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.domain.enums import ProjectStatus

from .models import ProjectCatalogReadPage
from src.core.modules.project_management.contracts.reads.sorting import ReadSort


class ProjectCatalogReader(Protocol):
    def read_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        search_text: str,
        status: ProjectStatus | None,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> ProjectCatalogReadPage: ...


__all__ = ["ProjectCatalogReader"]
