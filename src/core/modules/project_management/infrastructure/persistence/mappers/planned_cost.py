from __future__ import annotations

from src.core.modules.project_management.domain.financials.planned_cost import (
    PlannedCostVersionStatus,
    ProjectPlannedCostLine,
    ProjectPlannedCostVersion,
)
from src.core.modules.project_management.infrastructure.persistence.orm.planned_cost import (
    ProjectPlannedCostLineORM,
    ProjectPlannedCostVersionORM,
)


def planned_cost_version_to_orm(
    version: ProjectPlannedCostVersion,
) -> ProjectPlannedCostVersionORM:
    return ProjectPlannedCostVersionORM(
        id=version.id,
        tenant_id=version.tenant_id,
        organization_id=version.organization_id,
        project_id=version.project_id,
        revision=version.revision,
        status=version.status.value,
        currency_code=version.currency_code,
        as_of=version.as_of,
        calculated_by=version.calculated_by,
        calculated_at=version.calculated_at,
        rates_complete=version.rates_complete,
        allocations_complete=version.allocations_complete,
        cost_codes_complete=version.cost_codes_complete,
        unresolved_rate_count=version.unresolved_rate_count,
        partially_allocated_resource_count=version.partially_allocated_resource_count,
        unclassified_line_count=version.unclassified_line_count,
        superseded_by=version.superseded_by,
        superseded_at=version.superseded_at,
        version=version.row_version,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


def planned_cost_version_from_orm(
    row: ProjectPlannedCostVersionORM,
) -> ProjectPlannedCostVersion:
    return ProjectPlannedCostVersion(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        revision=row.revision,
        status=PlannedCostVersionStatus(row.status),
        currency_code=row.currency_code,
        as_of=row.as_of,
        calculated_by=row.calculated_by,
        calculated_at=row.calculated_at,
        rates_complete=row.rates_complete,
        allocations_complete=row.allocations_complete,
        cost_codes_complete=row.cost_codes_complete,
        unresolved_rate_count=row.unresolved_rate_count,
        partially_allocated_resource_count=row.partially_allocated_resource_count,
        unclassified_line_count=row.unclassified_line_count,
        superseded_by=row.superseded_by,
        superseded_at=row.superseded_at,
        row_version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def planned_cost_line_to_orm(line: ProjectPlannedCostLine) -> ProjectPlannedCostLineORM:
    return ProjectPlannedCostLineORM(
        id=line.id,
        tenant_id=line.tenant_id,
        organization_id=line.organization_id,
        version_id=line.version_id,
        project_id=line.project_id,
        task_id=line.task_id,
        resource_id=line.resource_id,
        project_resource_id=line.project_resource_id,
        cost_code_id=line.cost_code_id,
        source_assignment_id=line.source_assignment_id,
        planned_hours=line.planned_hours,
        rate_amount=line.rate_amount,
        amount=line.amount,
        currency_code=line.currency_code,
        rate_card_id=line.rate_card_id,
        rate_line_id=line.rate_line_id,
        rate_card_version=line.rate_card_version,
        created_at=line.created_at,
    )


def planned_cost_line_from_orm(row: ProjectPlannedCostLineORM) -> ProjectPlannedCostLine:
    return ProjectPlannedCostLine(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        version_id=row.version_id,
        project_id=row.project_id,
        task_id=row.task_id,
        resource_id=row.resource_id,
        project_resource_id=row.project_resource_id,
        cost_code_id=row.cost_code_id,
        source_assignment_id=row.source_assignment_id,
        planned_hours=row.planned_hours,
        rate_amount=row.rate_amount,
        amount=row.amount,
        currency_code=row.currency_code,
        rate_card_id=row.rate_card_id,
        rate_line_id=row.rate_line_id,
        rate_card_version=row.rate_card_version,
        created_at=row.created_at,
    )


__all__ = [
    "planned_cost_line_from_orm",
    "planned_cost_line_to_orm",
    "planned_cost_version_from_orm",
    "planned_cost_version_to_orm",
]
