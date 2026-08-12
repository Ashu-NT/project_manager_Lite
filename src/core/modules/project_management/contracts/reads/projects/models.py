from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.core.modules.project_management.domain.projects.project import Project


@dataclass(frozen=True, slots=True)
class ProjectCatalogReadItem:
    project: Project
    site_label: str = ""
    financial_currency_code: str = ""
    approved_budget: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ProjectCatalogSummary:
    total: int = 0
    active: int = 0
    planned: int = 0
    on_hold: int = 0
    completed: int = 0


@dataclass(frozen=True, slots=True)
class ProjectCatalogReadPage:
    items: tuple[ProjectCatalogReadItem, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    summary: ProjectCatalogSummary = ProjectCatalogSummary()


__all__ = [
    "ProjectCatalogReadItem",
    "ProjectCatalogReadPage",
    "ProjectCatalogSummary",
]
