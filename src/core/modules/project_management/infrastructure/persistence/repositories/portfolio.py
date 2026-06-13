from __future__ import annotations

from sqlalchemy import delete, select
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
from src.core.modules.project_management.infrastructure.persistence.orm.portfolio import (
    PortfolioIntakeItemORM,
    PortfolioProjectDependencyORM,
    PortfolioScoringTemplateORM,
    PortfolioScenarioORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.repositories._tenant_scope import (
    ProjectManagementParentScopedRepositorySupport,
    ProjectManagementTenantScopedRepositorySupport,
)
from src.core.platform.tenancy.tenant_context import TenantContextService
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyPortfolioIntakeRepository(
    ProjectManagementTenantScopedRepositorySupport,
    PortfolioIntakeRepository,
):
    _repository_label = "Portfolio intake repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _scoped_stmt(self, *, operation_label: str):
        ctx = self._context(operation_label=operation_label)
        return self._apply_scope(select(PortfolioIntakeItemORM), PortfolioIntakeItemORM, ctx)

    def add(self, item: PortfolioIntakeItem) -> None:
        ctx = self._context(operation_label="manage portfolio intake")
        orm = portfolio_intake_to_orm(item)
        self._stamp_scope(ctx, orm)
        item.organization_id = orm.organization_id
        self.session.add(orm)

    def update(self, item: PortfolioIntakeItem) -> None:
        ctx = self._context(operation_label="manage portfolio intake")
        orm = portfolio_intake_to_orm(item)
        self._stamp_scope(ctx, orm)
        item.organization_id = orm.organization_id
        extra_filters = {"organization_id": ctx.organization_id}
        active_tenant_id = getattr(ctx, "tenant_id", None)
        if active_tenant_id is not None:
            extra_filters["tenant_id"] = active_tenant_id
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
            extra_filters=extra_filters,
            not_found_message="Portfolio intake item not found.",
            stale_message="Portfolio intake item was updated by another user.",
        )

    def get(self, item_id: str) -> PortfolioIntakeItem | None:
        obj = self._get_in_scope(
            PortfolioIntakeItemORM,
            item_id,
            operation_label="access portfolio intake",
        )
        return portfolio_intake_from_orm(obj) if obj else None

    def get_for_organization(self, item_id: str, organization_id: str) -> PortfolioIntakeItem | None:
        ctx = self._context(operation_label="access portfolio intake")
        if organization_id != ctx.organization_id:
            return None
        return self.get(item_id)

    def list_for_organization(self, organization_id: str) -> list[PortfolioIntakeItem]:
        ctx = self._context(operation_label="access portfolio intake")
        if organization_id != ctx.organization_id:
            return []
        stmt = self._apply_scope(
            select(PortfolioIntakeItemORM)
            .where(PortfolioIntakeItemORM.organization_id == organization_id)
            .order_by(PortfolioIntakeItemORM.updated_at.desc()),
            PortfolioIntakeItemORM,
            ctx,
        )
        rows = self.session.execute(stmt).scalars().all()
        return [portfolio_intake_from_orm(row) for row in rows]

    def delete(self, item_id: str) -> None:
        scoped_ids = (
            self._scoped_stmt(operation_label="manage portfolio intake")
            .where(PortfolioIntakeItemORM.id == item_id)
            .with_only_columns(PortfolioIntakeItemORM.id)
            .scalar_subquery()
        )
        self.session.execute(
            delete(PortfolioIntakeItemORM).where(PortfolioIntakeItemORM.id == scoped_ids)
        )


class SqlAlchemyPortfolioScenarioRepository(
    ProjectManagementTenantScopedRepositorySupport,
    PortfolioScenarioRepository,
):
    _repository_label = "Portfolio scenario repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _scoped_stmt(self, *, operation_label: str):
        ctx = self._context(operation_label=operation_label)
        return self._apply_scope(select(PortfolioScenarioORM), PortfolioScenarioORM, ctx)

    def add(self, scenario: PortfolioScenario) -> None:
        ctx = self._context(operation_label="manage portfolio scenarios")
        orm = portfolio_scenario_to_orm(scenario)
        self._stamp_scope(ctx, orm)
        scenario.organization_id = orm.organization_id
        self.session.add(orm)

    def update(self, scenario: PortfolioScenario) -> None:
        ctx = self._context(operation_label="manage portfolio scenarios")
        orm = portfolio_scenario_to_orm(scenario)
        self._stamp_scope(ctx, orm)
        scenario.organization_id = orm.organization_id
        row = self._require_in_scope(
            PortfolioScenarioORM,
            scenario.id,
            operation_label="manage portfolio scenarios",
            not_found_message="Portfolio scenario not found.",
        )
        row.organization_id = orm.organization_id
        row.tenant_id = orm.tenant_id
        row.name = scenario.name
        row.budget_limit = scenario.budget_limit
        row.capacity_limit_percent = scenario.capacity_limit_percent
        row.project_ids_json = orm.project_ids_json
        row.intake_item_ids_json = orm.intake_item_ids_json
        row.notes = scenario.notes
        row.created_at = scenario.created_at
        row.updated_at = scenario.updated_at

    def get(self, scenario_id: str) -> PortfolioScenario | None:
        obj = self._get_in_scope(
            PortfolioScenarioORM,
            scenario_id,
            operation_label="access portfolio scenarios",
        )
        return portfolio_scenario_from_orm(obj) if obj else None

    def get_for_organization(self, scenario_id: str, organization_id: str) -> PortfolioScenario | None:
        ctx = self._context(operation_label="access portfolio scenarios")
        if organization_id != ctx.organization_id:
            return None
        return self.get(scenario_id)

    def list_for_organization(self, organization_id: str) -> list[PortfolioScenario]:
        ctx = self._context(operation_label="access portfolio scenarios")
        if organization_id != ctx.organization_id:
            return []
        stmt = self._apply_scope(
            select(PortfolioScenarioORM)
            .where(PortfolioScenarioORM.organization_id == organization_id)
            .order_by(PortfolioScenarioORM.updated_at.desc()),
            PortfolioScenarioORM,
            ctx,
        )
        rows = self.session.execute(stmt).scalars().all()
        return [portfolio_scenario_from_orm(row) for row in rows]

    def delete(self, scenario_id: str) -> None:
        scoped_ids = (
            self._scoped_stmt(operation_label="manage portfolio scenarios")
            .where(PortfolioScenarioORM.id == scenario_id)
            .with_only_columns(PortfolioScenarioORM.id)
            .scalar_subquery()
        )
        self.session.execute(
            delete(PortfolioScenarioORM).where(PortfolioScenarioORM.id == scoped_ids)
        )


class SqlAlchemyPortfolioProjectDependencyRepository(
    ProjectManagementParentScopedRepositorySupport,
    PortfolioProjectDependencyRepository,
):
    _repository_label = "Portfolio project dependency repository"

    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _ensure_project_in_scope(self, project_id: str) -> None:
        self._require_anchor_in_scope(
            ProjectORM,
            project_id,
            operation_label="manage portfolio project dependencies",
            not_found_message="Project not found.",
        )

    def _scoped_stmt(self, *, operation_label: str):
        ctx = self._context(operation_label=operation_label)
        predecessor = aliased(ProjectORM)
        successor = aliased(ProjectORM)
        stmt = (
            select(PortfolioProjectDependencyORM)
            .join(
                predecessor,
                predecessor.id == PortfolioProjectDependencyORM.predecessor_project_id,
            )
            .join(
                successor,
                successor.id == PortfolioProjectDependencyORM.successor_project_id,
            )
            .where(
                predecessor.organization_id == ctx.organization_id,
                successor.organization_id == ctx.organization_id,
            )
        )
        active_tenant_id = getattr(ctx, "tenant_id", None)
        if active_tenant_id is not None:
            stmt = stmt.where(
                predecessor.tenant_id == active_tenant_id,
                successor.tenant_id == active_tenant_id,
            )
        return stmt

    def add(self, dependency: PortfolioProjectDependency) -> None:
        self._ensure_project_in_scope(dependency.predecessor_project_id)
        self._ensure_project_in_scope(dependency.successor_project_id)
        self.session.add(portfolio_project_dependency_to_orm(dependency))

    def get_for_organization(
        self,
        dependency_id: str,
        organization_id: str,
    ) -> PortfolioProjectDependency | None:
        ctx = self._context(operation_label="access portfolio project dependencies")
        if organization_id != ctx.organization_id:
            return None
        stmt = self._scoped_stmt(
            operation_label="access portfolio project dependencies"
        ).where(PortfolioProjectDependencyORM.id == dependency_id)
        obj = self.session.execute(stmt).scalars().first()
        return portfolio_project_dependency_from_orm(obj) if obj else None

    def list_for_organization(self, organization_id: str) -> list[PortfolioProjectDependency]:
        ctx = self._context(operation_label="access portfolio project dependencies")
        if organization_id != ctx.organization_id:
            return []
        stmt = self._scoped_stmt(
            operation_label="access portfolio project dependencies"
        ).order_by(
            PortfolioProjectDependencyORM.updated_at.desc(),
            PortfolioProjectDependencyORM.created_at.desc(),
        )
        rows = self.session.execute(stmt).scalars().all()
        return [portfolio_project_dependency_from_orm(row) for row in rows]

    def delete_for_organization(self, dependency_id: str, organization_id: str) -> None:
        ctx = self._context(operation_label="manage portfolio project dependencies")
        if organization_id != ctx.organization_id:
            return
        scoped_ids = (
            self._scoped_stmt(operation_label="manage portfolio project dependencies")
            .where(PortfolioProjectDependencyORM.id == dependency_id)
            .with_only_columns(PortfolioProjectDependencyORM.id)
            .scalar_subquery()
        )
        self.session.execute(
            delete(PortfolioProjectDependencyORM).where(
                PortfolioProjectDependencyORM.id == scoped_ids
            )
        )


class SqlAlchemyPortfolioScoringTemplateRepository(
    ProjectManagementTenantScopedRepositorySupport,
    PortfolioScoringTemplateRepository,
):
    _repository_label = "Portfolio scoring template repository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _scoped_stmt(self, *, operation_label: str):
        ctx = self._context(operation_label=operation_label)
        return self._apply_scope(
            select(PortfolioScoringTemplateORM),
            PortfolioScoringTemplateORM,
            ctx,
        )

    def add(self, template: PortfolioScoringTemplate) -> None:
        ctx = self._context(operation_label="manage portfolio scoring templates")
        orm = portfolio_scoring_template_to_orm(template)
        self._stamp_scope(ctx, orm)
        template.organization_id = orm.organization_id
        self.session.add(orm)

    def update(self, template: PortfolioScoringTemplate) -> None:
        ctx = self._context(operation_label="manage portfolio scoring templates")
        orm = portfolio_scoring_template_to_orm(template)
        self._stamp_scope(ctx, orm)
        template.organization_id = orm.organization_id
        row = self._require_in_scope(
            PortfolioScoringTemplateORM,
            template.id,
            operation_label="manage portfolio scoring templates",
            not_found_message="Portfolio scoring template not found.",
        )
        row.organization_id = orm.organization_id
        row.tenant_id = orm.tenant_id
        row.name = template.name
        row.summary = template.summary
        row.strategic_weight = template.strategic_weight
        row.value_weight = template.value_weight
        row.urgency_weight = template.urgency_weight
        row.risk_weight = template.risk_weight
        row.is_active = template.is_active
        row.created_at = template.created_at
        row.updated_at = template.updated_at

    def get(self, template_id: str) -> PortfolioScoringTemplate | None:
        obj = self._get_in_scope(
            PortfolioScoringTemplateORM,
            template_id,
            operation_label="access portfolio scoring templates",
        )
        return portfolio_scoring_template_from_orm(obj) if obj else None

    def get_for_organization(self, template_id: str, organization_id: str) -> PortfolioScoringTemplate | None:
        ctx = self._context(operation_label="access portfolio scoring templates")
        if organization_id != ctx.organization_id:
            return None
        return self.get(template_id)

    def list_for_organization(self, organization_id: str) -> list[PortfolioScoringTemplate]:
        ctx = self._context(operation_label="access portfolio scoring templates")
        if organization_id != ctx.organization_id:
            return []
        stmt = self._apply_scope(
            select(PortfolioScoringTemplateORM)
            .where(PortfolioScoringTemplateORM.organization_id == organization_id)
            .order_by(
                PortfolioScoringTemplateORM.is_active.desc(),
                PortfolioScoringTemplateORM.updated_at.desc(),
                PortfolioScoringTemplateORM.name.asc(),
            ),
            PortfolioScoringTemplateORM,
            ctx,
        )
        rows = self.session.execute(stmt).scalars().all()
        return [portfolio_scoring_template_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyPortfolioIntakeRepository",
    "SqlAlchemyPortfolioProjectDependencyRepository",
    "SqlAlchemyPortfolioScoringTemplateRepository",
    "SqlAlchemyPortfolioScenarioRepository",
]
