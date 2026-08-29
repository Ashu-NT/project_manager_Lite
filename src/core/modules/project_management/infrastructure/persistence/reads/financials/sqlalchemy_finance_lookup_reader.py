from __future__ import annotations

from datetime import date

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.financials.models.finance_lookup_facts import (
    FinanceLookupOptionFact,
    FinanceLookupPageFacts,
    FinanceLookupQuery,
    ManualActualCostCodeQuery,
    ManualActualDefaultsFacts,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectCostCodeORM,
    ProjectCostCodeRestrictionORM,
    ProjectFinancialProfileORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM


class SqlAlchemyFinanceLookupReader:
    """Bounded, scope-explicit selectors used by Project Finance commands."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def search_projects(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        require_active_finance_profile: bool,
        request: FinanceLookupQuery,
    ) -> FinanceLookupPageFacts:
        conditions = [
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
        ]
        if allowed_project_ids is not None:
            if not allowed_project_ids:
                return _empty_page(request.normalized_page, request.normalized_page_size)
            conditions.append(ProjectORM.id.in_(allowed_project_ids))
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(ProjectORM.name.ilike(pattern), ProjectORM.project_code.ilike(pattern))
            )
        base = select(ProjectORM.id, ProjectORM.project_code, ProjectORM.name).where(*conditions)
        if require_active_finance_profile:
            base = base.join(
                ProjectFinancialProfileORM,
                and_(
                    ProjectFinancialProfileORM.tenant_id == ProjectORM.tenant_id,
                    ProjectFinancialProfileORM.organization_id == ProjectORM.organization_id,
                    ProjectFinancialProfileORM.project_id == ProjectORM.id,
                    ProjectFinancialProfileORM.status == "active",
                ),
            )
        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        page, page_size, offset = _window(
            request.normalized_page, request.normalized_page_size, total
        )
        rows = self._session.execute(
            base.order_by(ProjectORM.name.asc(), ProjectORM.id.asc())
            .offset(offset)
            .limit(page_size)
        ).all()
        return FinanceLookupPageFacts(
            items=tuple(
                FinanceLookupOptionFact(
                    id=str(row.id), label=_project_label(row.project_code, row.name)
                )
                for row in rows
            ),
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_project_option(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        require_active_finance_profile: bool,
    ) -> FinanceLookupOptionFact | None:
        if allowed_project_ids is not None and project_id not in allowed_project_ids:
            return None
        statement = select(ProjectORM.id, ProjectORM.project_code, ProjectORM.name).where(
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
            ProjectORM.id == project_id,
        )
        if require_active_finance_profile:
            statement = statement.join(
                ProjectFinancialProfileORM,
                and_(
                    ProjectFinancialProfileORM.tenant_id == ProjectORM.tenant_id,
                    ProjectFinancialProfileORM.organization_id == ProjectORM.organization_id,
                    ProjectFinancialProfileORM.project_id == ProjectORM.id,
                    ProjectFinancialProfileORM.status == "active",
                ),
            )
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        return FinanceLookupOptionFact(
            id=str(row.id), label=_project_label(row.project_code, row.name)
        )

    def search_tasks(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: FinanceLookupQuery,
    ) -> FinanceLookupPageFacts:
        conditions = [
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
            ProjectORM.id == project_id,
            TaskORM.project_id == project_id,
        ]
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            conditions.append(
                or_(
                    TaskORM.name.ilike(pattern),
                    TaskORM.task_code.ilike(pattern),
                    TaskORM.wbs_code.ilike(pattern),
                )
            )
        base = (
            select(TaskORM.id, TaskORM.task_code, TaskORM.wbs_code, TaskORM.name)
            .select_from(TaskORM)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(*conditions)
        )
        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        page, page_size, offset = _window(
            request.normalized_page, request.normalized_page_size, total
        )
        rows = self._session.execute(
            base.order_by(TaskORM.wbs_code.asc(), TaskORM.name.asc(), TaskORM.id.asc())
            .offset(offset)
            .limit(page_size)
        ).all()
        return FinanceLookupPageFacts(
            items=tuple(
                FinanceLookupOptionFact(id=str(row.id), label=_task_label(row))
                for row in rows
            ),
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_task_option(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        task_id: str,
    ) -> FinanceLookupOptionFact | None:
        row = self._session.execute(
            select(TaskORM.id, TaskORM.task_code, TaskORM.wbs_code, TaskORM.name)
            .select_from(TaskORM)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(
                ProjectORM.tenant_id == tenant_id,
                ProjectORM.organization_id == organization_id,
                ProjectORM.id == project_id,
                TaskORM.project_id == project_id,
                TaskORM.id == task_id,
            )
        ).one_or_none()
        return (
            FinanceLookupOptionFact(id=str(row.id), label=_task_label(row))
            if row is not None
            else None
        )

    def search_cost_codes(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        request: ManualActualCostCodeQuery,
    ) -> FinanceLookupPageFacts:
        effective_on = request.effective_on or date.today()
        base = self._cost_code_statement(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            effective_on=effective_on,
        )
        if request.search.strip():
            pattern = f"%{request.search.strip()}%"
            base = base.where(
                or_(
                    ProjectCostCodeORM.code.ilike(pattern),
                    ProjectCostCodeORM.name.ilike(pattern),
                )
            )
        total = int(self._session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        page, page_size, offset = _window(
            request.normalized_page, request.normalized_page_size, total
        )
        rows = self._session.execute(
            base.order_by(ProjectCostCodeORM.code.asc(), ProjectCostCodeORM.id.asc())
            .offset(offset)
            .limit(page_size)
        ).all()
        return FinanceLookupPageFacts(
            items=tuple(
                FinanceLookupOptionFact(
                    id=str(row.id), label=f"{row.code} - {row.name}"
                )
                for row in rows
            ),
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_cost_code_option(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        cost_code_id: str,
        effective_on: date | None,
    ) -> FinanceLookupOptionFact | None:
        row = self._session.execute(
            self._cost_code_statement(
                tenant_id=tenant_id,
                organization_id=organization_id,
                project_id=project_id,
                effective_on=effective_on or date.today(),
            ).where(ProjectCostCodeORM.id == cost_code_id)
        ).one_or_none()
        return (
            FinanceLookupOptionFact(
                id=str(row.id), label=f"{row.code} - {row.name}"
            )
            if row is not None
            else None
        )

    def get_manual_actual_defaults(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
    ) -> ManualActualDefaultsFacts | None:
        row = self._session.execute(
            select(
                ProjectFinancialProfileORM.project_id,
                ProjectFinancialProfileORM.currency_code,
            ).where(
                ProjectFinancialProfileORM.tenant_id == tenant_id,
                ProjectFinancialProfileORM.organization_id == organization_id,
                ProjectFinancialProfileORM.project_id == project_id,
                ProjectFinancialProfileORM.status == "active",
            )
        ).one_or_none()
        return (
            ManualActualDefaultsFacts(
                project_id=str(row.project_id), currency_code=str(row.currency_code)
            )
            if row is not None
            else None
        )

    @staticmethod
    def _cost_code_statement(
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        effective_on: date,
    ):
        restricted_code_exists = exists(
            select(ProjectCostCodeRestrictionORM.id).where(
                ProjectCostCodeRestrictionORM.tenant_id == tenant_id,
                ProjectCostCodeRestrictionORM.organization_id == organization_id,
                ProjectCostCodeRestrictionORM.project_id == project_id,
                ProjectCostCodeRestrictionORM.cost_code_id == ProjectCostCodeORM.id,
            )
        )
        return (
            select(ProjectCostCodeORM.id, ProjectCostCodeORM.code, ProjectCostCodeORM.name)
            .select_from(ProjectCostCodeORM)
            .join(
                ProjectFinancialProfileORM,
                and_(
                    ProjectFinancialProfileORM.tenant_id == ProjectCostCodeORM.tenant_id,
                    ProjectFinancialProfileORM.organization_id
                    == ProjectCostCodeORM.organization_id,
                    ProjectFinancialProfileORM.project_id == project_id,
                    ProjectFinancialProfileORM.status == "active",
                ),
            )
            .where(
                ProjectCostCodeORM.tenant_id == tenant_id,
                ProjectCostCodeORM.organization_id == organization_id,
                ProjectCostCodeORM.is_active.is_(True),
                or_(
                    ProjectCostCodeORM.effective_from.is_(None),
                    ProjectCostCodeORM.effective_from <= effective_on,
                ),
                or_(
                    ProjectCostCodeORM.effective_to.is_(None),
                    ProjectCostCodeORM.effective_to >= effective_on,
                ),
                or_(
                    ProjectFinancialProfileORM.cost_code_policy != "restricted",
                    restricted_code_exists,
                ),
            )
        )


def _window(page: int, page_size: int, total: int) -> tuple[int, int, int]:
    last_page = max(1, (total + page_size - 1) // page_size)
    normalized_page = min(page, last_page)
    return normalized_page, page_size, (normalized_page - 1) * page_size


def _empty_page(page: int, page_size: int) -> FinanceLookupPageFacts:
    return FinanceLookupPageFacts(items=(), total=0, page=page, page_size=page_size)


def _project_label(project_code: str | None, name: str) -> str:
    return f"{project_code} - {name}" if project_code else str(name)


def _task_label(row) -> str:
    reference = row.wbs_code or row.task_code or ""
    return f"{reference} - {row.name}" if reference else str(row.name)


__all__ = ["SqlAlchemyFinanceLookupReader"]
