from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import require_any_permission

if TYPE_CHECKING:
    from .department_service import DepartmentService


def require_department_read_access(service: DepartmentService, operation_label: str) -> None:
    require_any_permission(
        service._user_session,
        ("settings.manage", "department.read"),
        operation_label=operation_label,
    )


__all__ = ["require_department_read_access"]
