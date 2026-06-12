from __future__ import annotations


from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from src.core.modules.project_management.contracts.repositories.portfolio import (
    PortfolioIntakeRepository,
    PortfolioProjectDependencyRepository,
    PortfolioScoringTemplateRepository,
    PortfolioScenarioRepository,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioProjectDependency,
    PortfolioScoringTemplate,
    PortfolioScenario,
)
from src.core.modules.project_management.infrastructure.persistence.orm.portfolio import (
    PortfolioIntakeItemORM,
    PortfolioProjectDependencyORM,
    PortfolioScoringTemplateORM,
    PortfolioScenarioORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.modules.project_management.infrastructure.persistence.mappers.portfolio import (
    portfolio_intake_from_orm,
    portfolio_intake_to_orm,
    portfolio_project_dependency_from_orm,
    portfolio_project_dependency_to_orm,
    portfolio_scoring_template_from_orm,
    portfolio_scoring_template_to_orm,
    portfolio_scenario_from_orm,
    portfolio_scenario_to_orm,
)


class SqlAlchemyPortfolioIntakeRepository(PortfolioIntakeRepository):
    def __init__(self, session: Session, *, tenant_id_provider=None):
        self.session = session
        self._tenant_id_provider = tenant_id_provider or (lambda: None)

    def add(self, item: PortfolioIntakeItem) -> None:
        orm = portfolio_intake_to_orm(item)
        if orm.tenant_id is None:
            orm.tenant_id = self._tenant_id_provider()
        self.session.add(orm)

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
                "scoring_template_id": item.scoring_template_id,
                "scoring_template_name": item.scoring_template_name,
                "strategic_weight": item.strategic_weight,
                "value_weight": item.value_weight,
                "urgency_weight": item.urgency_weight,
                "risk_weight": item.risk_weight,
                "status": item.status.value,
                "updated_at": item.updated_at,
            },
            not_found_message="Portfolio intake item not found.",
            stale_message="Portfolio intake item was updated by another user.",
        )

    def get(self, item_id: str) -> PortfolioIntakeItem | None:
        obj = self.session.get(PortfolioIntakeItemORM, item_id)
        if obj is None:
            return None
        _tid = self._tenant_id_provider()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return portfolio_intake_from_orm(obj)

    def get_for_organization(self, item_id: str, organization_id: str) -> PortfolioIntakeItem | None:
        _tid = self._tenant_id_provider()
        stmt = select(PortfolioIntakeItemORM).where(
            PortfolioIntakeItemORM.id == item_id,
            PortfolioIntakeItemORM.organization_id == organization_id,
        )
        if _tid is not None:
            stmt = stmt.where(PortfolioIntakeItemORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalars().first()
        return portfolio_intake_from_orm(obj) if obj else None

    def list_for_organization(self, organization_id: str) -> list[PortfolioIntakeItem]:
        _tid = self._tenant_id_provider()
        stmt = (
            select(PortfolioIntakeItemORM)
            .where(PortfolioIntakeItemORM.organization_id == organization_id)
            .order_by(PortfolioIntakeItemORM.updated_at.desc())
        )
        if _tid is not None:
            stmt = stmt.where(PortfolioIntakeItemORM.tenant_id == _tid)
        rows = self.session.execute(stmt).scalars().all()
        return [portfolio_intake_from_orm(row) for row in rows]

    def delete(self, item_id: str) -> None:
        obj = self.session.get(PortfolioIntakeItemORM, item_id)
        if obj is not None:
            self.session.delete(obj)


class SqlAlchemyPortfolioScenarioRepository(PortfolioScenarioRepository):
    def __init__(self, session: Session, *, tenant_id_provider=None):
        self.session = session
        self._tenant_id_provider = tenant_id_provider or (lambda: None)

    def add(self, scenario: PortfolioScenario) -> None:
        orm = portfolio_scenario_to_orm(scenario)
        if orm.tenant_id is None:
            orm.tenant_id = self._tenant_id_provider()
        self.session.add(orm)

    def update(self, scenario: PortfolioScenario) -> None:
        orm = portfolio_scenario_to_orm(scenario)
        if orm.tenant_id is None:
            existing = self.session.get(PortfolioScenarioORM, scenario.id)
            orm.tenant_id = (existing.tenant_id if existing is not None else None) or self._tenant_id_provider()
        self.session.merge(orm)

    def get(self, scenario_id: str) -> PortfolioScenario | None:
        obj = self.session.get(PortfolioScenarioORM, scenario_id)
        if obj is None:
            return None
        _tid = self._tenant_id_provider()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return portfolio_scenario_from_orm(obj)

    def get_for_organization(self, scenario_id: str, organization_id: str) -> PortfolioScenario | None:
        _tid = self._tenant_id_provider()
        stmt = select(PortfolioScenarioORM).where(
            PortfolioScenarioORM.id == scenario_id,
            PortfolioScenarioORM.organization_id == organization_id,
        )
        if _tid is not None:
            stmt = stmt.where(PortfolioScenarioORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalars().first()
        return portfolio_scenario_from_orm(obj) if obj else None

    def list_for_organization(self, organization_id: str) -> list[PortfolioScenario]:
        _tid = self._tenant_id_provider()
        stmt = (
            select(PortfolioScenarioORM)
            .where(PortfolioScenarioORM.organization_id == organization_id)
            .order_by(PortfolioScenarioORM.updated_at.desc())
        )
        if _tid is not None:
            stmt = stmt.where(PortfolioScenarioORM.tenant_id == _tid)
        rows = self.session.execute(stmt).scalars().all()
        return [portfolio_scenario_from_orm(row) for row in rows]

    def delete(self, scenario_id: str) -> None:
        obj = self.session.get(PortfolioScenarioORM, scenario_id)
        if obj is not None:
            self.session.delete(obj)


class SqlAlchemyPortfolioProjectDependencyRepository(PortfolioProjectDependencyRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, dependency: PortfolioProjectDependency) -> None:
        self.session.add(portfolio_project_dependency_to_orm(dependency))

    def get_for_organization(
        self,
        dependency_id: str,
        organization_id: str,
    ) -> PortfolioProjectDependency | None:
        predecessor = aliased(ProjectORM)
        successor = aliased(ProjectORM)
        stmt = (
            select(PortfolioProjectDependencyORM)
            .join(predecessor, predecessor.id == PortfolioProjectDependencyORM.predecessor_project_id)
            .join(successor, successor.id == PortfolioProjectDependencyORM.successor_project_id)
            .where(
                PortfolioProjectDependencyORM.id == dependency_id,
                predecessor.organization_id == organization_id,
                successor.organization_id == organization_id,
            )
        )
        obj = self.session.execute(stmt).scalars().first()
        return portfolio_project_dependency_from_orm(obj) if obj else None

    def list_for_organization(self, organization_id: str) -> list[PortfolioProjectDependency]:
        predecessor = aliased(ProjectORM)
        successor = aliased(ProjectORM)
        stmt = (
            select(PortfolioProjectDependencyORM)
            .join(predecessor, predecessor.id == PortfolioProjectDependencyORM.predecessor_project_id)
            .join(successor, successor.id == PortfolioProjectDependencyORM.successor_project_id)
            .where(
                predecessor.organization_id == organization_id,
                successor.organization_id == organization_id,
            )
            .order_by(
                PortfolioProjectDependencyORM.updated_at.desc(),
                PortfolioProjectDependencyORM.created_at.desc(),
            )
        )
        rows = self.session.execute(stmt).scalars().all()
        return [portfolio_project_dependency_from_orm(row) for row in rows]

    def delete_for_organization(self, dependency_id: str, organization_id: str) -> None:
        predecessor = aliased(ProjectORM)
        successor = aliased(ProjectORM)
        stmt = (
            select(PortfolioProjectDependencyORM)
            .join(predecessor, predecessor.id == PortfolioProjectDependencyORM.predecessor_project_id)
            .join(successor, successor.id == PortfolioProjectDependencyORM.successor_project_id)
            .where(
                PortfolioProjectDependencyORM.id == dependency_id,
                predecessor.organization_id == organization_id,
                successor.organization_id == organization_id,
            )
        )
        obj = self.session.execute(stmt).scalars().first()
        if obj is not None:
            self.session.delete(obj)


class SqlAlchemyPortfolioScoringTemplateRepository(PortfolioScoringTemplateRepository):
    def __init__(self, session: Session, *, tenant_id_provider=None):
        self.session = session
        self._tenant_id_provider = tenant_id_provider or (lambda: None)

    def add(self, template: PortfolioScoringTemplate) -> None:
        orm = portfolio_scoring_template_to_orm(template)
        if orm.tenant_id is None:
            orm.tenant_id = self._tenant_id_provider()
        self.session.add(orm)

    def update(self, template: PortfolioScoringTemplate) -> None:
        orm = portfolio_scoring_template_to_orm(template)
        if orm.tenant_id is None:
            existing = self.session.get(PortfolioScoringTemplateORM, template.id)
            orm.tenant_id = (existing.tenant_id if existing is not None else None) or self._tenant_id_provider()
        self.session.merge(orm)

    def get(self, template_id: str) -> PortfolioScoringTemplate | None:
        obj = self.session.get(PortfolioScoringTemplateORM, template_id)
        if obj is None:
            return None
        _tid = self._tenant_id_provider()
        if _tid is not None and obj.tenant_id != _tid:
            return None
        return portfolio_scoring_template_from_orm(obj)

    def get_for_organization(self, template_id: str, organization_id: str) -> PortfolioScoringTemplate | None:
        _tid = self._tenant_id_provider()
        stmt = select(PortfolioScoringTemplateORM).where(
            PortfolioScoringTemplateORM.id == template_id,
            PortfolioScoringTemplateORM.organization_id == organization_id,
        )
        if _tid is not None:
            stmt = stmt.where(PortfolioScoringTemplateORM.tenant_id == _tid)
        obj = self.session.execute(stmt).scalars().first()
        return portfolio_scoring_template_from_orm(obj) if obj else None

    def list_for_organization(self, organization_id: str) -> list[PortfolioScoringTemplate]:
        _tid = self._tenant_id_provider()
        stmt = (
            select(PortfolioScoringTemplateORM)
            .where(PortfolioScoringTemplateORM.organization_id == organization_id)
            .order_by(
                PortfolioScoringTemplateORM.is_active.desc(),
                PortfolioScoringTemplateORM.updated_at.desc(),
                PortfolioScoringTemplateORM.name.asc(),
            )
        )
        if _tid is not None:
            stmt = stmt.where(PortfolioScoringTemplateORM.tenant_id == _tid)
        rows = self.session.execute(stmt).scalars().all()
        return [portfolio_scoring_template_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyPortfolioIntakeRepository",
    "SqlAlchemyPortfolioProjectDependencyRepository",
    "SqlAlchemyPortfolioScoringTemplateRepository",
    "SqlAlchemyPortfolioScenarioRepository",
]
