from __future__ import annotations

from src.core.modules.project_management.domain.financials.configuration import (
    BillingMethod,
    BudgetControlMode,
    CostCodePolicy,
    FinancialProfileStatus,
    ProjectCostCode,
    ProjectCostCodeRestriction,
    ProjectFinancialProfile,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectCostCodeORM,
    ProjectCostCodeRestrictionORM,
    ProjectFinancialProfileORM,
)


def financial_profile_to_orm(profile: ProjectFinancialProfile) -> ProjectFinancialProfileORM:
    return ProjectFinancialProfileORM(
        id=profile.id,
        tenant_id=profile.tenant_id,
        organization_id=profile.organization_id,
        project_id=profile.project_id,
        currency_code=profile.currency_code,
        status=profile.status.value,
        billing_method=profile.billing_method.value,
        budget_control_mode=profile.budget_control_mode.value,
        cost_code_policy=profile.cost_code_policy.value,
        financial_start_date=profile.financial_start_date,
        financial_end_date=profile.financial_end_date,
        is_funded=profile.is_funded,
        is_billable=profile.is_billable,
        default_cost_code_id=profile.default_cost_code_id,
        version=profile.version,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def financial_profile_from_orm(row: ProjectFinancialProfileORM) -> ProjectFinancialProfile:
    return ProjectFinancialProfile(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        currency_code=row.currency_code,
        status=FinancialProfileStatus(row.status),
        billing_method=BillingMethod(row.billing_method),
        budget_control_mode=BudgetControlMode(row.budget_control_mode),
        cost_code_policy=CostCodePolicy(row.cost_code_policy),
        financial_start_date=row.financial_start_date,
        financial_end_date=row.financial_end_date,
        is_funded=row.is_funded,
        is_billable=row.is_billable,
        default_cost_code_id=row.default_cost_code_id,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def cost_code_to_orm(cost_code: ProjectCostCode) -> ProjectCostCodeORM:
    return ProjectCostCodeORM(
        id=cost_code.id,
        tenant_id=cost_code.tenant_id,
        organization_id=cost_code.organization_id,
        code=cost_code.code,
        name=cost_code.name,
        description=cost_code.description,
        parent_id=cost_code.parent_id,
        external_system=cost_code.external_system,
        external_reference=cost_code.external_reference,
        effective_from=cost_code.effective_from,
        effective_to=cost_code.effective_to,
        is_active=cost_code.is_active,
        version=cost_code.version,
        created_at=cost_code.created_at,
        updated_at=cost_code.updated_at,
    )


def cost_code_from_orm(row: ProjectCostCodeORM) -> ProjectCostCode:
    return ProjectCostCode(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        code=row.code,
        name=row.name,
        description=row.description,
        parent_id=row.parent_id,
        external_system=row.external_system,
        external_reference=row.external_reference,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        is_active=row.is_active,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def restriction_to_orm(
    restriction: ProjectCostCodeRestriction,
) -> ProjectCostCodeRestrictionORM:
    return ProjectCostCodeRestrictionORM(
        id=restriction.id,
        tenant_id=restriction.tenant_id,
        organization_id=restriction.organization_id,
        project_id=restriction.project_id,
        cost_code_id=restriction.cost_code_id,
        created_at=restriction.created_at,
    )


def restriction_from_orm(
    row: ProjectCostCodeRestrictionORM,
) -> ProjectCostCodeRestriction:
    return ProjectCostCodeRestriction(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        cost_code_id=row.cost_code_id,
        created_at=row.created_at,
    )


__all__ = [
    "cost_code_from_orm",
    "cost_code_to_orm",
    "financial_profile_from_orm",
    "financial_profile_to_orm",
    "restriction_from_orm",
    "restriction_to_orm",
]
