from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, aliased

from src.core.modules.project_management.contracts.reads.financials.models.finance_setup_facts import (
    FinanceSetupFacts,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectCostCodeORM,
    ProjectFinancialProfileORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
)


class SqlAlchemyFinanceSetupReader:
    """Immutable project Finance configuration projection."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def get_setup(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
    ) -> FinanceSetupFacts | None:
        default_code = aliased(ProjectCostCodeORM)
        row = self._session.execute(
            select(
                ProjectFinancialProfileORM.project_id,
                ProjectFinancialProfileORM.currency_code,
                ProjectFinancialProfileORM.status,
                ProjectFinancialProfileORM.billing_method,
                ProjectFinancialProfileORM.budget_control_mode,
                ProjectFinancialProfileORM.cost_code_policy,
                ProjectFinancialProfileORM.financial_start_date,
                ProjectFinancialProfileORM.financial_end_date,
                ProjectFinancialProfileORM.is_funded,
                ProjectFinancialProfileORM.is_billable,
                ProjectFinancialProfileORM.version,
                default_code.code.label("default_cost_code_value"),
                default_code.name.label("default_cost_code_name"),
            )
            .join(
                ProjectORM,
                and_(
                    ProjectORM.id == ProjectFinancialProfileORM.project_id,
                    ProjectORM.tenant_id == ProjectFinancialProfileORM.tenant_id,
                    ProjectORM.organization_id
                    == ProjectFinancialProfileORM.organization_id,
                ),
            )
            .outerjoin(
                default_code,
                and_(
                    default_code.id
                    == ProjectFinancialProfileORM.default_cost_code_id,
                    default_code.tenant_id == ProjectFinancialProfileORM.tenant_id,
                    default_code.organization_id
                    == ProjectFinancialProfileORM.organization_id,
                ),
            )
            .where(
                ProjectFinancialProfileORM.tenant_id == tenant_id,
                ProjectFinancialProfileORM.organization_id == organization_id,
                ProjectFinancialProfileORM.project_id == project_id,
                ProjectORM.tenant_id == tenant_id,
                ProjectORM.organization_id == organization_id,
                ProjectORM.id == project_id,
            )
        ).one_or_none()
        if row is None:
            return None
        default_cost_code = ""
        if row.default_cost_code_value:
            default_cost_code = (
                f"{row.default_cost_code_value} - {row.default_cost_code_name}"
            )
        return FinanceSetupFacts(
            project_id=str(row.project_id),
            currency_code=str(row.currency_code),
            status=str(row.status),
            billing_method=str(row.billing_method),
            budget_control_mode=str(row.budget_control_mode),
            cost_code_policy=str(row.cost_code_policy),
            financial_start_date=row.financial_start_date,
            financial_end_date=row.financial_end_date,
            is_funded=bool(row.is_funded),
            is_billable=bool(row.is_billable),
            default_cost_code=default_cost_code,
            version=int(row.version),
        )


__all__ = ["SqlAlchemyFinanceSetupReader"]
