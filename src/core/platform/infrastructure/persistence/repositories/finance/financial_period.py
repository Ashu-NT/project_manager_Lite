from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.contract.finance import FinancialPeriodRepository
from src.core.platform.finance.periods import FinancialPeriod, FinancialPeriodStatus
from src.core.platform.infrastructure.persistence.mappers.finance import (
    financial_period_from_orm,
    financial_period_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.finance import FinancialPeriodORM
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyFinancialPeriodRepository(
    TenantScopedRepositorySupport,
    FinancialPeriodRepository,
):
    _repository_label = "FinancialPeriodRepository"

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def lock_catalog(self) -> None:
        context = self._context(operation_label="change financial period catalog")
        organization_id = self.session.execute(
            select(OrganizationORM.id)
            .where(
                OrganizationORM.id == context.organization_id,
                OrganizationORM.tenant_id == context.tenant_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if organization_id is None:
            raise NotFoundError(
                "Active organization not found.",
                code="ORGANIZATION_NOT_FOUND",
            )

    def add(self, period: FinancialPeriod) -> None:
        context = self._context(operation_label="create financial period")
        self._require_entity_scope(period, context)
        self.session.add(financial_period_to_orm(period))

    def get(self, period_id: str) -> FinancialPeriod | None:
        context = self._context(operation_label="access financial period")
        row = self.session.execute(
            select(FinancialPeriodORM).where(
                FinancialPeriodORM.id == period_id,
                FinancialPeriodORM.tenant_id == context.tenant_id,
                FinancialPeriodORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return financial_period_from_orm(row) if row else None

    def get_by_code(self, code: str) -> FinancialPeriod | None:
        context = self._context(operation_label="access financial period")
        row = self.session.execute(
            select(FinancialPeriodORM).where(
                FinancialPeriodORM.code == str(code or "").strip().upper(),
                FinancialPeriodORM.tenant_id == context.tenant_id,
                FinancialPeriodORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return financial_period_from_orm(row) if row else None

    def find_for_date(self, posting_date: date) -> FinancialPeriod | None:
        context = self._context(operation_label="resolve financial period")
        row = self.session.execute(
            select(FinancialPeriodORM).where(
                FinancialPeriodORM.tenant_id == context.tenant_id,
                FinancialPeriodORM.organization_id == context.organization_id,
                FinancialPeriodORM.start_date <= posting_date,
                FinancialPeriodORM.end_date >= posting_date,
            )
        ).scalar_one_or_none()
        return financial_period_from_orm(row) if row else None

    def list(
        self,
        *,
        fiscal_year: int | None = None,
        status: FinancialPeriodStatus | None = None,
    ) -> list[FinancialPeriod]:
        context = self._context(operation_label="list financial periods")
        stmt = select(FinancialPeriodORM).where(
            FinancialPeriodORM.tenant_id == context.tenant_id,
            FinancialPeriodORM.organization_id == context.organization_id,
        )
        if fiscal_year is not None:
            stmt = stmt.where(FinancialPeriodORM.fiscal_year == fiscal_year)
        if status is not None:
            stmt = stmt.where(FinancialPeriodORM.status == status.value)
        rows = self.session.execute(
            stmt.order_by(
                FinancialPeriodORM.start_date,
                FinancialPeriodORM.period_number,
            )
        ).scalars().all()
        return [financial_period_from_orm(row) for row in rows]

    def overlaps(
        self,
        *,
        start_date: date,
        end_date: date,
        exclude_period_id: str | None = None,
    ) -> bool:
        context = self._context(operation_label="validate financial period range")
        stmt = select(FinancialPeriodORM.id).where(
            FinancialPeriodORM.tenant_id == context.tenant_id,
            FinancialPeriodORM.organization_id == context.organization_id,
            FinancialPeriodORM.start_date <= end_date,
            FinancialPeriodORM.end_date >= start_date,
        )
        if exclude_period_id:
            stmt = stmt.where(FinancialPeriodORM.id != exclude_period_id)
        return self.session.execute(stmt.limit(1)).scalar_one_or_none() is not None

    def update(self, period: FinancialPeriod, *, expected_version: int) -> None:
        context = self._context(operation_label="update financial period")
        self._require_entity_scope(period, context)
        period.version = update_with_version_check(
            self.session,
            FinancialPeriodORM,
            period.id,
            expected_version,
            {
                "code": period.code,
                "name": period.name,
                "fiscal_year": period.fiscal_year,
                "period_number": period.period_number,
                "start_date": period.start_date,
                "end_date": period.end_date,
                "status": period.status.value,
                "closed_by": period.closed_by,
                "closed_at": period.closed_at,
                "locked_by": period.locked_by,
                "locked_at": period.locked_at,
                "updated_by": period.updated_by,
                "updated_at": period.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
            },
            not_found_message="Financial period not found.",
            stale_message="Financial period was updated by another user.",
        )

    @staticmethod
    def _require_entity_scope(period: FinancialPeriod, context) -> None:
        if (
            period.tenant_id != context.tenant_id
            or period.organization_id != context.organization_id
        ):
            raise BusinessRuleError(
                "Financial period scope does not match the active organization.",
                code="FINANCIAL_PERIOD_SCOPE_MISMATCH",
            )


__all__ = ["SqlAlchemyFinancialPeriodRepository"]
