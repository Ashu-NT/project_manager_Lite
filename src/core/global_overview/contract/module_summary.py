from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.global_overview.contract.action_center import (
    ActionCenterContext,
)


@dataclass(frozen=True, slots=True)
class ModuleSummaryDto:
    module_code: str
    title: str
    description: str
    summary_text: str
    route_id: str


class ModuleSummaryContributor(Protocol):
    def get_summary(self, context: ActionCenterContext) -> ModuleSummaryDto | None: ...


__all__ = ["ModuleSummaryContributor", "ModuleSummaryDto"]
