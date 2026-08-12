from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.finance.commitments.commitment import (
    ProjectCommitmentRepository,
)
from src.core.modules.project_management.domain.financials.commitment import (
    ProjectCommitment,
    ProjectCommitmentLine,
    ProjectCommitmentMatch,
    ProjectCommitmentMatchKind,
    ProjectCommitmentSourceRevision,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.commitment import (
    commitment_from_orm,
    commitment_line_from_orm,
    commitment_line_to_orm,
    commitment_match_from_orm,
    commitment_match_to_orm,
    commitment_revision_from_orm,
    commitment_revision_to_orm,
    commitment_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.commitment import (
    ProjectCommitmentLineORM,
    ProjectCommitmentMatchORM,
    ProjectCommitmentORM,
    ProjectCommitmentSourceRevisionORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.platform.application.tenant.tenancy.tenant_context import (
    ActiveScopeIds,
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyProjectCommitmentRepository(ProjectCommitmentRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def add(self, commitment: ProjectCommitment) -> None:
        context = self._context(operation_label="create project commitment")
        self._require_scope(commitment, context)
        self._require_project(commitment.project_id, context)
        self.session.add(commitment_to_orm(commitment))

    def get(self, commitment_id: str) -> ProjectCommitment | None:
        context = self._context(operation_label="access project commitment")
        row = self.session.execute(
            select(ProjectCommitmentORM).where(
                ProjectCommitmentORM.id == commitment_id,
                ProjectCommitmentORM.tenant_id == context.tenant_id,
                ProjectCommitmentORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return commitment_from_orm(row) if row else None

    def get_by_purchase_order(self, purchase_order_id: str) -> ProjectCommitment | None:
        context = self._context(operation_label="access purchase-order commitment")
        row = self.session.execute(
            select(ProjectCommitmentORM).where(
                ProjectCommitmentORM.tenant_id == context.tenant_id,
                ProjectCommitmentORM.organization_id == context.organization_id,
                ProjectCommitmentORM.purchase_order_id == purchase_order_id,
            )
        ).scalar_one_or_none()
        return commitment_from_orm(row) if row else None

    def add_line(self, line: ProjectCommitmentLine) -> None:
        context = self._context(operation_label="create project commitment line")
        self._require_scope(line, context)
        self._require_commitment(line.commitment_id, line.project_id, context)
        self.session.add(commitment_line_to_orm(line))

    def get_line(
        self, line_id: str, *, for_update: bool = False
    ) -> ProjectCommitmentLine | None:
        context = self._context(operation_label="access project commitment line")
        stmt = select(ProjectCommitmentLineORM).where(
            ProjectCommitmentLineORM.id == line_id,
            ProjectCommitmentLineORM.tenant_id == context.tenant_id,
            ProjectCommitmentLineORM.organization_id == context.organization_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        row = self.session.execute(stmt).scalar_one_or_none()
        return commitment_line_from_orm(row) if row else None

    def get_line_by_source(
        self,
        purchase_order_id: str,
        purchase_order_line_id: str,
        *,
        for_update: bool = False,
    ) -> ProjectCommitmentLine | None:
        context = self._context(operation_label="access purchase-order commitment line")
        stmt = (
            select(ProjectCommitmentLineORM)
            .join(
                ProjectCommitmentORM,
                ProjectCommitmentORM.id == ProjectCommitmentLineORM.commitment_id,
            )
            .where(
                ProjectCommitmentLineORM.tenant_id == context.tenant_id,
                ProjectCommitmentLineORM.organization_id == context.organization_id,
                ProjectCommitmentORM.purchase_order_id == purchase_order_id,
                ProjectCommitmentLineORM.purchase_order_line_id == purchase_order_line_id,
            )
        )
        if for_update:
            stmt = stmt.with_for_update()
        row = self.session.execute(stmt).scalar_one_or_none()
        return commitment_line_from_orm(row) if row else None

    def list_lines_for_project(
        self, project_id: str, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[ProjectCommitmentLine], int]:
        context = self._context(operation_label="list project commitment lines")
        filters = (
            ProjectCommitmentLineORM.tenant_id == context.tenant_id,
            ProjectCommitmentLineORM.organization_id == context.organization_id,
            ProjectCommitmentLineORM.project_id == project_id,
        )
        total = self.session.execute(
            select(func.count(ProjectCommitmentLineORM.id)).where(*filters)
        ).scalar_one()
        rows = self.session.execute(
            select(ProjectCommitmentLineORM)
            .where(*filters)
            .order_by(
                ProjectCommitmentLineORM.order_date.desc(),
                ProjectCommitmentLineORM.id.asc(),
            )
            .offset(max(0, offset))
            .limit(max(1, min(limit, 200)))
        ).scalars().all()
        return [commitment_line_from_orm(row) for row in rows], int(total)

    def update_line(self, line: ProjectCommitmentLine, *, expected_row_version: int) -> None:
        context = self._context(operation_label="update project commitment line")
        self._require_scope(line, context)
        line.row_version = update_with_version_check(
            self.session,
            ProjectCommitmentLineORM,
            line.id,
            expected_row_version,
            {
                "state": line.state.value,
                "ordered_quantity": line.ordered_quantity,
                "unit_price": line.unit_price,
                "amount": line.amount,
                "base_amount": line.base_amount,
                "exchange_rate": line.exchange_rate,
                "exchange_rate_date": line.exchange_rate_date,
                "exchange_rate_source": line.exchange_rate_source,
                "exchange_rate_captured_at": line.exchange_rate_captured_at,
                "matched_amount": line.matched_amount,
                "task_id": line.task_id,
                "order_date": line.order_date,
                "expected_delivery_date": line.expected_delivery_date,
                "source_requisition_id": line.source_requisition_id,
                "source_requisition_line_id": line.source_requisition_line_id,
                "source_revision": line.source_revision,
                "source_content_hash": line.source_content_hash,
                "source_idempotency_key": line.source_idempotency_key,
                "updated_by": line.updated_by,
                "updated_at": line.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
                "project_id": line.project_id,
            },
            not_found_message="Project commitment line not found.",
            stale_message="Project commitment line was updated concurrently.",
        )

    def add_source_revision(self, revision: ProjectCommitmentSourceRevision) -> None:
        context = self._context(operation_label="record commitment source revision")
        self._require_scope(revision, context)
        self.session.add(commitment_revision_to_orm(revision))

    def get_source_revision(
        self, line_id: str, source_revision: int
    ) -> ProjectCommitmentSourceRevision | None:
        context = self._context(operation_label="access commitment source revision")
        row = self.session.execute(
            select(ProjectCommitmentSourceRevisionORM).where(
                ProjectCommitmentSourceRevisionORM.tenant_id == context.tenant_id,
                ProjectCommitmentSourceRevisionORM.organization_id == context.organization_id,
                ProjectCommitmentSourceRevisionORM.commitment_line_id == line_id,
                ProjectCommitmentSourceRevisionORM.source_revision == source_revision,
            )
        ).scalar_one_or_none()
        return commitment_revision_from_orm(row) if row else None

    def add_match(self, match: ProjectCommitmentMatch) -> None:
        context = self._context(operation_label="match project commitment")
        self._require_scope(match, context)
        self.session.add(commitment_match_to_orm(match))

    def get_match(self, match_id: str) -> ProjectCommitmentMatch | None:
        context = self._context(operation_label="access project commitment match")
        row = self.session.execute(
            select(ProjectCommitmentMatchORM).where(
                ProjectCommitmentMatchORM.id == match_id,
                ProjectCommitmentMatchORM.tenant_id == context.tenant_id,
                ProjectCommitmentMatchORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return commitment_match_from_orm(row) if row else None

    def get_match_by_idempotency_key(
        self, idempotency_key: str
    ) -> ProjectCommitmentMatch | None:
        context = self._context(operation_label="access project commitment match")
        row = self.session.execute(
            select(ProjectCommitmentMatchORM).where(
                ProjectCommitmentMatchORM.tenant_id == context.tenant_id,
                ProjectCommitmentMatchORM.organization_id == context.organization_id,
                ProjectCommitmentMatchORM.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()
        return commitment_match_from_orm(row) if row else None

    def get_original_match_for_cost_entry(
        self, cost_entry_id: str
    ) -> ProjectCommitmentMatch | None:
        context = self._context(operation_label="access cost-entry commitment match")
        row = self.session.execute(
            select(ProjectCommitmentMatchORM).where(
                ProjectCommitmentMatchORM.tenant_id == context.tenant_id,
                ProjectCommitmentMatchORM.organization_id == context.organization_id,
                ProjectCommitmentMatchORM.cost_entry_id == cost_entry_id,
                ProjectCommitmentMatchORM.kind == ProjectCommitmentMatchKind.MATCH.value,
            )
        ).scalar_one_or_none()
        return commitment_match_from_orm(row) if row else None

    def has_reversal_for_match(self, match_id: str) -> bool:
        context = self._context(operation_label="check commitment match reversal")
        row = self.session.execute(
            select(ProjectCommitmentMatchORM.id).where(
                ProjectCommitmentMatchORM.tenant_id == context.tenant_id,
                ProjectCommitmentMatchORM.organization_id == context.organization_id,
                ProjectCommitmentMatchORM.reverses_match_id == match_id,
            )
        ).scalar_one_or_none()
        return row is not None

    def list_matches_for_line(self, line_id: str) -> list[ProjectCommitmentMatch]:
        context = self._context(operation_label="list project commitment matches")
        rows = self.session.execute(
            select(ProjectCommitmentMatchORM)
            .where(
                ProjectCommitmentMatchORM.tenant_id == context.tenant_id,
                ProjectCommitmentMatchORM.organization_id == context.organization_id,
                ProjectCommitmentMatchORM.commitment_line_id == line_id,
            )
            .order_by(ProjectCommitmentMatchORM.created_at.asc(), ProjectCommitmentMatchORM.id.asc())
        ).scalars().all()
        return [commitment_match_from_orm(row) for row in rows]

    def flush(self) -> None:
        self.session.flush()

    def _context(self, *, operation_label: str) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Project commitment repository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    @staticmethod
    def _require_scope(entity, context: ActiveScopeIds) -> None:
        if entity.tenant_id != context.tenant_id or entity.organization_id != context.organization_id:
            raise BusinessRuleError(
                "Project commitment scope does not match the active organization.",
                code="PROJECT_COMMITMENT_SCOPE_MISMATCH",
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

    def _require_commitment(
        self, commitment_id: str, project_id: str, context: ActiveScopeIds
    ) -> None:
        exists = self.session.execute(
            select(ProjectCommitmentORM.id).where(
                ProjectCommitmentORM.id == commitment_id,
                ProjectCommitmentORM.project_id == project_id,
                ProjectCommitmentORM.tenant_id == context.tenant_id,
                ProjectCommitmentORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if exists is None:
            raise NotFoundError("Project commitment not found.")


__all__ = ["SqlAlchemyProjectCommitmentRepository"]
