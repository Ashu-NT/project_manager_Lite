from __future__ import annotations

from datetime import date
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
        site_id: str | None = None,
        department_id: str | None = None,
        manager_user_id: str | None = None,
        start_date_from: date | None = None,
        start_date_to: date | None = None,
        end_date_from: date | None = None,
        end_date_to: date | None = None,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> ProjectCatalogReadPage: ...


__all__ = ["ProjectCatalogReader"]
