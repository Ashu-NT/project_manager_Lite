from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.platform.application.master_data.employee.queries.employee_queries import (
        EmployeePage,
    )
    from src.core.platform.domain.master_data.employee import Employee

from src.core.platform.application.master_data.employee.dto.responses.employee import (
    EmployeeDto,
    EmployeePageDto,
)


def serialize_employee_page(page: EmployeePage) -> EmployeePageDto:
    return EmployeePageDto(
        items=tuple(serialize_employee(employee) for employee in page.items),
        total=page.total,
        filtered_total=page.filtered_total,
        page=page.page,
        page_size=page.page_size,
    )







def serialize_employee(employee: Employee) -> EmployeeDto:
    return EmployeeDto(
        id=employee.id,
        employee_code=employee.employee_code,
        full_name=employee.full_name,
        department_id=employee.department_id,
        department=employee.department,
        site_id=employee.site_id,
        site_name=employee.site_name,
        title=employee.title,
        employment_type=employee.employment_type.value,
        email=employee.email,
        phone=employee.phone,
        status=employee.status.value,
        is_active=employee.is_active,
        user_id=employee.user_id,
        version=employee.version,
        organization_id=employee.organization_id,
    )
