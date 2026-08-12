from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.domain.financials.budget import (
    BudgetLine,
    ProjectBudget,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.budget import (
    budget_from_orm,
    budget_line_from_orm,
    budget_line_to_orm,
    budget_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.budget import (
    BudgetLineORM,
    ProjectBudgetORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds, TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.infra.persistence.db.optimistic import (
    delete_with_version_check,
    update_with_version_check,
)

_OPEN_STATUSES = ("draft", "submitted")


class _BudgetScope:
    session: Session
    _tenant_context_service: TenantContextService | None

    def _context(self, *, operation_label: str) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Budget repository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    @staticmethod
    def _require_entity_scope(entity, context: ActiveScopeIds) -> None:
        if (
            entity.tenant_id != context.tenant_id
            or entity.organization_id != context.organization_id
        ):
            raise BusinessRuleError(
                "Budget scope does not match the active organization.",
                code="PROJECT_BUDGET_SCOPE_MISMATCH",
            )

    def _require_project(self, project_id: str, context: ActiveScopeIds) -> None:
        project = self.session.execute(
            select(ProjectORM.id).where(
                ProjectORM.id == project_id,
                ProjectORM.tenant_id == context.tenant_id,
                ProjectORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found.")


class SqlAlchemyProjectBudgetRepository(_BudgetScope, ProjectBudgetRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def add(self, budget: ProjectBudget) -> None:
        context = self._context(operation_label="create project budget")
        self._require_entity_scope(budget, context)
        self._require_project(budget.project_id, context)
        self.session.add(budget_to_orm(budget))

    def get(self, budget_id: str) -> ProjectBudget | None:
        context = self._context(operation_label="access project budget")
        row = self.session.execute(
            select(ProjectBudgetORM).where(
                ProjectBudgetORM.id == budget_id,
                ProjectBudgetORM.tenant_id == context.tenant_id,
                ProjectBudgetORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return budget_from_orm(row) if row else None

    def list_for_project(
        self, project_id: str, *, include_superseded: bool = True
    ) -> list[ProjectBudget]:
        context = self._context(operation_label="list project budgets")
        stmt = select(ProjectBudgetORM).where(
            ProjectBudgetORM.tenant_id == context.tenant_id,
            ProjectBudgetORM.organization_id == context.organization_id,
            ProjectBudgetORM.project_id == project_id,
        )
        if not include_superseded:
            stmt = stmt.where(ProjectBudgetORM.status != "superseded")
        rows = (
            self.session.execute(stmt.order_by(ProjectBudgetORM.revision.desc()))
            .scalars()
            .all()
        )
        return [budget_from_orm(row) for row in rows]

    def get_latest_for_project(self, project_id: str) -> ProjectBudget | None:
        context = self._context(operation_label="access latest project budget")
        row = self.session.execute(
            select(ProjectBudgetORM)
            .where(
                ProjectBudgetORM.tenant_id == context.tenant_id,
                ProjectBudgetORM.organization_id == context.organization_id,
                ProjectBudgetORM.project_id == project_id,
            )
            .order_by(ProjectBudgetORM.revision.desc())
            .limit(1)
        ).scalar_one_or_none()
        return budget_from_orm(row) if row else None

    def get_approved_for_project(self, project_id: str) -> ProjectBudget | None:
        context = self._context(operation_label="access approved project budget")
        row = self.session.execute(
            select(ProjectBudgetORM).where(
                ProjectBudgetORM.tenant_id == context.tenant_id,
                ProjectBudgetORM.organization_id == context.organization_id,
                ProjectBudgetORM.project_id == project_id,
                ProjectBudgetORM.status == "approved",
            )
        ).scalar_one_or_none()
        return budget_from_orm(row) if row else None

    def has_open_for_project(self, project_id: str) -> bool:
        context = self._context(operation_label="check open project budget")
        row = self.session.execute(
            select(ProjectBudgetORM.id).where(
                ProjectBudgetORM.tenant_id == context.tenant_id,
                ProjectBudgetORM.organization_id == context.organization_id,
                ProjectBudgetORM.project_id == project_id,
                ProjectBudgetORM.status.in_(_OPEN_STATUSES),
            )
        ).scalar_one_or_none()
        return row is not None

    def update(self, budget: ProjectBudget, *, expected_row_version: int) -> None:
        context = self._context(operation_label="update project budget")
        self._require_entity_scope(budget, context)
        budget.row_version = update_with_version_check(
            self.session,
            ProjectBudgetORM,
            budget.id,
            expected_row_version,
            {
                "name": budget.name,
                "status": budget.status.value,
                "submitted_by": budget.submitted_by,
                "submitted_at": budget.submitted_at,
                "approved_by": budget.approved_by,
                "approved_at": budget.approved_at,
                "rejected_by": budget.rejected_by,
                "rejected_at": budget.rejected_at,
                "superseded_by": budget.superseded_by,
                "superseded_at": budget.superseded_at,
                "closed_by": budget.closed_by,
                "closed_at": budget.closed_at,
                "notes": budget.notes,
                "submission_notes": budget.submission_notes,
                "approval_notes": budget.approval_notes,
                "rejection_notes": budget.rejection_notes,
                "closure_notes": budget.closure_notes,
                "updated_at": budget.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
            },
            not_found_message="Project budget not found.",
            stale_message="Project budget was updated by another user.",
        )

    def delete(self, budget_id: str, *, expected_row_version: int) -> None:
        context = self._context(operation_label="delete project budget")
        delete_with_version_check(
            self.session,
            ProjectBudgetORM,
            budget_id,
            expected_row_version,
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
            },
            not_found_message="Project budget not found.",
            stale_message="Project budget was updated by another user.",
        )

    def add_line(self, line: BudgetLine) -> None:
        context = self._context(operation_label="create project budget line")
        self._require_entity_scope(line, context)
        self._require_budget(line.budget_id, context)
        self.session.add(budget_line_to_orm(line))

    def get_line(self, line_id: str) -> BudgetLine | None:
        context = self._context(operation_label="access project budget line")
        row = self.session.execute(
            select(BudgetLineORM).where(
                BudgetLineORM.id == line_id,
                BudgetLineORM.tenant_id == context.tenant_id,
                BudgetLineORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        return budget_line_from_orm(row) if row else None

    def update_line(self, line: BudgetLine, *, expected_row_version: int) -> None:
        context = self._context(operation_label="update project budget line")
        self._require_entity_scope(line, context)
        line.row_version = update_with_version_check(
            self.session,
            BudgetLineORM,
            line.id,
            expected_row_version,
            {
                "cost_code_id": line.cost_code_id,
                "task_id": line.task_id,
                "description": line.description,
                "amount": line.amount,
                "currency_code": line.currency_code,
                "updated_at": line.updated_at,
            },
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
                "budget_id": line.budget_id,
            },
            not_found_message="Project budget line not found.",
            stale_message="Project budget line was updated by another user.",
        )

    def delete_line(self, line_id: str, *, expected_row_version: int) -> None:
        context = self._context(operation_label="delete project budget line")
        delete_with_version_check(
            self.session,
            BudgetLineORM,
            line_id,
            expected_row_version,
            extra_filters={
                "tenant_id": context.tenant_id,
                "organization_id": context.organization_id,
            },
            not_found_message="Project budget line not found.",
            stale_message="Project budget line was updated by another user.",
        )

    def list_lines(self, budget_id: str) -> list[BudgetLine]:
        context = self._context(operation_label="list project budget lines")
        rows = self.session.execute(
            select(BudgetLineORM).where(
                BudgetLineORM.budget_id == budget_id,
                BudgetLineORM.tenant_id == context.tenant_id,
                BudgetLineORM.organization_id == context.organization_id,
            )
        ).scalars().all()
        return [budget_line_from_orm(row) for row in rows]

    def list_lines_for_project(
        self, project_id: str, *, offset: int = 0, limit: int = 50
    ) -> list[BudgetLine]:
        context = self._context(operation_label="list project budget lines")
        rows = (
            self.session.execute(
                select(BudgetLineORM)
                .join(ProjectBudgetORM, ProjectBudgetORM.id == BudgetLineORM.budget_id)
                .where(
                    BudgetLineORM.tenant_id == context.tenant_id,
                    BudgetLineORM.organization_id == context.organization_id,
                    BudgetLineORM.project_id == project_id,
                    ProjectBudgetORM.tenant_id == context.tenant_id,
                    ProjectBudgetORM.organization_id == context.organization_id,
                    ProjectBudgetORM.project_id == project_id,
                )
                .order_by(
                    ProjectBudgetORM.revision.desc(),
                    BudgetLineORM.created_at.asc(),
                    BudgetLineORM.id.asc(),
                )
                .offset(max(0, offset))
                .limit(max(1, limit))
            )
            .scalars()
            .all()
        )
        return [budget_line_from_orm(row) for row in rows]

    def summarize_lines_for_project(
        self, project_id: str
    ) -> dict[str, tuple[int, Decimal]]:
        context = self._context(operation_label="summarize project budget lines")
        rows = self.session.execute(
            select(
                BudgetLineORM.budget_id,
                func.count(BudgetLineORM.id),
                func.coalesce(func.sum(BudgetLineORM.amount), 0),
            )
            .where(
                    BudgetLineORM.project_id == project_id,
                    BudgetLineORM.tenant_id == context.tenant_id,
                    BudgetLineORM.organization_id == context.organization_id,
                )
            .group_by(BudgetLineORM.budget_id)
        ).all()
        return {
            str(budget_id): (int(line_count), total_amount)
            for budget_id, line_count, total_amount in rows
        }

    def flush(self) -> None:
        self.session.flush()

    def _require_budget(self, budget_id: str, context: ActiveScopeIds) -> ProjectBudgetORM:
        row = self.session.execute(
            select(ProjectBudgetORM).where(
                ProjectBudgetORM.id == budget_id,
                ProjectBudgetORM.tenant_id == context.tenant_id,
                ProjectBudgetORM.organization_id == context.organization_id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError("Project budget not found.")
        return row


__all__ = ["SqlAlchemyProjectBudgetRepository"]
