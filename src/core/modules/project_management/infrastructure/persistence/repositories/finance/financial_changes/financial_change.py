from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.finance.financial_changes.financial_change import (
    FinancialChangeRepository,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeRequest,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.financial_change import (
    financial_change_from_orm,
    financial_change_impact_from_orm,
    financial_change_impact_to_orm,
    financial_change_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_change import (
    FinancialChangeImpactORM,
    FinancialChangeRequestORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.platform.application.tenant.tenancy.tenant_context import (
    ActiveScopeIds,
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyFinancialChangeRepository(FinancialChangeRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self, *, operation_label: str) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Financial change repository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    @staticmethod
    def _require_scope(value, context: ActiveScopeIds) -> None:
        if (
            value.tenant_id != context.tenant_id
            or value.organization_id != context.organization_id
        ):
            raise BusinessRuleError(
                "Financial change scope does not match the active organization.",
                code="FINANCIAL_CHANGE_SCOPE_MISMATCH",
            )

    def add(self, change: FinancialChangeRequest) -> None:
        context = self._context(operation_label="create financial change")
        self._require_scope(change, context)
        project = self.session.execute(
            select(ProjectORM.id).where(
                ProjectORM.id == change.project_id,
                ProjectORM.tenant_id == context.tenant_id,
                ProjectORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        self.session.add(financial_change_to_orm(change))

    def get(self, change_id: str) -> FinancialChangeRequest | None:
        context = self._context(operation_label="access financial change")
        row = self.session.execute(
            select(FinancialChangeRequestORM).where(
                FinancialChangeRequestORM.id == change_id,
                FinancialChangeRequestORM.tenant_id == context.tenant_id,
                FinancialChangeRequestORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return financial_change_from_orm(row) if row else None

    def get_latest_for_project(self, project_id: str) -> FinancialChangeRequest | None:
        context = self._context(operation_label="access latest financial change")
        row = self.session.execute(
            select(FinancialChangeRequestORM)
            .where(
                FinancialChangeRequestORM.project_id == project_id,
                FinancialChangeRequestORM.tenant_id == context.tenant_id,
                FinancialChangeRequestORM.organization_id == context.organization_id,
            )
            .order_by(FinancialChangeRequestORM.revision.desc())
            .limit(1)
        ).scalar_one_or_none()
        return financial_change_from_orm(row) if row else None

    def list_for_project(self, project_id: str) -> list[FinancialChangeRequest]:
        context = self._context(operation_label="list financial changes")
        rows = self.session.execute(
            select(FinancialChangeRequestORM)
            .where(
                FinancialChangeRequestORM.project_id == project_id,
                FinancialChangeRequestORM.tenant_id == context.tenant_id,
                FinancialChangeRequestORM.organization_id == context.organization_id,
            )
            .order_by(FinancialChangeRequestORM.revision.desc())
        ).scalars().all()
        return [financial_change_from_orm(row) for row in rows]

    def update(
        self, change: FinancialChangeRequest, *, expected_row_version: int
    ) -> None:
        context = self._context(operation_label="update financial change")
        self._require_scope(change, context)
        change.row_version = update_with_version_check(
            self.session,
            FinancialChangeRequestORM,
            change.id,
            expected_row_version,
            {
                "status": change.status.value,
                "approval_request_id": change.approval_request_id,
                "applied_budget_id": change.applied_budget_id,
                "applied_forecast_id": change.applied_forecast_id,
                "applied_schedule_count": change.applied_schedule_count,
                "submitted_by": change.submitted_by,
                "submitted_at": change.submitted_at,
                "applied_by": change.applied_by,
                "applied_at": change.applied_at,
                "rejected_by": change.rejected_by,
                "rejected_at": change.rejected_at,
                "rejection_notes": change.rejection_notes,
                "updated_at": change.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
                "project_id": change.project_id,
            },
            not_found_message="Financial change not found.",
            stale_message="Financial change was updated by another user.",
        )

    def add_impact(self, impact: FinancialChangeImpact) -> None:
        context = self._context(operation_label="create financial change impact")
        self._require_scope(impact, context)
        parent = self._require_change(impact.change_request_id, context)
        if parent.project_id != impact.project_id:
            raise BusinessRuleError(
                "Financial change impact project does not match its request.",
                code="FINANCIAL_CHANGE_IMPACT_PROJECT_MISMATCH",
            )
        self.session.add(financial_change_impact_to_orm(impact))

    def list_impacts(self, change_id: str) -> list[FinancialChangeImpact]:
        context = self._context(operation_label="list financial change impacts")
        self._require_change(change_id, context)
        rows = self.session.execute(
            select(FinancialChangeImpactORM)
            .where(
                FinancialChangeImpactORM.change_request_id == change_id,
                FinancialChangeImpactORM.tenant_id == context.tenant_id,
                FinancialChangeImpactORM.organization_id == context.organization_id,
            )
            .order_by(
                FinancialChangeImpactORM.impact_type.asc(),
                FinancialChangeImpactORM.created_at.asc(),
                FinancialChangeImpactORM.id.asc(),
            )
        ).scalars().all()
        return [financial_change_impact_from_orm(row) for row in rows]

    def update_impact_application(
        self,
        impact_id: str,
        *,
        applied_reference_type: str,
        applied_reference_id: str,
    ) -> None:
        context = self._context(operation_label="apply financial change impact")
        result = self.session.execute(
            update(FinancialChangeImpactORM)
            .where(
                FinancialChangeImpactORM.id == impact_id,
                FinancialChangeImpactORM.tenant_id == context.tenant_id,
                FinancialChangeImpactORM.organization_id == context.organization_id,
                FinancialChangeImpactORM.applied_reference_id.is_(None),
            )
            .values(
                applied_reference_type=applied_reference_type,
                applied_reference_id=applied_reference_id,
            )
        )
        if result.rowcount != 1:
            raise BusinessRuleError(
                "Financial change impact was already applied or is unavailable.",
                code="FINANCIAL_CHANGE_IMPACT_APPLICATION_CONFLICT",
            )

    def flush(self) -> None:
        self.session.flush()

    def _require_change(
        self, change_id: str, context: ActiveScopeIds
    ) -> FinancialChangeRequestORM:
        row = self.session.execute(
            select(FinancialChangeRequestORM).where(
                FinancialChangeRequestORM.id == change_id,
                FinancialChangeRequestORM.tenant_id == context.tenant_id,
                FinancialChangeRequestORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError(
                "Financial change not found.", code="FINANCIAL_CHANGE_NOT_FOUND"
            )
        return row


__all__ = ["SqlAlchemyFinancialChangeRepository"]
