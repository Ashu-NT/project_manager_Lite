from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, aliased

from src.core.modules.project_management.contracts.reads.resources import (
    ResourceCatalogReadItem,
    ResourceCatalogReadPage,
    ResourceCatalogSummary,
    ResourceInspectorFact,
    ResourceSummaryFact,
)
from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
    ProjectResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)
from src.core.modules.project_management.infrastructure.persistence.reads.sorting import stable_order_by
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import (
    DepartmentORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM


ResourceDepartment = aliased(DepartmentORM, name="resource_department")
EmployeeDepartment = aliased(DepartmentORM, name="employee_department")
EmployeeSite = aliased(SiteORM, name="employee_site")
DepartmentSite = aliased(SiteORM, name="department_site")


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.lower()}%"


def _with_resource_context_joins(statement):
    return (
        statement.outerjoin(
            OrganizationORM,
            (OrganizationORM.id == ResourceORM.organization_id)
            & (OrganizationORM.tenant_id == ResourceORM.tenant_id),
        )
        .outerjoin(
            EmployeeORM,
            (EmployeeORM.id == ResourceORM.employee_id)
            & (EmployeeORM.tenant_id == ResourceORM.tenant_id)
            & (EmployeeORM.organization_id == ResourceORM.organization_id),
        )
        .outerjoin(
            ResourceDepartment,
            (ResourceDepartment.id == ResourceORM.department_id)
            & (ResourceDepartment.tenant_id == ResourceORM.tenant_id)
            & (ResourceDepartment.organization_id == ResourceORM.organization_id),
        )
        .outerjoin(
            EmployeeDepartment,
            (EmployeeDepartment.id == EmployeeORM.department_id)
            & (EmployeeDepartment.tenant_id == ResourceORM.tenant_id)
            & (EmployeeDepartment.organization_id == ResourceORM.organization_id),
        )
        .outerjoin(
            EmployeeSite,
            (EmployeeSite.id == EmployeeORM.site_id)
            & (EmployeeSite.tenant_id == ResourceORM.tenant_id)
            & (EmployeeSite.organization_id == ResourceORM.organization_id),
        )
        .outerjoin(
            DepartmentSite,
            (DepartmentSite.id == ResourceDepartment.site_id)
            & (DepartmentSite.tenant_id == ResourceORM.tenant_id)
            & (DepartmentSite.organization_id == ResourceORM.organization_id),
        )
    )


def _department_id_expression():
    return func.coalesce(ResourceORM.department_id, EmployeeORM.department_id)


def _department_label_expression():
    return func.coalesce(
        ResourceDepartment.name,
        EmployeeDepartment.name,
        EmployeeORM.department,
        "",
    )


def _site_id_expression():
    return func.coalesce(EmployeeORM.site_id, ResourceDepartment.site_id)


def _site_label_expression():
    return func.coalesce(EmployeeSite.name, DepartmentSite.name, EmployeeORM.site_name, "")


class SqlAlchemyResourceCatalogReader:
    """Bounded scalar projections for the Resource catalog and detail foundation."""

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
            filtered.append(
                or_(
                    func.lower(func.coalesce(ResourceORM.resource_code, "")).like(
                        pattern, escape="\\"
                    ),
                    func.lower(ResourceORM.name).like(pattern, escape="\\"),
                    func.lower(func.coalesce(ResourceORM.role, "")).like(
                        pattern, escape="\\"
                    ),
                )
            )

        filtered_total = int(
            self._session.scalar(select(func.count(ResourceORM.id)).where(*filtered)) or 0
        )
        rows_stmt = _with_resource_context_joins(
            select(
                ResourceORM.id,
                ResourceORM.resource_code,
                ResourceORM.name,
                ResourceORM.role,
                ResourceORM.worker_type,
                ResourceORM.cost_type,
                ResourceORM.is_active,
                ResourceORM.capacity_percent,
                ResourceORM.organization_id,
                OrganizationORM.display_name,
                _department_id_expression(),
                _department_label_expression(),
                _site_id_expression(),
                _site_label_expression(),
                ResourceORM.employee_id,
                EmployeeORM.full_name,
                EmployeeORM.title,
                ResourceORM.version,
            ).select_from(ResourceORM)
        )
        sort_expressions = {
            "title": (func.lower(ResourceORM.name),),
            "resourceCode": (func.lower(func.coalesce(ResourceORM.resource_code, "")),),
            "statusLabel": (ResourceORM.is_active,),
            "department": (func.lower(_department_label_expression()),),
            "site": (func.lower(_site_label_expression()),),
            "role": (func.lower(func.coalesce(ResourceORM.role, "")),),
            "workerTypeLabel": (ResourceORM.worker_type,),
            "capacityPercent": (ResourceORM.capacity_percent,),
        }
        order_by = (
            (ResourceORM.is_active.desc(), func.lower(ResourceORM.name).asc(), ResourceORM.id.asc())
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
                    resource_id=str(row[0]),
                    code=str(row[1] or ""),
                    name=str(row[2] or ""),
                    role=str(row[3] or ""),
                    worker_type=str(getattr(row[4], "value", row[4]) or ""),
                    cost_type=str(getattr(row[5], "value", row[5]) or ""),
                    is_active=bool(row[6]),
                    capacity_percent=float(row[7] or 0.0),
                    organization_id=str(row[8]),
                    organization_label=str(row[9] or ""),
                    department_id=str(row[10]) if row[10] else None,
                    department_label=str(row[11] or ""),
                    site_id=str(row[12]) if row[12] else None,
                    site_label=str(row[13] or ""),
                    employee_id=str(row[14]) if row[14] else None,
                    employee_name=str(row[15] or ""),
                    employee_title=str(row[16] or ""),
                    version=int(row[17] or 1),
                )
                for row in rows
            ),
            filtered_total=filtered_total,
            page=page,
            page_size=page_size,
            summary=summary,
            sort=sort,
        )

    def read_inspector(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
    ) -> ResourceInspectorFact | None:
        project_count = (
            select(func.count(ProjectResourceORM.id))
            .join(ProjectORM, ProjectORM.id == ProjectResourceORM.project_id)
            .where(
                ProjectResourceORM.resource_id == ResourceORM.id,
                ProjectResourceORM.is_active.is_(True),
                ProjectORM.tenant_id == tenant_id,
                ProjectORM.organization_id == organization_id,
            )
            .correlate(ResourceORM)
            .scalar_subquery()
        )
        assignment_count = (
            select(func.count(TaskAssignmentORM.id))
            .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(
                TaskAssignmentORM.resource_id == ResourceORM.id,
                ProjectORM.tenant_id == tenant_id,
                ProjectORM.organization_id == organization_id,
            )
            .correlate(ResourceORM)
            .scalar_subquery()
        )
        statement = _with_resource_context_joins(
            select(
                ResourceORM.id,
                ResourceORM.resource_code,
                ResourceORM.name,
                ResourceORM.role,
                ResourceORM.worker_type,
                ResourceORM.is_active,
                ResourceORM.capacity_percent,
                ResourceORM.organization_id,
                OrganizationORM.display_name,
                _department_id_expression(),
                _department_label_expression(),
                _site_id_expression(),
                _site_label_expression(),
                ResourceORM.employee_id,
                EmployeeORM.full_name,
                project_count,
                assignment_count,
                ResourceORM.version,
            ).select_from(ResourceORM)
        ).where(
            ResourceORM.id == resource_id,
            ResourceORM.tenant_id == tenant_id,
            ResourceORM.organization_id == organization_id,
        )
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        return ResourceInspectorFact(
            resource_id=str(row[0]),
            code=str(row[1] or ""),
            name=str(row[2] or ""),
            role=str(row[3] or ""),
            worker_type=str(getattr(row[4], "value", row[4]) or ""),
            is_active=bool(row[5]),
            capacity_percent=float(row[6] or 0.0),
            organization_id=str(row[7]),
            organization_label=str(row[8] or ""),
            department_id=str(row[9]) if row[9] else None,
            department_label=str(row[10] or ""),
            site_id=str(row[11]) if row[11] else None,
            site_label=str(row[12] or ""),
            employee_id=str(row[13]) if row[13] else None,
            employee_name=str(row[14] or ""),
            project_count=int(row[15] or 0),
            assignment_count=int(row[16] or 0),
            version=int(row[17] or 1),
        )

    def read_summary(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
    ) -> ResourceSummaryFact | None:
        statement = _with_resource_context_joins(
            select(
                ResourceORM.id,
                ResourceORM.resource_code,
                ResourceORM.name,
                ResourceORM.role,
                ResourceORM.worker_type,
                ResourceORM.cost_type,
                ResourceORM.hourly_rate,
                ResourceORM.currency_code,
                ResourceORM.is_active,
                ResourceORM.capacity_percent,
                ResourceORM.address,
                ResourceORM.contact,
                ResourceORM.organization_id,
                OrganizationORM.display_name,
                _department_id_expression(),
                _department_label_expression(),
                _site_id_expression(),
                _site_label_expression(),
                ResourceORM.employee_id,
                EmployeeORM.full_name,
                EmployeeORM.title,
                ResourceORM.version,
            ).select_from(ResourceORM)
        ).where(
            ResourceORM.id == resource_id,
            ResourceORM.tenant_id == tenant_id,
            ResourceORM.organization_id == organization_id,
        )
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        return ResourceSummaryFact(
            resource_id=str(row[0]),
            code=str(row[1] or ""),
            name=str(row[2] or ""),
            role=str(row[3] or ""),
            worker_type=str(getattr(row[4], "value", row[4]) or ""),
            cost_type=str(getattr(row[5], "value", row[5]) or ""),
            hourly_rate=Decimal(str(row[6] or 0)),
            currency_code=str(row[7]).upper() if row[7] else None,
            is_active=bool(row[8]),
            capacity_percent=float(row[9] or 0.0),
            address=str(row[10] or ""),
            contact=str(row[11] or ""),
            organization_id=str(row[12]),
            organization_label=str(row[13] or ""),
            department_id=str(row[14]) if row[14] else None,
            department_label=str(row[15] or ""),
            site_id=str(row[16]) if row[16] else None,
            site_label=str(row[17] or ""),
            employee_id=str(row[18]) if row[18] else None,
            employee_name=str(row[19] or ""),
            employee_title=str(row[20] or ""),
            version=int(row[21] or 1),
        )


__all__ = ["SqlAlchemyResourceCatalogReader"]
