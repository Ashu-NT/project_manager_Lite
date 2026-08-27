from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    BudgetLineFact,
    BudgetVersionFact,
    FinancePageFacts,
    FinancePageRequest,
)
from src.core.modules.project_management.infrastructure.persistence.orm.budget import (
    BudgetLineORM,
    ProjectBudgetORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectCostCodeORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM


_VERSION_SORTS = {
    "title": ProjectBudgetORM.name,
    "statusLabel": ProjectBudgetORM.status,
    "supportingText": func.coalesce(func.sum(BudgetLineORM.amount), 0),
    "metaText": ProjectBudgetORM.approved_at,
    "revision": ProjectBudgetORM.revision,
}
_LINE_SORTS = {
    "title": BudgetLineORM.description,
    "subtitle": ProjectCostCodeORM.code,
    "supportingText": BudgetLineORM.amount,
    "metaText": ProjectBudgetORM.revision,
}


class SqlAlchemyFinanceBudgetReader:
    """Bounded scalar Budget projection; never hydrates Finance aggregates."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def list_versions(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinancePageRequest,
    ) -> FinancePageFacts[BudgetVersionFact]:
        conditions = [
            ProjectBudgetORM.tenant_id == tenant_id,
            ProjectBudgetORM.organization_id == organization_id,
            ProjectBudgetORM.project_id == project_id,
        ]
        if request.status.strip():
            conditions.append(ProjectBudgetORM.status == request.status.strip().lower())
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(
                    ProjectBudgetORM.name.ilike(pattern),
                    ProjectBudgetORM.notes.ilike(pattern),
                )
            )

        total = int(
            self._session.scalar(
                select(func.count(ProjectBudgetORM.id)).where(*conditions)
            )
            or 0
        )
        page, page_size, offset = _normalized_window(request, total)
        sort_key = request.sort_key if request.sort_key in _VERSION_SORTS else "revision"
        direction = "asc" if request.sort_direction == "asc" else "desc"
        sort_expression = _VERSION_SORTS[sort_key]
        ordered = sort_expression.asc() if direction == "asc" else sort_expression.desc()

        line_join = (
            (BudgetLineORM.tenant_id == ProjectBudgetORM.tenant_id)
            & (BudgetLineORM.organization_id == ProjectBudgetORM.organization_id)
            & (BudgetLineORM.project_id == ProjectBudgetORM.project_id)
            & (BudgetLineORM.budget_id == ProjectBudgetORM.id)
        )
        stmt = (
            select(
                ProjectBudgetORM.id,
                ProjectBudgetORM.name,
                ProjectBudgetORM.status,
                ProjectBudgetORM.revision,
                ProjectBudgetORM.version,
                ProjectBudgetORM.currency_code,
                ProjectBudgetORM.submitted_by,
                ProjectBudgetORM.submitted_at,
                ProjectBudgetORM.approved_by,
                ProjectBudgetORM.approved_at,
                ProjectBudgetORM.notes,
                func.count(BudgetLineORM.id).label("line_count"),
                func.coalesce(func.sum(BudgetLineORM.amount), 0).label("total_amount"),
            )
            .select_from(ProjectBudgetORM)
            .outerjoin(BudgetLineORM, line_join)
            .where(*conditions)
            .group_by(
                ProjectBudgetORM.id,
                ProjectBudgetORM.name,
                ProjectBudgetORM.status,
                ProjectBudgetORM.revision,
                ProjectBudgetORM.version,
                ProjectBudgetORM.currency_code,
                ProjectBudgetORM.submitted_by,
                ProjectBudgetORM.submitted_at,
                ProjectBudgetORM.approved_by,
                ProjectBudgetORM.approved_at,
                ProjectBudgetORM.notes,
            )
            .order_by(ordered, ProjectBudgetORM.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self._session.execute(stmt).all()
        return FinancePageFacts(
            items=tuple(
                BudgetVersionFact(
                    id=row.id,
                    name=row.name,
                    status=row.status,
                    revision=row.revision,
                    row_version=row.version,
                    currency_code=row.currency_code,
                    line_count=int(row.line_count or 0),
                    total_amount=Decimal(row.total_amount or 0),
                    submitted_by=row.submitted_by,
                    submitted_at=row.submitted_at,
                    approved_by=row.approved_by,
                    approved_at=row.approved_at,
                    notes=row.notes,
                )
                for row in rows
            ),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=direction,
        )

    def list_lines(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        budget_id: str,
        request: FinancePageRequest,
    ) -> FinancePageFacts[BudgetLineFact]:
        conditions = [
            BudgetLineORM.tenant_id == tenant_id,
            BudgetLineORM.organization_id == organization_id,
            BudgetLineORM.project_id == project_id,
            BudgetLineORM.budget_id == budget_id,
            ProjectBudgetORM.tenant_id == tenant_id,
            ProjectBudgetORM.organization_id == organization_id,
            ProjectBudgetORM.project_id == project_id,
            ProjectBudgetORM.id == budget_id,
        ]
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(
                    BudgetLineORM.description.ilike(pattern),
                    ProjectCostCodeORM.code.ilike(pattern),
                    ProjectCostCodeORM.name.ilike(pattern),
                    TaskORM.name.ilike(pattern),
                    TaskORM.wbs_code.ilike(pattern),
                )
            )

        joins = (
            ProjectBudgetORM,
            ProjectBudgetORM.id == BudgetLineORM.budget_id,
            ProjectCostCodeORM,
            (ProjectCostCodeORM.id == BudgetLineORM.cost_code_id)
            & (ProjectCostCodeORM.tenant_id == tenant_id)
            & (ProjectCostCodeORM.organization_id == organization_id),
        )
        count_stmt = (
            select(func.count(BudgetLineORM.id))
            .select_from(BudgetLineORM)
            .join(joins[0], joins[1])
            .join(joins[2], joins[3])
            .outerjoin(
                TaskORM,
                (TaskORM.id == BudgetLineORM.task_id)
                & (TaskORM.project_id == project_id),
            )
            .where(*conditions)
        )
        total = int(self._session.scalar(count_stmt) or 0)
        page, page_size, offset = _normalized_window(request, total)
        sort_key = request.sort_key if request.sort_key in _LINE_SORTS else "metaText"
        direction = "asc" if request.sort_direction == "asc" else "desc"
        sort_expression = _LINE_SORTS[sort_key]
        ordered = sort_expression.asc() if direction == "asc" else sort_expression.desc()

        stmt = (
            select(
                BudgetLineORM.id,
                BudgetLineORM.budget_id,
                ProjectBudgetORM.name.label("budget_name"),
                ProjectBudgetORM.revision.label("budget_revision"),
                ProjectBudgetORM.status.label("budget_status"),
                BudgetLineORM.description,
                ProjectCostCodeORM.code.label("cost_code"),
                ProjectCostCodeORM.name.label("cost_code_name"),
                TaskORM.name.label("task_name"),
                TaskORM.wbs_code,
                BudgetLineORM.amount,
                BudgetLineORM.currency_code,
            )
            .select_from(BudgetLineORM)
            .join(joins[0], joins[1])
            .join(joins[2], joins[3])
            .outerjoin(
                TaskORM,
                (TaskORM.id == BudgetLineORM.task_id)
                & (TaskORM.project_id == project_id),
            )
            .where(*conditions)
            .order_by(ordered, BudgetLineORM.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self._session.execute(stmt).all()
        return FinancePageFacts(
            items=tuple(
                BudgetLineFact(
                    id=row.id,
                    budget_id=row.budget_id,
                    budget_name=row.budget_name,
                    budget_revision=row.budget_revision,
                    budget_status=row.budget_status,
                    description=row.description,
                    cost_code=row.cost_code,
                    cost_code_name=row.cost_code_name,
                    task_name=row.task_name or "Unassigned",
                    wbs_code=row.wbs_code or "",
                    amount=Decimal(row.amount),
                    currency_code=row.currency_code,
                )
                for row in rows
            ),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=direction,
        )


def _normalized_window(request: FinancePageRequest, total: int) -> tuple[int, int, int]:
    page_size = request.normalized_page_size
    last_page = max(1, (max(0, total) + page_size - 1) // page_size)
    page = min(request.normalized_page, last_page)
    return page, page_size, (page - 1) * page_size


__all__ = ["SqlAlchemyFinanceBudgetReader"]
