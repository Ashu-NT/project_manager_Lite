from __future__ import annotations

from datetime import date

from decimal import Decimal

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.projects import (
    ProjectCatalogReadItem,
    ProjectCatalogReadPage,
    ProjectCatalogSummary,
    ProjectActivityFact,
    ProjectActivityPage,
    ProjectResourceDetailFact,
    ProjectResourceDetailPage,
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
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskAssignmentORM
from src.core.platform.infrastructure.persistence.orm.history.activity.activity import ActivityEntryORM
from src.core.platform.infrastructure.persistence.orm.time_management.time.time import TimeEntryORM
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

    def read_resources_page(
        self, *, tenant_id: str, organization_id: str, project_id: str,
        search_text: str, active: bool | None, page: int, page_size: int,
        sort: ReadSort,
    ) -> ProjectResourceDetailPage:
        time_actuals = (
            select(
                TimeEntryORM.assignment_id.label("assignment_id"),
                func.count(TimeEntryORM.id).label("entry_count"),
                func.coalesce(func.sum(TimeEntryORM.hours), 0).label("hours"),
            )
            .where(
                TimeEntryORM.tenant_id == tenant_id,
                TimeEntryORM.organization_id == organization_id,
                TimeEntryORM.assignment_id.is_not(None),
            )
            .group_by(TimeEntryORM.assignment_id)
            .subquery("project_resource_time_actuals")
        )
        assignment_actual = case(
            (func.coalesce(time_actuals.c.entry_count, 0) > 0, time_actuals.c.hours),
            else_=TaskAssignmentORM.hours_logged,
        )
        usage = (
            select(
                TaskAssignmentORM.project_resource_id.label("project_resource_id"),
                func.coalesce(func.sum(TaskAssignmentORM.allocated_planned_hours), 0).label("allocated"),
                func.coalesce(func.sum(assignment_actual), 0).label("actual"),
            )
            .outerjoin(time_actuals, time_actuals.c.assignment_id == TaskAssignmentORM.id)
            .where(TaskAssignmentORM.project_resource_id.is_not(None))
            .group_by(TaskAssignmentORM.project_resource_id)
            .subquery("project_resource_usage")
        )
        filters = [
            ProjectResourceORM.project_id == project_id,
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
            ResourceORM.tenant_id == tenant_id,
            ResourceORM.organization_id == organization_id,
        ]
        if active is not None:
            filters.append(ProjectResourceORM.is_active.is_(active))
        normalized_search = str(search_text or "").strip()
        if normalized_search:
            pattern = _contains_pattern(normalized_search)
            filters.append(or_(
                func.lower(ResourceORM.name).like(pattern, escape="\\"),
                func.lower(func.coalesce(ResourceORM.resource_code, "")).like(pattern, escape="\\"),
                func.lower(func.coalesce(ResourceORM.role, "")).like(pattern, escape="\\"),
            ))
        from_clause = (
            ProjectResourceORM.__table__
            .join(ProjectORM, ProjectORM.id == ProjectResourceORM.project_id)
            .join(ResourceORM, ResourceORM.id == ProjectResourceORM.resource_id)
            .outerjoin(usage, usage.c.project_resource_id == ProjectResourceORM.id)
        )
        total = int(self._session.scalar(
            select(func.count(ProjectResourceORM.id)).select_from(from_clause).where(*filters)
        ) or 0)
        allocated = func.coalesce(usage.c.allocated, 0)
        actual = func.coalesce(usage.c.actual, 0)
        sort_expressions = {
            "resourceName": (func.lower(ResourceORM.name),),
            "resourceCode": (func.lower(func.coalesce(ResourceORM.resource_code, "")),),
            "role": (func.lower(func.coalesce(ResourceORM.role, "")),),
            "plannedHours": (ProjectResourceORM.planned_hours,),
            "allocatedHours": (allocated,), "actualHours": (actual,),
            "remainingHours": (ProjectResourceORM.planned_hours - actual,),
        }
        rows = self._session.execute(
            select(
                ProjectResourceORM.id, ResourceORM.id, ResourceORM.resource_code,
                ResourceORM.name, ResourceORM.role, ProjectResourceORM.planned_hours,
                allocated, actual, ProjectResourceORM.is_active, ProjectResourceORM.version,
            ).select_from(from_clause).where(*filters).order_by(*stable_order_by(
                sort=sort, expressions=sort_expressions, default_key="resourceName",
                tie_breakers=(ProjectResourceORM.id,),
            )).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return ProjectResourceDetailPage(
            items=tuple(ProjectResourceDetailFact(
                project_resource_id=str(row[0]), resource_id=str(row[1]),
                resource_code=str(row[2] or ""), resource_name=str(row[3] or ""),
                role=str(row[4] or ""), planned_hours=Decimal(str(row[5] or 0)),
                allocated_hours=Decimal(str(row[6] or 0)), actual_hours=Decimal(str(row[7] or 0)),
                remaining_hours=Decimal(str(row[5] or 0)) - Decimal(str(row[7] or 0)),
                is_active=bool(row[8]), version=int(row[9] or 1),
            ) for row in rows), filtered_total=total, page=page, page_size=page_size, sort=sort,
        )

    def read_activity_page(
        self, *, tenant_id: str, organization_id: str, project_id: str,
        search_text: str, category: str, page: int, page_size: int,
    ) -> ProjectActivityPage:
        primary = and_(ActivityEntryORM.entity_type == "project", ActivityEntryORM.entity_id == project_id)
        resources = and_(ActivityEntryORM.entity_type == "project_resource", ActivityEntryORM.parent_entity_id == project_id)
        filters = [
            ActivityEntryORM.tenant_id == tenant_id,
            ActivityEntryORM.organization_id == organization_id,
            ActivityEntryORM.module == "project_management",
            or_(primary, resources),
        ]
        normalized_category = str(category or "all").lower()
        if normalized_category == "project": filters.append(primary)
        elif normalized_category == "resources": filters.append(resources)
        normalized_search = str(search_text or "").strip()
        if normalized_search:
            pattern = _contains_pattern(normalized_search)
            filters.append(or_(
                func.lower(ActivityEntryORM.action).like(pattern, escape="\\"),
                func.lower(func.coalesce(ActivityEntryORM.human_message, "")).like(pattern, escape="\\"),
            ))
        total = int(self._session.scalar(select(func.count(ActivityEntryORM.id)).where(*filters)) or 0)
        rows = self._session.execute(select(
            ActivityEntryORM.id, ActivityEntryORM.timestamp, ActivityEntryORM.actor_id,
            ActivityEntryORM.action, ActivityEntryORM.entity_type,
            ActivityEntryORM.human_message, ActivityEntryORM.details,
        ).where(*filters).order_by(ActivityEntryORM.timestamp.desc(), ActivityEntryORM.id.desc())
          .offset((page - 1) * page_size).limit(page_size)).all()
        return ProjectActivityPage(items=tuple(ProjectActivityFact(
            activity_id=str(r[0]), occurred_at=r[1], actor_id=str(r[2]) if r[2] else None,
            action=str(r[3] or "activity"), entity_type=str(r[4] or "project"),
            summary=str(r[5] or r[3] or "Activity recorded"), details=dict(r[6] or {}),
        ) for r in rows), filtered_total=total, page=page, page_size=page_size,
                         sort=ReadSort.normalize(key="occurredAt", direction="desc", allowed_keys={"occurredAt"}, default_key="occurredAt"))

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
