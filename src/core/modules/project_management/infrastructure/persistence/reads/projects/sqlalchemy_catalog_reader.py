from __future__ import annotations

from datetime import date

from sqlalchemy import func, literal, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.projects import (
    ProjectCatalogReadItem,
    ProjectCatalogReadPage,
    ProjectCatalogSummary,
)
from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.infrastructure.persistence.reads.sorting import (
    stable_order_by,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.infrastructure.persistence.mappers.project import (
    project_from_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.budget import (
    BudgetLineORM,
    ProjectBudgetORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.financial_configuration import (
    ProjectFinancialProfileORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM
from src.core.platform.infrastructure.persistence.orm.master_data.party.party import PartyORM


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.lower()}%"


class SqlAlchemyProjectCatalogReader:
    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        finance_allowed_project_ids: tuple[str, ...] | None,
        search_text: str,
        status: ProjectStatus | None,
        project_name: str | None = None,
        client_name: str | None = None,
        site_id: str | None = None,
        department_id: str | None = None,
        manager_user_id: str | None = None,
        start_date_from: date | None = None,
        start_date_to: date | None = None,
        end_date_from: date | None = None,
        end_date_to: date | None = None,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> ProjectCatalogReadPage:
        if allowed_project_ids == ():
            return ProjectCatalogReadPage(page=page, page_size=page_size)

        scope_filters = (
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
        )
        if allowed_project_ids is not None:
            scope_filters = (*scope_filters, ProjectORM.id.in_(allowed_project_ids))

        status_rows = self._session.execute(
            select(ProjectORM.status, func.count(ProjectORM.id))
            .where(*scope_filters)
            .group_by(ProjectORM.status)
        ).all()
        status_counts = {status_value: int(count or 0) for status_value, count in status_rows}
        summary = ProjectCatalogSummary(
            total=sum(status_counts.values()),
            active=status_counts.get(ProjectStatus.ACTIVE, 0),
            planned=status_counts.get(ProjectStatus.PLANNED, 0),
            on_hold=status_counts.get(ProjectStatus.ON_HOLD, 0),
            completed=status_counts.get(ProjectStatus.COMPLETED, 0),
        )

        filtered = list(scope_filters)
        if status is not None:
            filtered.append(ProjectORM.status == status)
        if site_id:
            filtered.append(ProjectORM.site_id == site_id)
        if department_id:
            filtered.append(ProjectORM.department_id == department_id)
        if manager_user_id:
            filtered.append(ProjectORM.manager_user_id == manager_user_id)
        normalized_project_name = str(project_name or "").strip()
        if normalized_project_name:
            filtered.append(
                func.lower(ProjectORM.name).like(
                    _contains_pattern(normalized_project_name), escape="\\"
                )
            )
        normalized_client_name = str(client_name or "").strip()
        if normalized_client_name:
            # Filters the raw stored `client_name` free-text field -- the
            # resolved-via-party `client_label` used for display would need
            # the PartyORM outerjoin also present in the bare filtered_total
            # count query below, which it deliberately is not (to avoid an
            # unjoined-table cross-join inflating that count).
            filtered.append(
                func.lower(func.coalesce(ProjectORM.client_name, "")).like(
                    _contains_pattern(normalized_client_name), escape="\\"
                )
            )
        if start_date_from is not None:
            filtered.append(ProjectORM.start_date >= start_date_from)
        if start_date_to is not None:
            filtered.append(ProjectORM.start_date <= start_date_to)
        if end_date_from is not None:
            filtered.append(ProjectORM.end_date >= end_date_from)
        if end_date_to is not None:
            filtered.append(ProjectORM.end_date <= end_date_to)
        normalized_search = str(search_text or "").strip()
        if normalized_search:
            pattern = _contains_pattern(normalized_search)
            filtered.append(
                or_(
                    func.lower(ProjectORM.name).like(pattern, escape="\\"),
                    func.lower(func.coalesce(ProjectORM.client_name, "")).like(pattern, escape="\\"),
                    func.lower(func.coalesce(ProjectORM.client_contact, "")).like(pattern, escape="\\"),
                    func.lower(func.coalesce(ProjectORM.description, "")).like(pattern, escape="\\"),
                )
            )

        filtered_total = int(
            self._session.scalar(select(func.count(ProjectORM.id)).where(*filtered)) or 0
        )
        approved_budget, approved_budget_currency, approved_budget_visible = (
            self._approved_budget_projections(finance_allowed_project_ids)
        )
        resolved_client_name = func.coalesce(PartyORM.party_name, ProjectORM.client_name, "")
        rows_stmt = (
            select(
                ProjectORM,
                SiteORM.name,
                ProjectFinancialProfileORM.currency_code,
                approved_budget.label("approved_budget"),
                approved_budget_currency.label("approved_budget_currency"),
                approved_budget_visible.label("approved_budget_visible"),
                resolved_client_name.label("client_label"),
            )
            .outerjoin(
                SiteORM,
                (SiteORM.id == ProjectORM.site_id)
                & (SiteORM.tenant_id == ProjectORM.tenant_id)
                & (SiteORM.organization_id == ProjectORM.organization_id),
            )
            # LEFT OUTER: a project without a finance profile must still appear in
            # the page (filtered_total above is computed without this join at all,
            # so an INNER join here would silently drop such rows while the total
            # still counted them).
            .outerjoin(
                ProjectFinancialProfileORM,
                (ProjectFinancialProfileORM.project_id == ProjectORM.id)
                & (ProjectFinancialProfileORM.tenant_id == ProjectORM.tenant_id)
                & (ProjectFinancialProfileORM.organization_id == ProjectORM.organization_id),
            )
            .outerjoin(
                PartyORM,
                (PartyORM.id == ProjectORM.client_party_id)
                & (PartyORM.organization_id == ProjectORM.organization_id),
            )
            .where(*filtered)
        )
        sort_expressions = {
            "title": (func.lower(ProjectORM.name),),
            "projectCode": (func.lower(func.coalesce(ProjectORM.project_code, "")),),
            "statusLabel": (ProjectORM.status,),
            "clientLabel": (func.lower(resolved_client_name),),
            "siteLabel": (func.lower(func.coalesce(SiteORM.name, "")),),
            "clientContact": (func.lower(func.coalesce(ProjectORM.client_contact, "")),),
            "startDateLabel": (ProjectORM.start_date,),
            "endDateLabel": (ProjectORM.end_date,),
            "approvedBudgetLabel": (approved_budget,),
        }
        rows = self._session.execute(
            rows_stmt.order_by(
                *stable_order_by(
                    sort=sort,
                    expressions=sort_expressions,
                    default_key="title",
                    tie_breakers=(ProjectORM.id,),
                )
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return ProjectCatalogReadPage(
            items=tuple(
                ProjectCatalogReadItem(
                    project=project_from_orm(project_row),
                    site_label=str(site_name or ""),
                    financial_currency_code=str(financial_currency_code or ""),
                    approved_budget=approved_budget_value,
                    approved_budget_currency=str(approved_budget_currency_value or ""),
                    approved_budget_visible=bool(approved_budget_visible_value),
                    client_label=str(client_label_value or ""),
                )
                for (
                    project_row,
                    site_name,
                    financial_currency_code,
                    approved_budget_value,
                    approved_budget_currency_value,
                    approved_budget_visible_value,
                    client_label_value,
                ) in rows
            ),
            filtered_total=filtered_total,
            page=page,
            page_size=page_size,
            summary=summary,
            sort=sort,
        )

    def read_one(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        include_approved_budget: bool,
    ) -> ProjectCatalogReadItem | None:
        approved_budget, approved_budget_currency, approved_budget_visible = (
            self._approved_budget_projections(None if include_approved_budget else ())
        )
        resolved_client_name = func.coalesce(PartyORM.party_name, ProjectORM.client_name, "")
        row = self._session.execute(
            select(
                ProjectORM,
                SiteORM.name,
                ProjectFinancialProfileORM.currency_code,
                approved_budget.label("approved_budget"),
                approved_budget_currency.label("approved_budget_currency"),
                approved_budget_visible.label("approved_budget_visible"),
                resolved_client_name.label("client_label"),
            )
            .outerjoin(
                SiteORM,
                (SiteORM.id == ProjectORM.site_id)
                & (SiteORM.tenant_id == ProjectORM.tenant_id)
                & (SiteORM.organization_id == ProjectORM.organization_id),
            )
            .outerjoin(
                ProjectFinancialProfileORM,
                (ProjectFinancialProfileORM.project_id == ProjectORM.id)
                & (ProjectFinancialProfileORM.tenant_id == ProjectORM.tenant_id)
                & (ProjectFinancialProfileORM.organization_id == ProjectORM.organization_id),
            )
            .outerjoin(
                PartyORM,
                (PartyORM.id == ProjectORM.client_party_id)
                & (PartyORM.organization_id == ProjectORM.organization_id),
            )
            .where(
                ProjectORM.tenant_id == tenant_id,
                ProjectORM.organization_id == organization_id,
                ProjectORM.id == project_id,
            )
            .limit(1)
        ).one_or_none()
        if row is None:
            return None
        (
            project_row,
            site_name,
            financial_currency_code,
            approved_budget_value,
            approved_budget_currency_value,
            approved_budget_visible_value,
            client_label_value,
        ) = row
        return ProjectCatalogReadItem(
            project=project_from_orm(project_row),
            site_label=str(site_name or ""),
            financial_currency_code=str(financial_currency_code or ""),
            approved_budget=approved_budget_value,
            approved_budget_currency=str(approved_budget_currency_value or ""),
            approved_budget_visible=bool(approved_budget_visible_value),
            client_label=str(client_label_value or ""),
        )

    @staticmethod
    def _approved_budget_projections(
        finance_allowed_project_ids: tuple[str, ...] | None,
    ):
        if finance_allowed_project_ids == ():
            return literal(None), literal(""), literal(False)

        finance_scope_filters = ()
        if finance_allowed_project_ids is not None:
            finance_scope_filters = (ProjectORM.id.in_(finance_allowed_project_ids),)

        approved_budget = (
            select(func.sum(BudgetLineORM.amount))
            .join(
                ProjectBudgetORM,
                (ProjectBudgetORM.id == BudgetLineORM.budget_id)
                & (ProjectBudgetORM.tenant_id == BudgetLineORM.tenant_id)
                & (ProjectBudgetORM.organization_id == BudgetLineORM.organization_id)
                & (ProjectBudgetORM.project_id == BudgetLineORM.project_id),
            )
            .where(
                ProjectBudgetORM.tenant_id == ProjectORM.tenant_id,
                ProjectBudgetORM.organization_id == ProjectORM.organization_id,
                ProjectBudgetORM.project_id == ProjectORM.id,
                ProjectBudgetORM.status == "approved",
                *finance_scope_filters,
            )
            .correlate(ProjectORM)
            .scalar_subquery()
        )
        approved_budget_currency = (
            select(ProjectBudgetORM.currency_code)
            .where(
                ProjectBudgetORM.tenant_id == ProjectORM.tenant_id,
                ProjectBudgetORM.organization_id == ProjectORM.organization_id,
                ProjectBudgetORM.project_id == ProjectORM.id,
                ProjectBudgetORM.status == "approved",
                *finance_scope_filters,
            )
            .correlate(ProjectORM)
            .scalar_subquery()
        )
        approved_budget_visible = (
            literal(True)
            if finance_allowed_project_ids is None
            else ProjectORM.id.in_(finance_allowed_project_ids)
        )
        return approved_budget, approved_budget_currency, approved_budget_visible


__all__ = ["SqlAlchemyProjectCatalogReader"]
