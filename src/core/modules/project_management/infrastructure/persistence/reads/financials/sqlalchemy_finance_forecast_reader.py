from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_forecast_facts import (
    ForecastLineFact,
    ForecastLineRequest,
    ForecastVersionFact,
    ForecastVersionRequest,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectCostCodeORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.forecast import (
    ForecastLineORM,
    ProjectForecastORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM


_VERSION_SORTS = {
    "title": ProjectForecastORM.name,
    "revision": ProjectForecastORM.revision,
    "statusLabel": ProjectForecastORM.status,
    "subtitle": ProjectForecastORM.as_of_date,
    "supportingText": func.coalesce(func.sum(ForecastLineORM.amount), 0),
    "metaText": ProjectForecastORM.approved_at,
}
_LINE_SORTS = {
    "title": ForecastLineORM.description,
    "statusLabel": ForecastLineORM.source_kind,
    "subtitle": ForecastLineORM.source_type,
    "supportingText": ForecastLineORM.amount,
    "metaText": ForecastLineORM.period_start,
    "costCode": ProjectCostCodeORM.code,
    "task": TaskORM.name,
}
_STATUSES = {"draft", "submitted", "approved", "rejected", "superseded"}
_GENERATION_MODES = {"automatic", "manual", "hybrid"}
_SOURCE_TYPES = {
    "remaining_plan",
    "open_commitment",
    "risk",
    "manual_estimate",
    "base_forecast",
    "financial_change",
}


class SqlAlchemyFinanceForecastReader:
    """Bounded scalar Forecast projections with no lifecycle mutation."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def list_versions(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: ForecastVersionRequest,
    ) -> FinancePageFacts[ForecastVersionFact]:
        conditions = self._version_conditions(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
        )
        status = request.status.strip().lower()
        if status in _STATUSES:
            conditions.append(ProjectForecastORM.status == status)
        generation_mode = request.generation_mode.strip().lower()
        if generation_mode in _GENERATION_MODES:
            conditions.append(ProjectForecastORM.generation_mode == generation_mode)
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(
                    ProjectForecastORM.name.ilike(pattern),
                    ProjectForecastORM.notes.ilike(pattern),
                    ProjectForecastORM.created_by.ilike(pattern),
                )
            )

        total = int(
            self._session.scalar(
                select(func.count(ProjectForecastORM.id)).where(*conditions)
            )
            or 0
        )
        page, page_size, offset = _normalized_window(
            request.normalized_page,
            request.normalized_page_size,
            total,
        )
        sort_key = request.normalized_sort_key
        direction = "asc" if request.sort_direction == "asc" else "desc"
        sort_expression = _VERSION_SORTS[sort_key]
        ordered = sort_expression.asc() if direction == "asc" else sort_expression.desc()
        rows = self._session.execute(
            self._version_projection(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            )
            .where(*conditions)
            .order_by(ordered, ProjectForecastORM.id.asc())
            .offset(offset)
            .limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(self._version_fact(row) for row in rows),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=direction,
        )

    def get_version(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        forecast_id: str,
    ) -> ForecastVersionFact | None:
        conditions = self._version_conditions(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
        )
        conditions.append(ProjectForecastORM.id == forecast_id)
        row = self._session.execute(
            self._version_projection(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
            ).where(*conditions)
        ).one_or_none()
        return self._version_fact(row) if row is not None else None

    def list_lines(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        forecast_id: str,
        request: ForecastLineRequest,
    ) -> FinancePageFacts[ForecastLineFact]:
        conditions = [
            ForecastLineORM.tenant_id == tenant_id,
            ForecastLineORM.organization_id == organization_id,
            ForecastLineORM.project_id == project_id,
            ForecastLineORM.forecast_id == forecast_id,
            ProjectForecastORM.tenant_id == tenant_id,
            ProjectForecastORM.organization_id == organization_id,
            ProjectForecastORM.project_id == project_id,
            ProjectForecastORM.id == forecast_id,
            ProjectCostCodeORM.tenant_id == tenant_id,
            ProjectCostCodeORM.organization_id == organization_id,
        ]
        source_type = request.source_type.strip().lower()
        if source_type in _SOURCE_TYPES:
            conditions.append(ForecastLineORM.source_type == source_type)
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(
                    ForecastLineORM.description.ilike(pattern),
                    ForecastLineORM.source_reference_type.ilike(pattern),
                    ForecastLineORM.source_reference_id.ilike(pattern),
                    ProjectCostCodeORM.code.ilike(pattern),
                    ProjectCostCodeORM.name.ilike(pattern),
                    TaskORM.name.ilike(pattern),
                    TaskORM.wbs_code.ilike(pattern),
                )
            )

        joined = (
            select(ForecastLineORM.id)
            .select_from(ForecastLineORM)
            .join(ProjectForecastORM, ProjectForecastORM.id == ForecastLineORM.forecast_id)
            .join(
                ProjectCostCodeORM,
                ProjectCostCodeORM.id == ForecastLineORM.cost_code_id,
            )
            .outerjoin(
                TaskORM,
                (TaskORM.id == ForecastLineORM.task_id)
                & (TaskORM.project_id == project_id),
            )
            .where(*conditions)
        )
        total = int(
            self._session.scalar(select(func.count()).select_from(joined.subquery())) or 0
        )
        page, page_size, offset = _normalized_window(
            request.normalized_page,
            request.normalized_page_size,
            total,
        )
        sort_key = request.normalized_sort_key
        direction = "asc" if request.sort_direction == "asc" else "desc"
        sort_expression = _LINE_SORTS[sort_key]
        ordered = sort_expression.asc() if direction == "asc" else sort_expression.desc()
        rows = self._session.execute(
            select(
                ForecastLineORM.id,
                ForecastLineORM.forecast_id,
                ForecastLineORM.description,
                ProjectCostCodeORM.code.label("cost_code"),
                ProjectCostCodeORM.name.label("cost_code_name"),
                TaskORM.name.label("task_name"),
                TaskORM.wbs_code,
                ForecastLineORM.amount,
                ForecastLineORM.currency_code,
                ForecastLineORM.source_kind,
                ForecastLineORM.source_type,
                ForecastLineORM.source_reference_type,
                ForecastLineORM.source_reference_id,
                ForecastLineORM.source_snapshot_at,
                ForecastLineORM.period_start,
                ForecastLineORM.period_end,
                ForecastLineORM.version,
            )
            .select_from(ForecastLineORM)
            .join(ProjectForecastORM, ProjectForecastORM.id == ForecastLineORM.forecast_id)
            .join(
                ProjectCostCodeORM,
                ProjectCostCodeORM.id == ForecastLineORM.cost_code_id,
            )
            .outerjoin(
                TaskORM,
                (TaskORM.id == ForecastLineORM.task_id)
                & (TaskORM.project_id == project_id),
            )
            .where(*conditions)
            .order_by(ordered, ForecastLineORM.id.asc())
            .offset(offset)
            .limit(page_size)
        ).all()
        return FinancePageFacts(
            items=tuple(
                ForecastLineFact(
                    id=row.id,
                    forecast_id=row.forecast_id,
                    description=row.description,
                    cost_code=row.cost_code,
                    cost_code_name=row.cost_code_name,
                    task_name=row.task_name or "Unassigned",
                    wbs_code=row.wbs_code or "",
                    amount=Decimal(row.amount),
                    currency_code=row.currency_code,
                    source_kind=row.source_kind,
                    source_type=row.source_type,
                    source_reference_type=row.source_reference_type or "",
                    source_reference_id=row.source_reference_id or "",
                    source_snapshot_at=row.source_snapshot_at,
                    period_start=row.period_start,
                    period_end=row.period_end,
                    row_version=row.version,
                )
                for row in rows
            ),
            total=total,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=direction,
        )

    @staticmethod
    def _version_conditions(
        *, tenant_id: str, organization_id: str, project_id: str
    ) -> list:
        return [
            ProjectForecastORM.tenant_id == tenant_id,
            ProjectForecastORM.organization_id == organization_id,
            ProjectForecastORM.project_id == project_id,
        ]

    @staticmethod
    def _version_projection(*, tenant_id: str, organization_id: str, project_id: str):
        line_join = (
            (ForecastLineORM.tenant_id == tenant_id)
            & (ForecastLineORM.organization_id == organization_id)
            & (ForecastLineORM.project_id == project_id)
            & (ForecastLineORM.forecast_id == ProjectForecastORM.id)
        )
        return (
            select(
                ProjectForecastORM.id,
                ProjectForecastORM.name,
                ProjectForecastORM.status,
                ProjectForecastORM.revision,
                ProjectForecastORM.version,
                ProjectForecastORM.currency_code,
                ProjectForecastORM.as_of_date,
                ProjectForecastORM.generation_mode,
                ProjectForecastORM.submitted_by,
                ProjectForecastORM.submitted_at,
                ProjectForecastORM.approved_by,
                ProjectForecastORM.approved_at,
                ProjectForecastORM.notes,
                func.count(ForecastLineORM.id).label("line_count"),
                func.coalesce(func.sum(ForecastLineORM.amount), 0).label("total_etc"),
            )
            .select_from(ProjectForecastORM)
            .outerjoin(ForecastLineORM, line_join)
            .group_by(
                ProjectForecastORM.id,
                ProjectForecastORM.name,
                ProjectForecastORM.status,
                ProjectForecastORM.revision,
                ProjectForecastORM.version,
                ProjectForecastORM.currency_code,
                ProjectForecastORM.as_of_date,
                ProjectForecastORM.generation_mode,
                ProjectForecastORM.submitted_by,
                ProjectForecastORM.submitted_at,
                ProjectForecastORM.approved_by,
                ProjectForecastORM.approved_at,
                ProjectForecastORM.notes,
            )
        )

    @staticmethod
    def _version_fact(row) -> ForecastVersionFact:
        return ForecastVersionFact(
            id=row.id,
            name=row.name,
            status=row.status,
            revision=row.revision,
            row_version=row.version,
            currency_code=row.currency_code,
            as_of_date=row.as_of_date,
            generation_mode=row.generation_mode,
            line_count=int(row.line_count or 0),
            total_etc=Decimal(row.total_etc or 0),
            submitted_by=row.submitted_by,
            submitted_at=row.submitted_at,
            approved_by=row.approved_by,
            approved_at=row.approved_at,
            notes=row.notes,
        )


def _normalized_window(page: int, page_size: int, total: int) -> tuple[int, int, int]:
    last_page = max(1, (max(0, total) + page_size - 1) // page_size)
    normalized_page = min(page, last_page)
    return normalized_page, page_size, (normalized_page - 1) * page_size


__all__ = ["SqlAlchemyFinanceForecastReader"]
