from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.legacy_cost_migration import LegacyCostMigrationRepository
from src.core.modules.project_management.domain.financials.legacy_migration import (
    LegacyCostMigrationItem,
    LegacyCostMigrationItemStatus,
    LegacyCostMigrationMode,
    LegacyCostMigrationPurpose,
    LegacyCostMigrationRun,
    LegacyCostMigrationRunStatus,
)
from src.core.modules.project_management.infrastructure.persistence.orm.legacy_cost_migration import (
    LegacyCostMigrationItemORM,
    LegacyCostMigrationRunORM,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError


def _run_to_orm(value: LegacyCostMigrationRun) -> LegacyCostMigrationRunORM:
    return LegacyCostMigrationRunORM(
        id=value.id,
        tenant_id=value.tenant_id,
        organization_id=value.organization_id,
        project_id=value.project_id,
        mode=value.mode.value,
        status=value.status.value,
        fallback_transaction_date=value.fallback_transaction_date,
        started_by=value.started_by,
        started_at=value.started_at,
        completed_at=value.completed_at,
        summary_json=value.summary_json,
    )


def _item_from_orm(row: LegacyCostMigrationItemORM) -> LegacyCostMigrationItem:
    return LegacyCostMigrationItem(
        id=row.id,
        tenant_id=row.tenant_id,
        organization_id=row.organization_id,
        project_id=row.project_id,
        legacy_cost_item_id=row.legacy_cost_item_id,
        purpose=LegacyCostMigrationPurpose(row.purpose),
        status=LegacyCostMigrationItemStatus(row.status),
        last_run_id=row.last_run_id,
        source_amount=row.source_amount,
        target_amount=row.target_amount,
        rounding_delta=row.rounding_delta,
        currency_code=row.currency_code,
        target_type=row.target_type,
        target_id=row.target_id,
        reason_code=row.reason_code,
        decision_json=row.decision_json,
        updated_at=row.updated_at,
    )


class SqlAlchemyLegacyCostMigrationRepository(LegacyCostMigrationRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self, operation_label: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Legacy cost migration repository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(operation_label=operation_label)

    def add_run(self, run: LegacyCostMigrationRun) -> None:
        context = self._context("create legacy cost migration run")
        self._require_scope(run, context)
        self.session.add(_run_to_orm(run))

    def update_run(self, run: LegacyCostMigrationRun) -> None:
        context = self._context("update legacy cost migration run")
        self._require_scope(run, context)
        row = self.session.execute(
            select(LegacyCostMigrationRunORM).where(
                LegacyCostMigrationRunORM.id == run.id,
                LegacyCostMigrationRunORM.tenant_id == context.tenant_id,
                LegacyCostMigrationRunORM.organization_id == context.organization_id,
            )
        ).scalar_one()
        row.status = run.status.value
        row.completed_at = run.completed_at
        row.summary_json = run.summary_json

    def get_item(self, legacy_cost_item_id: str, purpose: LegacyCostMigrationPurpose) -> LegacyCostMigrationItem | None:
        context = self._context("access legacy cost migration checkpoint")
        row = self.session.execute(
            select(LegacyCostMigrationItemORM).where(
                LegacyCostMigrationItemORM.tenant_id == context.tenant_id,
                LegacyCostMigrationItemORM.organization_id == context.organization_id,
                LegacyCostMigrationItemORM.legacy_cost_item_id == legacy_cost_item_id,
                LegacyCostMigrationItemORM.purpose == purpose.value,
            )
        ).scalar_one_or_none()
        return _item_from_orm(row) if row else None

    def save_item(self, item: LegacyCostMigrationItem) -> None:
        context = self._context("save legacy cost migration checkpoint")
        self._require_scope(item, context)
        row = self.session.execute(
            select(LegacyCostMigrationItemORM).where(
                LegacyCostMigrationItemORM.id == item.id,
                LegacyCostMigrationItemORM.tenant_id == context.tenant_id,
                LegacyCostMigrationItemORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if row is None:
            self.session.add(LegacyCostMigrationItemORM(
                id=item.id,
                tenant_id=item.tenant_id,
                organization_id=item.organization_id,
                project_id=item.project_id,
                legacy_cost_item_id=item.legacy_cost_item_id,
                purpose=item.purpose.value,
                status=item.status.value,
                last_run_id=item.last_run_id,
                source_amount=item.source_amount,
                target_amount=item.target_amount,
                rounding_delta=item.rounding_delta,
                currency_code=item.currency_code,
                target_type=item.target_type,
                target_id=item.target_id,
                reason_code=item.reason_code,
                decision_json=item.decision_json,
                updated_at=item.updated_at,
            ))
            return
        row.status = item.status.value
        row.last_run_id = item.last_run_id
        row.source_amount = item.source_amount
        row.target_amount = item.target_amount
        row.rounding_delta = item.rounding_delta
        row.currency_code = item.currency_code
        row.target_type = item.target_type
        row.target_id = item.target_id
        row.reason_code = item.reason_code
        row.decision_json = item.decision_json
        row.updated_at = item.updated_at

    def list_items_for_project(self, project_id: str) -> list[LegacyCostMigrationItem]:
        context = self._context("list legacy cost migration checkpoints")
        rows = self.session.execute(
            select(LegacyCostMigrationItemORM).where(
                LegacyCostMigrationItemORM.tenant_id == context.tenant_id,
                LegacyCostMigrationItemORM.organization_id == context.organization_id,
                LegacyCostMigrationItemORM.project_id == project_id,
            ).order_by(LegacyCostMigrationItemORM.legacy_cost_item_id, LegacyCostMigrationItemORM.purpose)
        ).scalars().all()
        return [_item_from_orm(row) for row in rows]

    @staticmethod
    def _require_scope(value, context) -> None:
        if value.tenant_id != context.tenant_id or value.organization_id != context.organization_id:
            raise BusinessRuleError(
                "Legacy cost migration scope does not match the active organization.",
                code="LEGACY_COST_MIGRATION_SCOPE_MISMATCH",
            )


__all__ = ["SqlAlchemyLegacyCostMigrationRepository"]
