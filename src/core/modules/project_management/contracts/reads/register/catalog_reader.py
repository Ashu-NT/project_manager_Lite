from __future__ import annotations

from datetime import date
from typing import Protocol

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)

from .models import RegisterCatalogReadPage


class RegisterCatalogReader(Protocol):
    def read_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        project_id: str | None,
        entry_type: RegisterEntryType | None,
        status: RegisterEntryStatus | None,
        severity: RegisterEntrySeverity | None,
        search_text: str,
        as_of: date,
        page: int,
        page_size: int,
    ) -> RegisterCatalogReadPage: ...


__all__ = ["RegisterCatalogReader"]
