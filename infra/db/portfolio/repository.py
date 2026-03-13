from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.interfaces import PortfolioIntakeRepository, PortfolioScenarioRepository
from core.models import PortfolioIntakeItem, PortfolioScenario
from infra.db.models import PortfolioIntakeItemORM, PortfolioScenarioORM
from infra.db.optimistic import update_with_version_check
from infra.db.portfolio.mapper import (
    portfolio_intake_from_orm,
    portfolio_intake_to_orm,
    portfolio_scenario_from_orm,
    portfolio_scenario_to_orm,
)


class SqlAlchemyPortfolioIntakeRepository(PortfolioIntakeRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, item: PortfolioIntakeItem) -> None:
        self.session.add(portfolio_intake_to_orm(item))

    def update(self, item: PortfolioIntakeItem) -> None:
        item.version = update_with_version_check(
            self.session,
            PortfolioIntakeItemORM,
            item.id,
            getattr(item, "version", 1),
            {
                "title": item.title,
                "sponsor_name": item.sponsor_name,
                "summary": item.summary,
                "requested_budget": item.requested_budget,
                "requested_capacity_percent": item.requested_capacity_percent,
                "target_start_date": item.target_start_date,
                "strategic_score": item.strategic_score,
                "value_score": item.value_score,
                "urgency_score": item.urgency_score,
                "risk_score": item.risk_score,
                "status": item.status.value,
                "updated_at": item.updated_at,
            },
            not_found_message="Portfolio intake item not found.",
            stale_message="Portfolio intake item was updated by another user.",
        )

    def get(self, item_id: str) -> Optional[PortfolioIntakeItem]:
        obj = self.session.get(PortfolioIntakeItemORM, item_id)
        return portfolio_intake_from_orm(obj) if obj else None

    def list_all(self) -> List[PortfolioIntakeItem]:
        stmt = select(PortfolioIntakeItemORM).order_by(PortfolioIntakeItemORM.updated_at.desc())
        rows = self.session.execute(stmt).scalars().all()
        return [portfolio_intake_from_orm(row) for row in rows]

    def delete(self, item_id: str) -> None:
        obj = self.session.get(PortfolioIntakeItemORM, item_id)
        if obj is not None:
            self.session.delete(obj)


class SqlAlchemyPortfolioScenarioRepository(PortfolioScenarioRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, scenario: PortfolioScenario) -> None:
        self.session.add(portfolio_scenario_to_orm(scenario))

    def update(self, scenario: PortfolioScenario) -> None:
        self.session.merge(portfolio_scenario_to_orm(scenario))

    def get(self, scenario_id: str) -> Optional[PortfolioScenario]:
        obj = self.session.get(PortfolioScenarioORM, scenario_id)
        return portfolio_scenario_from_orm(obj) if obj else None

    def list_all(self) -> List[PortfolioScenario]:
        stmt = select(PortfolioScenarioORM).order_by(PortfolioScenarioORM.updated_at.desc())
        rows = self.session.execute(stmt).scalars().all()
        return [portfolio_scenario_from_orm(row) for row in rows]

    def delete(self, scenario_id: str) -> None:
        obj = self.session.get(PortfolioScenarioORM, scenario_id)
        if obj is not None:
            self.session.delete(obj)


__all__ = [
    "SqlAlchemyPortfolioIntakeRepository",
    "SqlAlchemyPortfolioScenarioRepository",
]
