from __future__ import annotations

from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeImpactType,
    FinancialChangeRequest,
    FinancialChangeStatus,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_change import (
    FinancialChangeImpactORM,
    FinancialChangeRequestORM,
)


def financial_change_to_orm(value: FinancialChangeRequest) -> FinancialChangeRequestORM:
    return FinancialChangeRequestORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        title=value.title,
        reason=value.reason,
        description=value.description,
        effective_date=value.effective_date,
        currency_code=value.currency_code,
        created_by=value.created_by,
        revision=value.revision,
        status=value.status.value,
        base_budget_id=value.base_budget_id,
        base_budget_revision=value.base_budget_revision,
        base_forecast_id=value.base_forecast_id,
        base_forecast_revision=value.base_forecast_revision,
        approval_request_id=value.approval_request_id,
        applied_budget_id=value.applied_budget_id,
        applied_forecast_id=value.applied_forecast_id,
        submitted_by=value.submitted_by,
        submitted_at=value.submitted_at,
        applied_by=value.applied_by,
        applied_at=value.applied_at,
        rejected_by=value.rejected_by,
        rejected_at=value.rejected_at,
        rejection_notes=value.rejection_notes,
        version=value.row_version,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def financial_change_from_orm(value: FinancialChangeRequestORM) -> FinancialChangeRequest:
    return FinancialChangeRequest(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        title=value.title,
        reason=value.reason,
        description=value.description,
        effective_date=value.effective_date,
        currency_code=value.currency_code,
        created_by=value.created_by,
        revision=value.revision,
        status=FinancialChangeStatus(value.status),
        base_budget_id=value.base_budget_id,
        base_budget_revision=value.base_budget_revision,
        base_forecast_id=value.base_forecast_id,
        base_forecast_revision=value.base_forecast_revision,
        approval_request_id=value.approval_request_id,
        applied_budget_id=value.applied_budget_id,
        applied_forecast_id=value.applied_forecast_id,
        submitted_by=value.submitted_by,
        submitted_at=value.submitted_at,
        applied_by=value.applied_by,
        applied_at=value.applied_at,
        rejected_by=value.rejected_by,
        rejected_at=value.rejected_at,
        rejection_notes=value.rejection_notes,
        row_version=value.version,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def financial_change_impact_to_orm(value: FinancialChangeImpact) -> FinancialChangeImpactORM:
    return FinancialChangeImpactORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        change_request_id=value.change_request_id,
        project_id=value.project_id,
        impact_type=value.impact_type.value,
        description=value.description,
        amount=value.amount,
        currency_code=value.currency_code,
        cost_code_id=value.cost_code_id,
        task_id=value.task_id,
        target_line_id=value.target_line_id,
        source_reference_type=value.source_reference_type,
        source_reference_id=value.source_reference_id,
        schedule_start=value.schedule_start,
        schedule_finish=value.schedule_finish,
        planned_hours_delta=value.planned_hours_delta,
        applied_line_id=value.applied_line_id,
        created_at=value.created_at,
    )


def financial_change_impact_from_orm(value: FinancialChangeImpactORM) -> FinancialChangeImpact:
    return FinancialChangeImpact(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        change_request_id=value.change_request_id,
        project_id=value.project_id,
        impact_type=FinancialChangeImpactType(value.impact_type),
        description=value.description,
        amount=value.amount,
        currency_code=value.currency_code,
        cost_code_id=value.cost_code_id,
        task_id=value.task_id,
        target_line_id=value.target_line_id,
        source_reference_type=value.source_reference_type,
        source_reference_id=value.source_reference_id,
        schedule_start=value.schedule_start,
        schedule_finish=value.schedule_finish,
        planned_hours_delta=value.planned_hours_delta,
        applied_line_id=value.applied_line_id,
        created_at=value.created_at,
    )


__all__ = [
    "financial_change_from_orm",
    "financial_change_impact_from_orm",
    "financial_change_impact_to_orm",
    "financial_change_to_orm",
]
