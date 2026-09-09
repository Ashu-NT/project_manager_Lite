from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.application.global_overview.contracts.action_center import ActionCenterContext


@dataclass(frozen=True, slots=True)
class ModuleSummaryDto:
    module_code: str
    title: str
    description: str
    summary_text: str
    route_id: str


class ModuleSummaryContributor(Protocol):
    def build_summary(self, context: ActionCenterContext) -> ModuleSummaryDto: ...


__all__ = ["ModuleSummaryDto", "ModuleSummaryContributor"]
