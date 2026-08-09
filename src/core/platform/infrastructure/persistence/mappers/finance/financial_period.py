from __future__ import annotations

from src.core.platform.finance.periods import FinancialPeriod, FinancialPeriodStatus
from src.core.platform.infrastructure.persistence.orm.finance.financial_period import (
    FinancialPeriodORM,
)


def financial_period_to_orm(period: FinancialPeriod) -> FinancialPeriodORM:
    return FinancialPeriodORM(
        id=period.id,
        tenant_id=period.tenant_id,
        organization_id=period.organization_id,
        code=period.code,
        name=period.name,
        fiscal_year=period.fiscal_year,
        period_number=period.period_number,
        start_date=period.start_date,
        end_date=period.end_date,
        status=period.status.value,
        closed_by=period.closed_by,
        closed_at=period.closed_at,
        locked_by=period.locked_by,
        locked_at=period.locked_at,
        version=period.version,
        created_by=period.created_by,
        created_at=period.created_at,
        updated_by=period.updated_by,
        updated_at=period.updated_at,
    )


def financial_period_from_orm(row: FinancialPeriodORM) -> FinancialPeriod:
    return FinancialPeriod(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        code=row.code,
        name=row.name,
        fiscal_year=row.fiscal_year,
        period_number=row.period_number,
        start_date=row.start_date,
        end_date=row.end_date,
        status=FinancialPeriodStatus(row.status),
        closed_by=row.closed_by,
        closed_at=row.closed_at,
        locked_by=row.locked_by,
        locked_at=row.locked_at,
        version=row.version,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_by=row.updated_by,
        updated_at=row.updated_at,
    )


__all__ = ["financial_period_from_orm", "financial_period_to_orm"]
