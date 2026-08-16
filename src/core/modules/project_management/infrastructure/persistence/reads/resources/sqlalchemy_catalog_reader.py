from __future__ import annotations

from sqlalchemy import String, case, cast, func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.resources import (
    ResourceCatalogReadItem,
    ResourceCatalogReadPage,
    ResourceCatalogSummary,
)
from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.infrastructure.persistence.reads.sorting import stable_order_by
from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.infrastructure.persistence.mappers.resource import (
    resource_from_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import (
    DepartmentORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.lower()}%"


class SqlAlchemyResourceCatalogReader:
    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        search_text: str,
        active: bool | None,
        category: CostType | None,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> ResourceCatalogReadPage:
        scope_filters = (
            ResourceORM.tenant_id == tenant_id,
            ResourceORM.organization_id == organization_id,
        )
        summary_row = self._session.execute(
            select(
                func.count(ResourceORM.id),
                func.sum(case((ResourceORM.is_active.is_(True), 1), else_=0)),
                func.sum(case((ResourceORM.worker_type == WorkerType.EMPLOYEE, 1), else_=0)),
                func.sum(case((ResourceORM.worker_type == WorkerType.EXTERNAL, 1), else_=0)),
                func.avg(ResourceORM.capacity_percent),
            ).where(*scope_filters)
        ).one()
        summary = ResourceCatalogSummary(
            total=int(summary_row[0] or 0),
            active=int(summary_row[1] or 0),
            employees=int(summary_row[2] or 0),
            external=int(summary_row[3] or 0),
            average_capacity=float(summary_row[4] or 0.0),
        )

        filtered = list(scope_filters)
        if active is not None:
            filtered.append(ResourceORM.is_active.is_(active))
        if category is not None:
            filtered.append(ResourceORM.cost_type == category)
        normalized_search = str(search_text or "").strip()
        if normalized_search:
            pattern = _contains_pattern(normalized_search)
            search_columns = (
                ResourceORM.name,
                ResourceORM.role,
                ResourceORM.resource_code,
                ResourceORM.address,
                ResourceORM.contact,
                ResourceORM.currency_code,
                EmployeeORM.full_name,
                EmployeeORM.title,
                EmployeeORM.email,
                EmployeeORM.phone,
                EmployeeORM.department,
                EmployeeORM.site_name,
                DepartmentORM.name,
                SiteORM.name,
            )
            filtered.append(
                or_(
                    *(
                        func.lower(func.coalesce(column, "")).like(pattern, escape="\\")
                        for column in search_columns
                    ),
                    func.lower(cast(ResourceORM.worker_type, String)).like(pattern, escape="\\"),
                    func.lower(cast(ResourceORM.cost_type, String)).like(pattern, escape="\\"),
                )
            )

        joins = (
            (EmployeeORM, (EmployeeORM.id == ResourceORM.employee_id)
             & (EmployeeORM.tenant_id == ResourceORM.tenant_id)
             & (EmployeeORM.organization_id == ResourceORM.organization_id)),
            (DepartmentORM, (DepartmentORM.id == EmployeeORM.department_id)
             & (DepartmentORM.tenant_id == ResourceORM.tenant_id)
             & (DepartmentORM.organization_id == ResourceORM.organization_id)),
            (SiteORM, (SiteORM.id == EmployeeORM.site_id)
             & (SiteORM.tenant_id == ResourceORM.tenant_id)
             & (SiteORM.organization_id == ResourceORM.organization_id)),
        )
        count_stmt = select(func.count(ResourceORM.id)).select_from(ResourceORM)
        for target, condition in joins:
            count_stmt = count_stmt.outerjoin(target, condition)
        filtered_total = int(self._session.scalar(count_stmt.where(*filtered)) or 0)

        rows_stmt = select(
            ResourceORM,
            EmployeeORM.full_name,
            EmployeeORM.title,
            EmployeeORM.email,
            EmployeeORM.phone,
            func.coalesce(DepartmentORM.name, EmployeeORM.department, ""),
            func.coalesce(SiteORM.name, EmployeeORM.site_name, ""),
        ).select_from(ResourceORM)
        for target, condition in joins:
            rows_stmt = rows_stmt.outerjoin(target, condition)
        sort_expressions = {
            "title": (func.lower(ResourceORM.name),),
            "resourceCode": (func.lower(func.coalesce(ResourceORM.resource_code, "")),),
            "statusLabel": (ResourceORM.is_active,),
            "department": (func.lower(func.coalesce(DepartmentORM.name, EmployeeORM.department, "")),),
            "site": (func.lower(func.coalesce(SiteORM.name, EmployeeORM.site_name, "")),),
            "role": (func.lower(func.coalesce(ResourceORM.role, "")),),
            "utilizationValue": (ResourceORM.capacity_percent,),
        }
        order_by = (
            (
                ResourceORM.is_active.desc(),
                func.lower(ResourceORM.name).asc(),
                ResourceORM.id.asc(),
            )
            if sort.key == "catalog"
            else stable_order_by(
                sort=sort,
                expressions=sort_expressions,
                default_key="title",
                tie_breakers=(ResourceORM.id,),
            )
        )
        rows = self._session.execute(
            rows_stmt.where(*filtered)
            .order_by(*order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return ResourceCatalogReadPage(
            items=tuple(
                ResourceCatalogReadItem(
                    resource=resource_from_orm(row),
                    employee_name=str(employee_name or ""),
                    employee_title=str(employee_title or ""),
                    employee_contact=str(email or phone or ""),
                    department_label=str(department or ""),
                    site_label=str(site or ""),
                )
                for row, employee_name, employee_title, email, phone, department, site in rows
            ),
            filtered_total=filtered_total,
            page=page,
            page_size=page_size,
            summary=summary,
            sort=sort,
        )


__all__ = ["SqlAlchemyResourceCatalogReader"]
