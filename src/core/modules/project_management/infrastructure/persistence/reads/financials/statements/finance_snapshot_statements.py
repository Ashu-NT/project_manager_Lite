from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from src.core.modules.project_management.infrastructure.persistence.orm.baseline import (
    BaselineTaskORM,
    ProjectBaselineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.commitment import (
    ProjectCommitmentLineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.budget import (
    BudgetLineORM,
    ProjectBudgetORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.cost_entry import (
    ProjectCostEntryORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.planned_cost import (
    ProjectPlannedCostLineORM,
    ProjectPlannedCostVersionORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectFinancialProfileORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.forecast import (
    ForecastLineORM,
    ProjectForecastORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
    ProjectResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)

SqlSelect = Select[tuple[Any, ...]]


def _project_scope(*, tenant_id: str, organization_id: str, project_id: str) -> ColumnElement[bool]:
    return and_(
        ProjectORM.id == project_id,
        ProjectORM.tenant_id == tenant_id,
        ProjectORM.organization_id == organization_id,
    )


def project_fact_statement(*, tenant_id: str, organization_id: str, project_id: str) -> SqlSelect:
    approved_budget_id = (
        select(ProjectBudgetORM.id)
        .where(
            ProjectBudgetORM.tenant_id == ProjectORM.tenant_id,
            ProjectBudgetORM.organization_id == ProjectORM.organization_id,
            ProjectBudgetORM.project_id == ProjectORM.id,
            ProjectBudgetORM.status == "approved",
        )
        .correlate(ProjectORM)
        .scalar_subquery()
    )
    approved_budget = (
        select(func.coalesce(func.sum(BudgetLineORM.amount), 0))
        .join(
            ProjectBudgetORM,
            (ProjectBudgetORM.id == BudgetLineORM.budget_id)
            & (ProjectBudgetORM.tenant_id == BudgetLineORM.tenant_id)
            & (ProjectBudgetORM.organization_id == BudgetLineORM.organization_id)
            & (ProjectBudgetORM.project_id == BudgetLineORM.project_id),
        )
        .where(
            ProjectBudgetORM.tenant_id == ProjectORM.tenant_id,
            ProjectBudgetORM.organization_id == ProjectORM.organization_id,
            ProjectBudgetORM.project_id == ProjectORM.id,
            ProjectBudgetORM.status == "approved",
        )
        .correlate(ProjectORM)
        .scalar_subquery()
    )
    approved_budget_at = (
        select(ProjectBudgetORM.approved_at)
        .where(ProjectBudgetORM.id == approved_budget_id)
        .scalar_subquery()
    )
    return select(
        ProjectORM.id,
        ProjectORM.tenant_id,
        ProjectORM.organization_id,
        ProjectFinancialProfileORM.currency_code,
        approved_budget.label("approved_budget"),
        approved_budget_id.label("approved_budget_id"),
        select(ProjectBudgetORM.revision)
        .where(ProjectBudgetORM.id == approved_budget_id)
        .scalar_subquery()
        .label("approved_budget_revision"),
        approved_budget_at.label("approved_budget_at"),
        ProjectORM.start_date,
        ProjectORM.end_date,
    ).join(
        ProjectFinancialProfileORM,
        (ProjectFinancialProfileORM.project_id == ProjectORM.id)
        & (ProjectFinancialProfileORM.tenant_id == ProjectORM.tenant_id)
        & (ProjectFinancialProfileORM.organization_id == ProjectORM.organization_id),
    ).where(_project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id))


def approved_forecast_facts_statement(
    *, tenant_id: str, organization_id: str, project_id: str, as_of: date
) -> SqlSelect:
    return (
        select(
            ProjectForecastORM.id,
            ProjectForecastORM.revision,
            ProjectForecastORM.name,
            ProjectForecastORM.currency_code,
            ProjectForecastORM.as_of_date,
        )
        .join(ProjectORM, ProjectORM.id == ProjectForecastORM.project_id)
        .where(
            ProjectForecastORM.tenant_id == tenant_id,
            ProjectForecastORM.organization_id == organization_id,
            ProjectForecastORM.project_id == project_id,
            ProjectForecastORM.status.in_(("approved", "superseded")),
            ProjectForecastORM.as_of_date <= as_of,
            _project_scope(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            ),
        )
        .order_by(
            ProjectForecastORM.as_of_date.desc(),
            ProjectForecastORM.revision.desc(),
        )
        .limit(1)
    )


def approved_forecast_line_facts_statement(
    *, tenant_id: str, organization_id: str, project_id: str, forecast_id: str
) -> SqlSelect:
    return (
        select(
            ForecastLineORM.id,
            ForecastLineORM.task_id,
            ForecastLineORM.cost_code_id,
            ForecastLineORM.description,
            ForecastLineORM.amount,
            ForecastLineORM.currency_code,
            ForecastLineORM.source_type,
            ForecastLineORM.source_reference_type,
            ForecastLineORM.source_reference_id,
            ForecastLineORM.period_start,
            ForecastLineORM.period_end,
            ProjectForecastORM.as_of_date,
        )
        .join(ProjectForecastORM, ProjectForecastORM.id == ForecastLineORM.forecast_id)
        .join(ProjectORM, ProjectORM.id == ForecastLineORM.project_id)
        .where(
            ForecastLineORM.tenant_id == tenant_id,
            ForecastLineORM.organization_id == organization_id,
            ForecastLineORM.project_id == project_id,
            ForecastLineORM.forecast_id == forecast_id,
            _project_scope(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            ),
        )
        .order_by(ForecastLineORM.period_start, ForecastLineORM.id)
    )


def approved_forecast_total_statement(
    *,
    tenant_id: str,
    organization_id: str,
    project_id: str,
    forecast_id: str,
    project_currency: str,
) -> SqlSelect:
    currency_matches = func.upper(ForecastLineORM.currency_code) == project_currency
    return (
        select(
            func.coalesce(
                func.sum(case((currency_matches, ForecastLineORM.amount), else_=0)),
                0,
            ).label("total_amount"),
            func.coalesce(
                func.sum(case((currency_matches, 0), else_=1)),
                0,
            ).label("currency_mismatch_count"),
        )
        .join(ProjectForecastORM, ProjectForecastORM.id == ForecastLineORM.forecast_id)
        .join(ProjectORM, ProjectORM.id == ForecastLineORM.project_id)
        .where(
            ForecastLineORM.tenant_id == tenant_id,
            ForecastLineORM.organization_id == organization_id,
            ForecastLineORM.project_id == project_id,
            ForecastLineORM.forecast_id == forecast_id,
            ProjectForecastORM.tenant_id == tenant_id,
            ProjectForecastORM.organization_id == organization_id,
            ProjectForecastORM.project_id == project_id,
            _project_scope(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            ),
        )
    )


def task_facts_statement(*, tenant_id: str, organization_id: str, project_id: str) -> SqlSelect:
    return (
        select(
            TaskORM.id,
            TaskORM.name,
            TaskORM.percent_complete,
            TaskORM.start_date,
            TaskORM.end_date,
            TaskORM.actual_start,
            TaskORM.actual_end,
        )
        .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
        .where(_project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id))
        .order_by(TaskORM.id)
    )


def evm_baseline_statement(
    *, tenant_id: str, organization_id: str, project_id: str, baseline_id: str | None
) -> SqlSelect:
    stmt = (
        select(ProjectBaselineORM.id)
        .join(ProjectORM, ProjectORM.id == ProjectBaselineORM.project_id)
        .where(_project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id))
    )
    if baseline_id is not None:
        return stmt.where(ProjectBaselineORM.id == baseline_id)
    return stmt.order_by(ProjectBaselineORM.created_at.desc()).limit(1)


def evm_baseline_task_facts_statement(
    *, tenant_id: str, organization_id: str, project_id: str, baseline_id: str
) -> SqlSelect:
    return (
        select(
            BaselineTaskORM.task_id,
            BaselineTaskORM.baseline_start,
            BaselineTaskORM.baseline_finish,
            BaselineTaskORM.baseline_duration_days,
            BaselineTaskORM.baseline_planned_cost,
        )
        .join(ProjectBaselineORM, ProjectBaselineORM.id == BaselineTaskORM.baseline_id)
        .join(ProjectORM, ProjectORM.id == ProjectBaselineORM.project_id)
        .where(
            BaselineTaskORM.baseline_id == baseline_id,
            _project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id),
        )
        .order_by(BaselineTaskORM.task_id)
    )


def planned_cost_facts_statement(
    *, tenant_id: str, organization_id: str, project_id: str, as_of: date
) -> SqlSelect:
    version_id = (
        select(ProjectPlannedCostVersionORM.id)
        .join(ProjectORM, ProjectORM.id == ProjectPlannedCostVersionORM.project_id)
        .where(
            ProjectPlannedCostVersionORM.tenant_id == tenant_id,
            ProjectPlannedCostVersionORM.organization_id == organization_id,
            ProjectPlannedCostVersionORM.project_id == project_id,
            ProjectPlannedCostVersionORM.as_of <= as_of,
            _project_scope(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            ),
        )
        .order_by(ProjectPlannedCostVersionORM.as_of.desc(), ProjectPlannedCostVersionORM.revision.desc())
        .limit(1)
        .scalar_subquery()
    )
    return (
        select(
            ProjectPlannedCostLineORM.id,
            ProjectPlannedCostLineORM.task_id,
            ProjectPlannedCostLineORM.resource_id,
            ProjectPlannedCostLineORM.source_assignment_id,
            ProjectPlannedCostLineORM.cost_code_id,
            ProjectPlannedCostLineORM.currency_code,
            ProjectPlannedCostLineORM.amount,
            ProjectPlannedCostVersionORM.as_of,
        )
        .join(ProjectPlannedCostVersionORM, ProjectPlannedCostVersionORM.id == ProjectPlannedCostLineORM.version_id)
        .join(ProjectORM, ProjectORM.id == ProjectPlannedCostLineORM.project_id)
        .where(
            ProjectPlannedCostLineORM.tenant_id == tenant_id,
            ProjectPlannedCostLineORM.organization_id == organization_id,
            ProjectPlannedCostLineORM.project_id == project_id,
            ProjectPlannedCostLineORM.version_id == version_id,
            _project_scope(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            ),
        )
        .order_by(ProjectPlannedCostLineORM.id)
    )


def commitment_facts_statement(
    *, tenant_id: str, organization_id: str, project_id: str, as_of: date
) -> SqlSelect:
    return (
        select(
            ProjectCommitmentLineORM.id,
            ProjectCommitmentLineORM.task_id,
            ProjectCommitmentLineORM.purchase_order_line_id,
            ProjectCommitmentLineORM.cost_code_id,
            ProjectCommitmentLineORM.state,
            ProjectCommitmentLineORM.currency_code,
            ProjectCommitmentLineORM.amount,
            ProjectCommitmentLineORM.base_currency_code,
            ProjectCommitmentLineORM.base_amount,
            ProjectCommitmentLineORM.exchange_rate,
            ProjectCommitmentLineORM.matched_amount,
            ProjectCommitmentLineORM.order_date,
        )
        .join(ProjectORM, ProjectORM.id == ProjectCommitmentLineORM.project_id)
        .where(
            ProjectCommitmentLineORM.tenant_id == tenant_id,
            ProjectCommitmentLineORM.organization_id == organization_id,
            ProjectCommitmentLineORM.project_id == project_id,
            _project_scope(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            ),
            ProjectCommitmentLineORM.state != "cancelled",
            or_(ProjectCommitmentLineORM.order_date.is_(None), ProjectCommitmentLineORM.order_date <= as_of),
        )
        .order_by(ProjectCommitmentLineORM.id)
    )


def actual_cost_facts_statement(
    *, tenant_id: str, organization_id: str, project_id: str, as_of: date
) -> SqlSelect:
    cost_type = case(
        (ProjectCostEntryORM.posting_purpose == "labor_actual", literal("LABOR")),
        (ProjectCostEntryORM.posting_purpose == "receipt_accrual", literal("MATERIAL")),
        else_=literal("OTHER"),
    )
    source_key = case(
        (ProjectCostEntryORM.posting_purpose == "labor_actual", literal("APPROVED_TIME")),
        (ProjectCostEntryORM.posting_purpose == "receipt_accrual", literal("PROCUREMENT_ACTUAL")),
        else_=literal("MANUAL_ACTUAL"),
    )
    return (
        select(
            ProjectCostEntryORM.id,
            ProjectCostEntryORM.task_id,
            ProjectCostEntryORM.resource_id,
            ProjectCostEntryORM.description,
            ProjectCostEntryORM.cost_code_id,
            ProjectCostEntryORM.currency_code,
            ProjectCostEntryORM.amount,
            ProjectCostEntryORM.base_currency_code,
            ProjectCostEntryORM.base_amount,
            ProjectCostEntryORM.posting_date,
            ProjectCostEntryORM.financial_period_id,
            cost_type.label("cost_type"),
            source_key.label("source_key"),
        )
        .join(ProjectORM, ProjectORM.id == ProjectCostEntryORM.project_id)
        .where(
            ProjectCostEntryORM.tenant_id == tenant_id,
            ProjectCostEntryORM.organization_id == organization_id,
            ProjectCostEntryORM.project_id == project_id,
            _project_scope(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            ),
            ProjectCostEntryORM.status.in_(("posted", "reversed")),
            ProjectCostEntryORM.posting_date <= as_of,
        )
        .order_by(ProjectCostEntryORM.posting_date, ProjectCostEntryORM.id)
    )


def actual_cost_total_statement(
    *,
    tenant_id: str,
    organization_id: str,
    project_id: str,
    as_of: date,
    project_currency: str,
) -> SqlSelect:
    transaction_matches = func.upper(ProjectCostEntryORM.currency_code) == project_currency
    base_matches = and_(
        func.upper(ProjectCostEntryORM.base_currency_code) == project_currency,
        ProjectCostEntryORM.base_amount.is_not(None),
    )
    amount = case(
        (transaction_matches, ProjectCostEntryORM.amount),
        (base_matches, ProjectCostEntryORM.base_amount),
        else_=0,
    )
    currency_matches = or_(transaction_matches, base_matches)
    return (
        select(
            func.coalesce(func.sum(amount), 0).label("total_amount"),
            func.coalesce(
                func.sum(case((currency_matches, 0), else_=1)),
                0,
            ).label("currency_mismatch_count"),
        )
        .join(ProjectORM, ProjectORM.id == ProjectCostEntryORM.project_id)
        .where(
            ProjectCostEntryORM.tenant_id == tenant_id,
            ProjectCostEntryORM.organization_id == organization_id,
            ProjectCostEntryORM.project_id == project_id,
            ProjectCostEntryORM.status.in_(("posted", "reversed")),
            ProjectCostEntryORM.posting_date <= as_of,
            _project_scope(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            ),
        )
    )


def commitment_total_statement(
    *,
    tenant_id: str,
    organization_id: str,
    project_id: str,
    as_of: date,
    project_currency: str,
) -> SqlSelect:
    transaction_matches = func.upper(ProjectCommitmentLineORM.currency_code) == project_currency
    base_matches = func.upper(ProjectCommitmentLineORM.base_currency_code) == project_currency
    transaction_remaining = ProjectCommitmentLineORM.amount - ProjectCommitmentLineORM.matched_amount
    base_remaining = (
        ProjectCommitmentLineORM.base_amount
        - ProjectCommitmentLineORM.matched_amount * ProjectCommitmentLineORM.exchange_rate
    )
    amount = case(
        (
            transaction_matches,
            case((transaction_remaining > 0, transaction_remaining), else_=0),
        ),
        (
            base_matches,
            case((base_remaining > 0, base_remaining), else_=0),
        ),
        else_=0,
    )
    currency_matches = or_(transaction_matches, base_matches)
    return (
        select(
            func.coalesce(func.sum(amount), 0).label("total_amount"),
            func.coalesce(
                func.sum(case((currency_matches, 0), else_=1)),
                0,
            ).label("currency_mismatch_count"),
        )
        .join(ProjectORM, ProjectORM.id == ProjectCommitmentLineORM.project_id)
        .where(
            ProjectCommitmentLineORM.tenant_id == tenant_id,
            ProjectCommitmentLineORM.organization_id == organization_id,
            ProjectCommitmentLineORM.project_id == project_id,
            ProjectCommitmentLineORM.state.not_in(("closed", "cancelled")),
            or_(
                ProjectCommitmentLineORM.order_date.is_(None),
                ProjectCommitmentLineORM.order_date <= as_of,
            ),
            _project_scope(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            ),
        )
    )


def project_resource_facts_statement(*, tenant_id: str, organization_id: str, project_id: str) -> SqlSelect:
    return (
        select(ProjectResourceORM.id, ProjectResourceORM.resource_id, ProjectResourceORM.planned_hours, ProjectResourceORM.is_active)
        .join(ProjectORM, ProjectORM.id == ProjectResourceORM.project_id)
        .where(_project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id))
        .order_by(ProjectResourceORM.id)
    )


def assignment_facts_statement(*, tenant_id: str, organization_id: str, project_id: str) -> SqlSelect:
    return (
        select(TaskAssignmentORM.id, TaskAssignmentORM.task_id, TaskAssignmentORM.resource_id, TaskAssignmentORM.hours_logged)
        .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
        .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
        .where(_project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id))
        .order_by(TaskAssignmentORM.id)
    )


def resource_facts_statement(
    *, tenant_id: str, organization_id: str, project_id: str, resource_ids: tuple[str, ...]
) -> SqlSelect:
    project_resource_exists = (
        select(ProjectResourceORM.id)
        .join(ProjectORM, ProjectORM.id == ProjectResourceORM.project_id)
        .where(
            ProjectResourceORM.resource_id == ResourceORM.id,
            _project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id),
        )
        .exists()
    )
    assignment_exists = (
        select(TaskAssignmentORM.id)
        .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
        .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
        .where(
            TaskAssignmentORM.resource_id == ResourceORM.id,
            _project_scope(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id),
        )
        .exists()
    )
    return (
        select(ResourceORM.id, ResourceORM.name, ResourceORM.is_active)
        .where(
            ResourceORM.tenant_id == tenant_id,
            ResourceORM.organization_id == organization_id,
            ResourceORM.id.in_(resource_ids),
            or_(project_resource_exists, assignment_exists),
        )
        .order_by(ResourceORM.id)
    )


__all__ = [
    "approved_forecast_facts_statement",
    "approved_forecast_line_facts_statement",
    "approved_forecast_total_statement",
    "actual_cost_facts_statement",
    "actual_cost_total_statement",
    "assignment_facts_statement",
    "commitment_facts_statement",
    "commitment_total_statement",
    "evm_baseline_statement",
    "evm_baseline_task_facts_statement",
    "planned_cost_facts_statement",
    "project_fact_statement",
    "project_resource_facts_statement",
    "resource_facts_statement",
    "task_facts_statement",
]
