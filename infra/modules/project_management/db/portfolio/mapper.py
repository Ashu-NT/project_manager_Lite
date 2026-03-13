from __future__ import annotations

import json

from core.platform.common.models import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioScenario,
)
from infra.platform.db.models import PortfolioIntakeItemORM, PortfolioScenarioORM


def portfolio_intake_to_orm(item: PortfolioIntakeItem) -> PortfolioIntakeItemORM:
    return PortfolioIntakeItemORM(
        id=item.id,
        title=item.title,
        sponsor_name=item.sponsor_name,
        summary=item.summary,
        requested_budget=item.requested_budget,
        requested_capacity_percent=item.requested_capacity_percent,
        target_start_date=item.target_start_date,
        strategic_score=item.strategic_score,
        value_score=item.value_score,
        urgency_score=item.urgency_score,
        risk_score=item.risk_score,
        status=item.status.value,
        created_at=item.created_at,
        updated_at=item.updated_at,
        version=getattr(item, "version", 1),
    )


def portfolio_intake_from_orm(obj: PortfolioIntakeItemORM) -> PortfolioIntakeItem:
    return PortfolioIntakeItem(
        id=obj.id,
        title=obj.title,
        sponsor_name=obj.sponsor_name,
        summary=obj.summary,
        requested_budget=obj.requested_budget,
        requested_capacity_percent=obj.requested_capacity_percent,
        target_start_date=obj.target_start_date,
        strategic_score=obj.strategic_score,
        value_score=obj.value_score,
        urgency_score=obj.urgency_score,
        risk_score=obj.risk_score,
        status=PortfolioIntakeStatus(obj.status),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        version=getattr(obj, "version", 1),
    )


def portfolio_scenario_to_orm(item: PortfolioScenario) -> PortfolioScenarioORM:
    return PortfolioScenarioORM(
        id=item.id,
        name=item.name,
        budget_limit=item.budget_limit,
        capacity_limit_percent=item.capacity_limit_percent,
        project_ids_json=json.dumps(list(item.project_ids or [])),
        intake_item_ids_json=json.dumps(list(item.intake_item_ids or [])),
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def portfolio_scenario_from_orm(obj: PortfolioScenarioORM) -> PortfolioScenario:
    def _decode(value: str | None) -> list[str]:
        try:
            data = json.loads(value or "[]")
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        return [str(item).strip() for item in data if str(item).strip()]

    return PortfolioScenario(
        id=obj.id,
        name=obj.name,
        budget_limit=obj.budget_limit,
        capacity_limit_percent=obj.capacity_limit_percent,
        project_ids=_decode(obj.project_ids_json),
        intake_item_ids=_decode(obj.intake_item_ids_json),
        notes=obj.notes,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


__all__ = [
    "portfolio_intake_from_orm",
    "portfolio_intake_to_orm",
    "portfolio_scenario_from_orm",
    "portfolio_scenario_to_orm",
]
