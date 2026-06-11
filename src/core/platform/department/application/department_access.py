from __future__ import annotations

from src.core.platform.auth.authorization import require_any_permission


def require_department_read_access(service, operation_label: str) -> None:
    require_any_permission(
        service._user_session,
        ("settings.manage", "department.read"),
        operation_label=operation_label,
    )


__all__ = ["require_department_read_access"]
