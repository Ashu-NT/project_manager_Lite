from __future__ import annotations


def employee_context(employee) -> str:
    parts = [
        str(getattr(employee, "department", "") or "").strip(),
        str(getattr(employee, "site_name", "") or "").strip(),
    ]
    values = [part for part in parts if part]
    return " | ".join(values) if values else "-"


def employee_contact(employee) -> str:
    return (
        getattr(employee, "email", None)
        or getattr(employee, "phone", None)
        or ""
    ).strip()


def employee_option_label(employee) -> str:
    label = (
        f"{str(getattr(employee, 'employee_code', '') or '').strip()} - "
        f"{str(getattr(employee, 'full_name', '') or '').strip()}"
    )
    context = employee_context(employee)
    if context != "-":
        label += f" [{context}]"
    if not bool(getattr(employee, "is_active", True)):
        label += " (Inactive)"
    return label


__all__ = ["employee_contact", "employee_context", "employee_option_label"]
