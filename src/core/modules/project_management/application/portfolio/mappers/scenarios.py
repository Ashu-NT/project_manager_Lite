from src.core.modules.project_management.application.portfolio.dto.responses.scenarios import (
    PortfolioScenarioResponse,
)
from src.core.modules.project_management.domain.portfolio import PortfolioScenario


def map_scenario(scenario: PortfolioScenario) -> PortfolioScenarioResponse:
    return PortfolioScenarioResponse(
        id=scenario.id, name=scenario.name, budget_limit=scenario.budget_limit,
        capacity_limit_percent=scenario.capacity_limit_percent,
        project_ids=tuple(scenario.project_ids), intake_item_ids=tuple(scenario.intake_item_ids),
        notes=scenario.notes, created_at=scenario.created_at, updated_at=scenario.updated_at,
    )
