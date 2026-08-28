from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.financials.configuration import (
    ProjectFinancialProfile,
)


@dataclass(frozen=True, slots=True)
class ProjectFinanceSetupRead:
    project_id: str
    profile: ProjectFinancialProfile
    default_cost_code: str


__all__ = ["ProjectFinanceSetupRead"]
