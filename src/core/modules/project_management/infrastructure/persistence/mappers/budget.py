from __future__ import annotations

from src.core.modules.project_management.domain.financials.budget import (
    BudgetLine,
    BudgetStatus,
    ProjectBudget,
)
from src.core.modules.project_management.infrastructure.persistence.orm.budget import (
    BudgetLineORM,
    ProjectBudgetORM,
)


def budget_to_orm(budget: ProjectBudget) -> ProjectBudgetORM:
    return ProjectBudgetORM(
        id=budget.id,
        tenant_id=budget.tenant_id,
        organization_id=budget.organization_id,
        project_id=budget.project_id,
        predecessor_budget_id=budget.predecessor_budget_id,
        name=budget.name,
        currency_code=budget.currency_code,
        status=budget.status.value,
        revision=budget.revision,
        version=budget.row_version,
        submitted_by=budget.submitted_by,
        submitted_at=budget.submitted_at,
        approved_by=budget.approved_by,
        approved_at=budget.approved_at,
        rejected_by=budget.rejected_by,
        rejected_at=budget.rejected_at,
        superseded_by=budget.superseded_by,
        superseded_at=budget.superseded_at,
        closed_by=budget.closed_by,
        closed_at=budget.closed_at,
        notes=budget.notes,
        submission_notes=budget.submission_notes,
        approval_notes=budget.approval_notes,
        rejection_notes=budget.rejection_notes,
        closure_notes=budget.closure_notes,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


def budget_from_orm(row: ProjectBudgetORM) -> ProjectBudget:
    return ProjectBudget(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        predecessor_budget_id=row.predecessor_budget_id,
        name=row.name,
        currency_code=row.currency_code,
        status=BudgetStatus(row.status),
        revision=row.revision,
        row_version=row.version,
        submitted_by=row.submitted_by,
        submitted_at=row.submitted_at,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        rejected_by=row.rejected_by,
        rejected_at=row.rejected_at,
        superseded_by=row.superseded_by,
        superseded_at=row.superseded_at,
        closed_by=row.closed_by,
        closed_at=row.closed_at,
        notes=row.notes,
        submission_notes=row.submission_notes,
        approval_notes=row.approval_notes,
        rejection_notes=row.rejection_notes,
        closure_notes=row.closure_notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def budget_line_to_orm(line: BudgetLine) -> BudgetLineORM:
    return BudgetLineORM(
        id=line.id,
        tenant_id=line.tenant_id,
        organization_id=line.organization_id,
        budget_id=line.budget_id,
        project_id=line.project_id,
        cost_code_id=line.cost_code_id,
        task_id=line.task_id,
        description=line.description,
        amount=line.amount,
        currency_code=line.currency_code,
        version=line.row_version,
        created_at=line.created_at,
        updated_at=line.updated_at,
    )


def budget_line_from_orm(row: BudgetLineORM) -> BudgetLine:
    return BudgetLine(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        budget_id=row.budget_id,
        project_id=row.project_id,
        cost_code_id=row.cost_code_id,
        task_id=row.task_id,
        description=row.description,
        amount=row.amount,
        currency_code=row.currency_code,
        row_version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


__all__ = [
    "budget_from_orm",
    "budget_line_from_orm",
    "budget_line_to_orm",
    "budget_to_orm",
]
