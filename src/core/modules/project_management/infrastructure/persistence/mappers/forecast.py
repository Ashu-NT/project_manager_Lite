from __future__ import annotations

from src.core.modules.project_management.domain.financials.forecast import (
    ForecastDecisionAction,
    ForecastDecisionReason,
    ForecastGenerationMode,
    ForecastLine,
    ForecastLineSourceKind,
    ForecastLineSourceType,
    ForecastStatus,
    ForecastSourceDecision,
    ProjectForecast,
)
from src.core.modules.project_management.infrastructure.persistence.orm.forecast import (
    ForecastLineORM,
    ForecastSourceDecisionORM,
    ProjectForecastORM,
)


def forecast_to_orm(value: ProjectForecast) -> ProjectForecastORM:
    return ProjectForecastORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        name=value.name,
        currency_code=value.currency_code,
        as_of_date=value.as_of_date,
        generation_mode=value.generation_mode.value,
        created_by=value.created_by,
        status=value.status.value,
        revision=value.revision,
        version=value.row_version,
        submitted_by=value.submitted_by,
        submitted_at=value.submitted_at,
        approved_by=value.approved_by,
        approved_at=value.approved_at,
        rejected_by=value.rejected_by,
        rejected_at=value.rejected_at,
        superseded_by=value.superseded_by,
        superseded_at=value.superseded_at,
        notes=value.notes,
        submission_notes=value.submission_notes,
        approval_notes=value.approval_notes,
        rejection_notes=value.rejection_notes,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def forecast_from_orm(value: ProjectForecastORM) -> ProjectForecast:
    return ProjectForecast(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        name=value.name,
        currency_code=value.currency_code,
        as_of_date=value.as_of_date,
        generation_mode=ForecastGenerationMode(value.generation_mode),
        created_by=value.created_by,
        status=ForecastStatus(value.status),
        revision=value.revision,
        row_version=value.version,
        submitted_by=value.submitted_by,
        submitted_at=value.submitted_at,
        approved_by=value.approved_by,
        approved_at=value.approved_at,
        rejected_by=value.rejected_by,
        rejected_at=value.rejected_at,
        superseded_by=value.superseded_by,
        superseded_at=value.superseded_at,
        notes=value.notes,
        submission_notes=value.submission_notes,
        approval_notes=value.approval_notes,
        rejection_notes=value.rejection_notes,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def forecast_line_to_orm(value: ForecastLine) -> ForecastLineORM:
    return ForecastLineORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        forecast_id=value.forecast_id,
        project_id=value.project_id,
        cost_code_id=value.cost_code_id,
        task_id=value.task_id,
        description=value.description,
        amount=value.amount,
        currency_code=value.currency_code,
        source_kind=value.source_kind.value,
        source_type=value.source_type.value,
        source_reference_type=value.source_reference_type,
        source_reference_id=value.source_reference_id,
        source_snapshot_at=value.source_snapshot_at,
        period_start=value.period_start,
        period_end=value.period_end,
        created_by=value.created_by,
        version=value.row_version,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def forecast_line_from_orm(value: ForecastLineORM) -> ForecastLine:
    return ForecastLine(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        forecast_id=value.forecast_id,
        project_id=value.project_id,
        cost_code_id=value.cost_code_id,
        task_id=value.task_id,
        description=value.description,
        amount=value.amount,
        currency_code=value.currency_code,
        source_kind=ForecastLineSourceKind(value.source_kind),
        source_type=ForecastLineSourceType(value.source_type),
        source_reference_type=value.source_reference_type,
        source_reference_id=value.source_reference_id,
        source_snapshot_at=value.source_snapshot_at,
        period_start=value.period_start,
        period_end=value.period_end,
        created_by=value.created_by,
        row_version=value.version,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def forecast_decision_to_orm(value: ForecastSourceDecision) -> ForecastSourceDecisionORM:
    return ForecastSourceDecisionORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        forecast_id=value.forecast_id,
        project_id=value.project_id,
        cost_code_id=value.cost_code_id,
        task_id=value.task_id,
        source_type=value.source_type.value,
        source_reference_type=value.source_reference_type,
        source_reference_id=value.source_reference_id,
        action=value.action.value,
        reason=value.reason.value,
        source_amount=value.source_amount,
        included_amount=value.included_amount,
        excluded_amount=value.excluded_amount,
        currency_code=value.currency_code,
        source_snapshot_at=value.source_snapshot_at,
        created_at=value.created_at,
    )


def forecast_decision_from_orm(value: ForecastSourceDecisionORM) -> ForecastSourceDecision:
    return ForecastSourceDecision(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        forecast_id=value.forecast_id,
        project_id=value.project_id,
        cost_code_id=value.cost_code_id,
        task_id=value.task_id,
        source_type=ForecastLineSourceType(value.source_type),
        source_reference_type=value.source_reference_type,
        source_reference_id=value.source_reference_id,
        action=ForecastDecisionAction(value.action),
        reason=ForecastDecisionReason(value.reason),
        source_amount=value.source_amount,
        included_amount=value.included_amount,
        excluded_amount=value.excluded_amount,
        currency_code=value.currency_code,
        source_snapshot_at=value.source_snapshot_at,
        created_at=value.created_at,
    )


__all__ = [
    "forecast_from_orm",
    "forecast_decision_from_orm",
    "forecast_decision_to_orm",
    "forecast_line_from_orm",
    "forecast_line_to_orm",
    "forecast_to_orm",
]
