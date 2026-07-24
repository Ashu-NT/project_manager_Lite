from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.formatters.employee_formatter import (
    employee_contact,
    employee_context,
    employee_option_label,
)
from src.core.modules.project_management.api.desktop.resources.models.options import (
    ResourceEmployeeOptionDescriptor,
)


def build_employee_options(
    employee_service: object | None = None,
) -> tuple[ResourceEmployeeOptionDescriptor, ...]:
    if employee_service is None:
        return ()
    try:
        employees = sorted(
            employee_service.list_employees(active_only=None),
            key=lambda employee: (
                not bool(getattr(employee, "is_active", True)),
                str(getattr(employee, "full_name", "") or "").casefold(),
                str(getattr(employee, "employee_code", "") or "").casefold(),
            ),
        )
    except Exception:
        return ()
    return tuple(
        ResourceEmployeeOptionDescriptor(
            value=employee.id,
            label=employee_option_label(employee),
            name=employee.full_name,
            title=(employee.title or "").strip(),
            contact=employee_contact(employee),
            context=employee_context(employee),
            department=(getattr(employee, "department", "") or "").strip(),
            site=(getattr(employee, "site_name", "") or "").strip(),
            is_active=bool(getattr(employee, "is_active", True)),
        )
        for employee in employees
        if getattr(employee, "id", None)
    )


def build_employee_lookup(
    employee_service: object | None = None,
) -> dict[str, ResourceEmployeeOptionDescriptor]:
    return {
        option.value: option
        for option in build_employee_options(employee_service)
    }


__all__ = ["build_employee_lookup", "build_employee_options"]
