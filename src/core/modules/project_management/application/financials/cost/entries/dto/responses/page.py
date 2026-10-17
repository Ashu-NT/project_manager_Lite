from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.financials.cost.entries.dto.responses.cost_entry import (
    CostEntryResponse,
)


@dataclass(frozen=True, slots=True)
class CostEntryPage:
    items: tuple[CostEntryResponse, ...] = ()
    total: int = 0
    offset: int = 0
    limit: int = 50
    sort_key: str = "metaText"
    sort_direction: str = "desc"
    can_create_manual_actual: bool = False
