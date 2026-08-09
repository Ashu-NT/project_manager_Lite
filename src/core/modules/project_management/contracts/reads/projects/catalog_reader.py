from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.domain.enums import ProjectStatus

from .models import ProjectCatalogReadPage


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
    ) -> ProjectCatalogReadPage: ...


__all__ = ["ProjectCatalogReader"]
