from __future__ import annotations

from src.core.platform.org import EmployeeService


def format_employee_context(*, department: str = "", site_name: str = "") -> str:
    parts = [str(department or "").strip(), str(site_name or "").strip()]
    values = [part for part in parts if part]
    return " | ".join(values) if values else "-"


def format_employee_context_from_record(employee) -> str:
    return format_employee_context(
        department=getattr(employee, "department", ""),
        site_name=getattr(employee, "site_name", ""),
    )


def build_employee_context_map(employee_service: EmployeeService | None) -> dict[str, str]:
    if employee_service is None:
        return {}
    employees = employee_service.list_employees()
    return {
        str(employee.id): format_employee_context_from_record(employee)
        for employee in employees
        if getattr(employee, "id", None)
    }


def employee_option_label(employee) -> str:
    label = f"{employee.employee_code} - {employee.full_name}"
    context = format_employee_context_from_record(employee)
    if context != "-":
        label += f" [{context}]"
    if not getattr(employee, "is_active", True):
        label += " (Inactive)"
    return label


__all__ = [
    "build_employee_context_map",
    "employee_option_label",
    "format_employee_context",
    "format_employee_context_from_record",
]
