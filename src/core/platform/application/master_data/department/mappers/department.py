from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.platform.application.master_data.department.queries.department_queries import (
        DepartmentPage,
    )

from src.core.platform.application.master_data.department.dto.responses.department import (
    DepartmentDto,
    DepartmentPageDto,
)
from src.core.platform.domain.master_data.department import Department


def serialize_department_page(page: DepartmentPage) -> DepartmentPageDto:
    return DepartmentPageDto(
        items=tuple(serialize_department(department) for department in page.items),
        total=page.total,
        filtered_total=page.filtered_total,
        page=page.page,
        page_size=page.page_size,
    )




def serialize_department(department: Department) -> DepartmentDto:
    return DepartmentDto(
        id=department.id,
        organization_id=department.organization_id,
        department_code=department.department_code,
        name=department.name,
        description=department.description,
        site_id=department.site_id,
        parent_department_id=department.parent_department_id,
        department_type=department.department_type,
        cost_center_code=department.cost_center_code,
        head_of_department_employee_id=department.head_of_department_employee_id,
        is_active=department.is_active,
        notes=department.notes,
        version=department.version,
        created_at=department.created_at,
        updated_at=department.updated_at,
    )
