from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.cost_entry import (
    ProjectCostEntryRepository,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryStatus,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.cost_entry import (
    cost_entry_from_orm,
    cost_entry_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.cost_entry import (
    ProjectCostEntryORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.platform.application.tenant.tenancy.tenant_context import (
    ActiveScopeIds,
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.infra.persistence.db.optimistic import (
    delete_with_version_check,
    update_with_version_check,
)


class SqlAlchemyProjectCostEntryRepository(ProjectCostEntryRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def add(self, entry: ProjectCostEntry) -> None:
        context = self._context(operation_label="create project cost entry")
        self._require_entity_scope(entry, context)
        self._require_project(entry.project_id, context)
        self.session.add(cost_entry_to_orm(entry))

    def get(self, entry_id: str, *, for_update: bool = False) -> ProjectCostEntry | None:
        context = self._context(operation_label="access project cost entry")
        stmt = select(ProjectCostEntryORM).where(
            ProjectCostEntryORM.id == entry_id,
            ProjectCostEntryORM.tenant_id == context.tenant_id,
            ProjectCostEntryORM.organization_id == context.organization_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        row = self.session.execute(stmt).scalar_one_or_none()
        return cost_entry_from_orm(row) if row else None

    def get_by_idempotency_key(self, idempotency_key: str) -> ProjectCostEntry | None:
        context = self._context(operation_label="access project cost source")
        row = self.session.execute(
            select(ProjectCostEntryORM).where(
                ProjectCostEntryORM.tenant_id == context.tenant_id,
                ProjectCostEntryORM.organization_id == context.organization_id,
                ProjectCostEntryORM.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()
        return cost_entry_from_orm(row) if row else None

    def list_for_project(
        self,
        project_id: str,
        *,
        status: ProjectCostEntryStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProjectCostEntry], int]:
        context = self._context(operation_label="list project cost entries")
        filters = (
            ProjectCostEntryORM.tenant_id == context.tenant_id,
            ProjectCostEntryORM.organization_id == context.organization_id,
            ProjectCostEntryORM.project_id == project_id,
        )
        stmt = select(ProjectCostEntryORM).where(*filters)
        count_stmt = select(func.count(ProjectCostEntryORM.id)).where(*filters)
        if status is not None:
            stmt = stmt.where(ProjectCostEntryORM.status == status.value)
            count_stmt = count_stmt.where(ProjectCostEntryORM.status == status.value)
        total = int(self.session.execute(count_stmt).scalar_one())
        rows = self.session.execute(
            stmt.order_by(
                ProjectCostEntryORM.transaction_date.desc(),
                ProjectCostEntryORM.created_at.desc(),
                ProjectCostEntryORM.id.asc(),
            )
            .offset(max(0, int(offset)))
            .limit(min(500, max(1, int(limit))))
        ).scalars().all()
        return [cost_entry_from_orm(row) for row in rows], total

    def update(self, entry: ProjectCostEntry, *, expected_row_version: int) -> None:
        context = self._context(operation_label="update project cost entry")
        self._require_entity_scope(entry, context)
        entry.row_version = update_with_version_check(
            self.session,
            ProjectCostEntryORM,
            entry.id,
            expected_row_version,
            {
                "description": entry.description,
                "entry_kind": entry.entry_kind.value,
                "status": entry.status.value,
                "amount": entry.amount,
                "currency_code": entry.currency_code,
                "base_amount": entry.base_amount,
                "base_currency_code": entry.base_currency_code,
                "exchange_rate": entry.exchange_rate,
                "exchange_rate_date": entry.exchange_rate_date,
                "exchange_rate_source": entry.exchange_rate_source,
                "exchange_rate_captured_at": entry.exchange_rate_captured_at,
                "transaction_date": entry.transaction_date,
                "posting_date": entry.posting_date,
                "financial_period_id": entry.financial_period_id,
                "cost_code_id": entry.cost_code_id,
                "task_id": entry.task_id,
                "resource_id": entry.resource_id,
                "source_content_hash": entry.source_content_hash,
                "reversed_by_entry_id": entry.reversed_by_entry_id,
                "updated_by": entry.updated_by,
                "updated_at": entry.updated_at,
                "submitted_by": entry.submitted_by,
                "submitted_at": entry.submitted_at,
                "approved_by": entry.approved_by,
                "approved_at": entry.approved_at,
                "rejected_by": entry.rejected_by,
                "rejected_at": entry.rejected_at,
                "rejection_notes": entry.rejection_notes,
                "posted_by": entry.posted_by,
                "posted_at": entry.posted_at,
                "reversed_by": entry.reversed_by,
                "reversed_at": entry.reversed_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
                "project_id": entry.project_id,
            },
            not_found_message="Project cost entry not found.",
            stale_message="Project cost entry was updated by another user.",
        )

    def delete_draft(self, entry_id: str, *, expected_row_version: int) -> None:
        context = self._context(operation_label="delete draft project cost entry")
        delete_with_version_check(
            self.session,
            ProjectCostEntryORM,
            entry_id,
            expected_row_version,
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
                "status": ProjectCostEntryStatus.DRAFT.value,
            },
            not_found_message="Draft project cost entry not found.",
            stale_message="Project cost entry was updated by another user.",
        )

    def flush(self) -> None:
        self.session.flush()

    def _context(self, *, operation_label: str) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Project cost entry repository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    @staticmethod
    def _require_entity_scope(entry: ProjectCostEntry, context: ActiveScopeIds) -> None:
        if (
            entry.tenant_id != context.tenant_id
            or entry.organization_id != context.organization_id
        ):
            raise BusinessRuleError(
                "Project cost entry scope does not match the active organization.",
                code="PROJECT_COST_ENTRY_SCOPE_MISMATCH",
            )

    def _require_project(self, project_id: str, context: ActiveScopeIds) -> None:
        exists = self.session.execute(
            select(ProjectORM.id).where(
                ProjectORM.id == project_id,
                ProjectORM.tenant_id == context.tenant_id,
                ProjectORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if exists is None:
            raise NotFoundError("Project not found.")


__all__ = ["SqlAlchemyProjectCostEntryRepository"]
