from __future__ import annotations

import json

from core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioProjectDependency,
    PortfolioScoringTemplate,
    PortfolioScenario,
)
from src.infra.persistence.orm.platform.models import (
    PortfolioIntakeItemORM,
    PortfolioProjectDependencyORM,
    PortfolioScoringTemplateORM,
    PortfolioScenarioORM,
)
from core.modules.project_management.domain.enums import DependencyType


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
        scoring_template_id=item.scoring_template_id,
        scoring_template_name=item.scoring_template_name,
        strategic_weight=item.strategic_weight,
        value_weight=item.value_weight,
        urgency_weight=item.urgency_weight,
        risk_weight=item.risk_weight,
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
        scoring_template_id=getattr(obj, "scoring_template_id", ""),
        scoring_template_name=getattr(obj, "scoring_template_name", "Balanced PMO"),
        strategic_weight=getattr(obj, "strategic_weight", 3),
        value_weight=getattr(obj, "value_weight", 2),
        urgency_weight=getattr(obj, "urgency_weight", 2),
        risk_weight=getattr(obj, "risk_weight", 1),
        status=PortfolioIntakeStatus(obj.status),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        version=getattr(obj, "version", 1),
    )


def portfolio_scoring_template_to_orm(item: PortfolioScoringTemplate) -> PortfolioScoringTemplateORM:
    return PortfolioScoringTemplateORM(
        id=item.id,
        name=item.name,
        summary=item.summary,
        strategic_weight=item.strategic_weight,
        value_weight=item.value_weight,
        urgency_weight=item.urgency_weight,
        risk_weight=item.risk_weight,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def portfolio_scoring_template_from_orm(obj: PortfolioScoringTemplateORM) -> PortfolioScoringTemplate:
    return PortfolioScoringTemplate(
        id=obj.id,
        name=obj.name,
        summary=obj.summary,
        strategic_weight=obj.strategic_weight,
        value_weight=obj.value_weight,
        urgency_weight=obj.urgency_weight,
        risk_weight=obj.risk_weight,
        is_active=bool(obj.is_active),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
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


def portfolio_project_dependency_to_orm(item: PortfolioProjectDependency) -> PortfolioProjectDependencyORM:
    return PortfolioProjectDependencyORM(
        id=item.id,
        predecessor_project_id=item.predecessor_project_id,
        successor_project_id=item.successor_project_id,
        dependency_type=item.dependency_type.value,
        summary=item.summary,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def portfolio_project_dependency_from_orm(obj: PortfolioProjectDependencyORM) -> PortfolioProjectDependency:
    return PortfolioProjectDependency(
        id=obj.id,
        predecessor_project_id=obj.predecessor_project_id,
        successor_project_id=obj.successor_project_id,
        dependency_type=DependencyType(obj.dependency_type),
        summary=obj.summary,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


__all__ = [
    "portfolio_intake_from_orm",
    "portfolio_intake_to_orm",
    "portfolio_project_dependency_from_orm",
    "portfolio_project_dependency_to_orm",
    "portfolio_scoring_template_from_orm",
    "portfolio_scoring_template_to_orm",
    "portfolio_scenario_from_orm",
    "portfolio_scenario_to_orm",
]
