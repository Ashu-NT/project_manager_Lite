from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PortfolioScenarioResponse:
    id: str
    name: str
    budget_limit: Decimal | None
    capacity_limit_percent: float | None
    project_ids: tuple[str, ...]
    intake_item_ids: tuple[str, ...]
    notes: str
    created_at: datetime
    updated_at: datetime
