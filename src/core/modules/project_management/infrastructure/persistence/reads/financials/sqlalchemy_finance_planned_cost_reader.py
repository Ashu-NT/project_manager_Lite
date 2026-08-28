from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageFacts,
    FinancePageRequest,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_planned_cost_facts import (
    PlannedCostLineFact,
    PlannedCostVersionFact,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectCostCodeORM,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.statements.planned_cost_rows import (
    PlannedCostLineRow,
    PlannedCostVersionRow,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
    ResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM


_VERSION_SORTS = {
    "title": PlannedCostVersionRow.revision,
    "revision": PlannedCostVersionRow.revision,
    "statusLabel": PlannedCostVersionRow.status,
    "subtitle": PlannedCostVersionRow.as_of,
    "supportingText": func.coalesce(func.sum(PlannedCostLineRow.amount), 0),
    "metaText": PlannedCostVersionRow.calculated_at,
}
_LINE_SORTS = {
    "title": TaskORM.name,
    "statusLabel": PlannedCostVersionRow.status,
    "subtitle": ResourceORM.name,
    "supportingText": PlannedCostLineRow.amount,
    "metaText": ProjectCostCodeORM.code,
}


class SqlAlchemyFinancePlannedCostReader:
    """Bounded scalar planned-cost projection; never hydrates domain snapshots."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def list_versions(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinancePageRequest,
    ) -> FinancePageFacts[PlannedCostVersionFact]:
        conditions = [
            PlannedCostVersionRow.tenant_id == tenant_id,
            PlannedCostVersionRow.organization_id == organization_id,
            PlannedCostVersionRow.project_id == project_id,
        ]
        if request.status.strip():
            conditions.append(
                PlannedCostVersionRow.status == request.status.strip().lower()
            )
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(
                    PlannedCostVersionRow.calculated_by.ilike(pattern),
                    PlannedCostVersionRow.currency_code.ilike(pattern),
                )
            )

        total = int(
            self._session.scalar(
                select(func.count(PlannedCostVersionRow.id)).where(*conditions)
            )
            or 0
        )
        page, page_size, offset = _normalized_window(request, total)
        sort_key = request.sort_key if request.sort_key in _VERSION_SORTS else "revision"
        direction = "asc" if request.sort_direction == "asc" else "desc"
        sort_expression = _VERSION_SORTS[sort_key]
        ordered = sort_expression.asc() if direction == "asc" else sort_expression.desc()

        line_join = (
            (PlannedCostLineRow.tenant_id == PlannedCostVersionRow.tenant_id)
            & (
                PlannedCostLineRow.organization_id
                == PlannedCostVersionRow.organization_id
            )
            & (PlannedCostLineRow.project_id == PlannedCostVersionRow.project_id)
            & (PlannedCostLineRow.version_id == PlannedCostVersionRow.id)
        )
        stmt = (
            select(
                PlannedCostVersionRow.id,
                PlannedCostVersionRow.revision,
                PlannedCostVersionRow.status,
                PlannedCostVersionRow.currency_code,
                PlannedCostVersionRow.as_of,
                PlannedCostVersionRow.calculated_by,
                PlannedCostVersionRow.calculated_at,
                PlannedCostVersionRow.rates_complete,
                PlannedCostVersionRow.allocations_complete,
                PlannedCostVersionRow.cost_codes_complete,
                PlannedCostVersionRow.unresolved_rate_count,
                PlannedCostVersionRow.partially_allocated_resource_count,
                PlannedCostVersionRow.unclassified_line_count,
                func.count(PlannedCostLineRow.id).label("line_count"),
                func.coalesce(func.sum(PlannedCostLineRow.planned_hours), 0).label(
                    "total_hours"
                ),
                func.coalesce(func.sum(PlannedCostLineRow.amount), 0).label(
                    "total_amount"
                ),
            )
            .select_from(PlannedCostVersionRow)
            .outerjoin(PlannedCostLineRow, line_join)
            .where(*conditions)
            .group_by(
                PlannedCostVersionRow.id,
                PlannedCostVersionRow.revision,
                PlannedCostVersionRow.status,
                PlannedCostVersionRow.currency_code,
                PlannedCostVersionRow.as_of,
                PlannedCostVersionRow.calculated_by,
                PlannedCostVersionRow.calculated_at,
                PlannedCostVersionRow.rates_complete,
                PlannedCostVersionRow.allocations_complete,
                PlannedCostVersionRow.cost_codes_complete,
                PlannedCostVersionRow.unresolved_rate_count,
                PlannedCostVersionRow.partially_allocated_resource_count,
                PlannedCostVersionRow.unclassified_line_count,
            )
            .order_by(ordered, PlannedCostVersionRow.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self._session.execute(stmt).all()
        return FinancePageFacts(
            items=tuple(
                PlannedCostVersionFact(
                    id=row.id,
                    revision=row.revision,
                    status=row.status,
                    currency_code=row.currency_code,
                    as_of=row.as_of,
                    calculated_by=row.calculated_by,
                    calculated_at=row.calculated_at,
                    line_count=int(row.line_count or 0),
                    total_hours=Decimal(row.total_hours or 0),
                    total_amount=Decimal(row.total_amount or 0),
                    rates_complete=bool(row.rates_complete),
                    allocations_complete=bool(row.allocations_complete),
                    cost_codes_complete=bool(row.cost_codes_complete),
                    unresolved_rate_count=int(row.unresolved_rate_count),
                    partially_allocated_resource_count=int(
                        row.partially_allocated_resource_count
                    ),
                    unclassified_line_count=int(row.unclassified_line_count),
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
        version_id: str,
        request: FinancePageRequest,
    ) -> FinancePageFacts[PlannedCostLineFact]:
        conditions = [
            PlannedCostLineRow.tenant_id == tenant_id,
            PlannedCostLineRow.organization_id == organization_id,
            PlannedCostLineRow.project_id == project_id,
            PlannedCostLineRow.version_id == version_id,
            PlannedCostVersionRow.tenant_id == tenant_id,
            PlannedCostVersionRow.organization_id == organization_id,
            PlannedCostVersionRow.project_id == project_id,
            PlannedCostVersionRow.id == version_id,
            ResourceORM.tenant_id == tenant_id,
            ResourceORM.organization_id == organization_id,
            ProjectCostCodeORM.tenant_id == tenant_id,
            ProjectCostCodeORM.organization_id == organization_id,
        ]
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(
                    TaskORM.name.ilike(pattern),
                    TaskORM.wbs_code.ilike(pattern),
                    ResourceORM.name.ilike(pattern),
                    ResourceORM.resource_code.ilike(pattern),
                    ProjectCostCodeORM.code.ilike(pattern),
                    ProjectCostCodeORM.name.ilike(pattern),
                )
            )

        base = (
            select(PlannedCostLineRow.id)
            .select_from(PlannedCostLineRow)
            .join(
                PlannedCostVersionRow,
                PlannedCostVersionRow.id == PlannedCostLineRow.version_id,
            )
            .join(
                TaskORM,
                (TaskORM.id == PlannedCostLineRow.task_id)
                & (TaskORM.project_id == project_id),
            )
            .join(ResourceORM, ResourceORM.id == PlannedCostLineRow.resource_id)
            .join(
                ProjectCostCodeORM,
                ProjectCostCodeORM.id == PlannedCostLineRow.cost_code_id,
            )
            .where(*conditions)
        )
        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        page, page_size, offset = _normalized_window(request, total)
        sort_key = request.sort_key if request.sort_key in _LINE_SORTS else "title"
        direction = "asc" if request.sort_direction == "asc" else "desc"
        sort_expression = _LINE_SORTS[sort_key]
        ordered = sort_expression.asc() if direction == "asc" else sort_expression.desc()

        stmt = (
            select(
                PlannedCostLineRow.id,
                PlannedCostLineRow.version_id,
                PlannedCostVersionRow.revision.label("version_revision"),
                PlannedCostVersionRow.status.label("version_status"),
                TaskORM.name.label("task_name"),
                TaskORM.wbs_code,
                ResourceORM.name.label("resource_name"),
                ResourceORM.resource_code,
                ProjectCostCodeORM.code.label("cost_code"),
                ProjectCostCodeORM.name.label("cost_code_name"),
                PlannedCostLineRow.planned_hours,
                PlannedCostLineRow.rate_amount,
                PlannedCostLineRow.amount,
                PlannedCostLineRow.currency_code,
                PlannedCostLineRow.rate_card_id,
                PlannedCostLineRow.rate_card_version,
            )
            .select_from(PlannedCostLineRow)
            .join(
                PlannedCostVersionRow,
                PlannedCostVersionRow.id == PlannedCostLineRow.version_id,
            )
            .join(
                TaskORM,
                (TaskORM.id == PlannedCostLineRow.task_id)
                & (TaskORM.project_id == project_id),
            )
            .join(ResourceORM, ResourceORM.id == PlannedCostLineRow.resource_id)
            .join(
                ProjectCostCodeORM,
                ProjectCostCodeORM.id == PlannedCostLineRow.cost_code_id,
            )
            .where(*conditions)
            .order_by(ordered, PlannedCostLineRow.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self._session.execute(stmt).all()
        return FinancePageFacts(
            items=tuple(
                PlannedCostLineFact(
                    id=row.id,
                    version_id=row.version_id,
                    version_revision=row.version_revision,
                    version_status=row.version_status,
                    task_name=row.task_name,
                    wbs_code=row.wbs_code,
                    resource_name=row.resource_name,
                    resource_code=row.resource_code or "",
                    cost_code=row.cost_code,
                    cost_code_name=row.cost_code_name,
                    planned_hours=Decimal(row.planned_hours),
                    rate_amount=Decimal(row.rate_amount),
                    amount=Decimal(row.amount),
                    currency_code=row.currency_code,
                    rate_card_id=row.rate_card_id,
                    rate_card_version=row.rate_card_version,
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


__all__ = ["SqlAlchemyFinancePlannedCostReader"]

