from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.portfolio.models.scenario_facts import (
    PortfolioScenarioAssignmentFact,
    PortfolioScenarioFact,
    PortfolioScenarioFacts,
    PortfolioScenarioIntakeFact,
    PortfolioScenarioProjectFact,
    PortfolioScenarioResourceFact,
    PortfolioScenarioTaskFact,
)
from src.core.modules.project_management.domain.portfolio import (
    calculate_portfolio_intake_composite_score,
)
from src.core.modules.project_management.infrastructure.persistence.orm.portfolio import (
    PortfolioIntakeItemORM,
    PortfolioScenarioORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)


def _ids_from_json(value: str | None) -> tuple[str, ...]:
    try:
        loaded = json.loads(value or "[]")
    except (TypeError, ValueError):
        return ()
    if not isinstance(loaded, list):
        return ()
    return tuple(str(item).strip() for item in loaded if str(item).strip())


class SqlAlchemyPortfolioScenarioReader:
    """Acquire one scoped fact graph for scenario evaluation or comparison."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_facts(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        scenario_ids: tuple[str, ...],
        accessible_project_ids: tuple[str, ...],
    ) -> PortfolioScenarioFacts:
        scenario_rows = self._session.execute(
            select(
                PortfolioScenarioORM.id,
                PortfolioScenarioORM.name,
                PortfolioScenarioORM.budget_limit,
                PortfolioScenarioORM.capacity_limit_percent,
                PortfolioScenarioORM.project_ids_json,
                PortfolioScenarioORM.intake_item_ids_json,
            ).where(
                PortfolioScenarioORM.tenant_id == tenant_id,
                PortfolioScenarioORM.organization_id == organization_id,
                PortfolioScenarioORM.id.in_(scenario_ids),
            )
        )
        scenarios = tuple(
            PortfolioScenarioFact(
                id=str(row.id),
                name=str(row.name or ""),
                budget_limit=(None if row.budget_limit is None else float(row.budget_limit)),
                capacity_limit_percent=(
                    None
                    if row.capacity_limit_percent is None
                    else float(row.capacity_limit_percent)
                ),
                project_ids=_ids_from_json(row.project_ids_json),
                intake_item_ids=_ids_from_json(row.intake_item_ids_json),
            )
            for row in scenario_rows
        )

        projects: tuple[PortfolioScenarioProjectFact, ...] = ()
        tasks: tuple[PortfolioScenarioTaskFact, ...] = ()
        assignments: tuple[PortfolioScenarioAssignmentFact, ...] = ()
        if accessible_project_ids:
            projects = tuple(
                PortfolioScenarioProjectFact(
                    id=str(row.id),
                    name=str(row.name or ""),
                    planned_budget=float(row.planned_budget or 0.0),
                )
                for row in self._session.execute(
                    select(ProjectORM.id, ProjectORM.name, ProjectORM.planned_budget)
                    .where(
                        ProjectORM.tenant_id == tenant_id,
                        ProjectORM.organization_id == organization_id,
                        ProjectORM.id.in_(accessible_project_ids),
                    )
                    .order_by(ProjectORM.id)
                )
            )
            tasks = tuple(
                PortfolioScenarioTaskFact(
                    id=str(row.id),
                    project_id=str(row.project_id),
                    parent_task_id=(
                        None if row.parent_task_id is None else str(row.parent_task_id)
                    ),
                    start_date=row.start_date,
                    end_date=row.end_date,
                )
                for row in self._session.execute(
                    select(
                        TaskORM.id,
                        TaskORM.project_id,
                        TaskORM.parent_task_id,
                        TaskORM.start_date,
                        TaskORM.end_date,
                    )
                    .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
                    .where(
                        ProjectORM.tenant_id == tenant_id,
                        ProjectORM.organization_id == organization_id,
                        ProjectORM.id.in_(accessible_project_ids),
                    )
                    .order_by(TaskORM.project_id, TaskORM.id)
                )
            )
            assignments = tuple(
                PortfolioScenarioAssignmentFact(
                    task_id=str(row.task_id),
                    resource_id=str(row.resource_id),
                    allocation_percent=float(row.allocation_percent or 0.0),
                )
                for row in self._session.execute(
                    select(
                        TaskAssignmentORM.task_id,
                        TaskAssignmentORM.resource_id,
                        TaskAssignmentORM.allocation_percent,
                    )
                    .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
                    .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
                    .join(ResourceORM, ResourceORM.id == TaskAssignmentORM.resource_id)
                    .where(
                        ProjectORM.tenant_id == tenant_id,
                        ProjectORM.organization_id == organization_id,
                        ProjectORM.id.in_(accessible_project_ids),
                        ResourceORM.tenant_id == tenant_id,
                        ResourceORM.organization_id == organization_id,
                    )
                    .order_by(TaskORM.project_id, TaskAssignmentORM.task_id)
                )
            )

        intake_items = tuple(
            PortfolioScenarioIntakeFact(
                id=str(row.id),
                title=str(row.title or ""),
                requested_budget=float(row.requested_budget or 0.0),
                requested_capacity_percent=float(row.requested_capacity_percent or 0.0),
                composite_score=calculate_portfolio_intake_composite_score(
                    strategic_score=row.strategic_score,
                    value_score=row.value_score,
                    urgency_score=row.urgency_score,
                    risk_score=row.risk_score,
                    strategic_weight=row.strategic_weight,
                    value_weight=row.value_weight,
                    urgency_weight=row.urgency_weight,
                    risk_weight=row.risk_weight,
                ),
            )
            for row in self._session.execute(
                select(
                    PortfolioIntakeItemORM.id,
                    PortfolioIntakeItemORM.title,
                    PortfolioIntakeItemORM.requested_budget,
                    PortfolioIntakeItemORM.requested_capacity_percent,
                    PortfolioIntakeItemORM.strategic_score,
                    PortfolioIntakeItemORM.value_score,
                    PortfolioIntakeItemORM.urgency_score,
                    PortfolioIntakeItemORM.risk_score,
                    PortfolioIntakeItemORM.strategic_weight,
                    PortfolioIntakeItemORM.value_weight,
                    PortfolioIntakeItemORM.urgency_weight,
                    PortfolioIntakeItemORM.risk_weight,
                )
                .where(
                    PortfolioIntakeItemORM.tenant_id == tenant_id,
                    PortfolioIntakeItemORM.organization_id == organization_id,
                )
                .order_by(PortfolioIntakeItemORM.id)
            )
        )
        resources = tuple(
            PortfolioScenarioResourceFact(
                id=str(row.id),
                name=str(row.name or ""),
                capacity_percent=float(row.capacity_percent or 100.0),
                is_active=bool(row.is_active),
            )
            for row in self._session.execute(
                select(
                    ResourceORM.id,
                    ResourceORM.name,
                    ResourceORM.capacity_percent,
                    ResourceORM.is_active,
                )
                .where(
                    ResourceORM.tenant_id == tenant_id,
                    ResourceORM.organization_id == organization_id,
                )
                .order_by(ResourceORM.id)
            )
        )
        return PortfolioScenarioFacts(
            tenant_id=tenant_id,
            organization_id=organization_id,
            scenarios=scenarios,
            projects=projects,
            intake_items=intake_items,
            tasks=tasks,
            assignments=assignments,
            resources=resources,
        )


__all__ = ["SqlAlchemyPortfolioScenarioReader"]
