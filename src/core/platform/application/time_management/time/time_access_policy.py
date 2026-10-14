from __future__ import annotations

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.contract.interface.time_management.time.contracts import (
    WorkAllocationRecord,
    WorkOwnerRecord,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.time_management.time import TimeEntry


class PlatformTimeAccessPolicy:
    """Global time.*/task.* capability checks with no module scope model."""

    def __init__(self, *, user_session: UserSessionContext | None) -> None:
        self._user_session = user_session

    def require_read_permission(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("time.read", "task.read"),
            operation_label=operation_label,
        )

    def require_manage_permission(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("time.manage", "task.manage"),
            operation_label=operation_label,
        )

    def require_project_scope(
        self,
        *,
        work_allocation: WorkAllocationRecord | None,
        work_owner: WorkOwnerRecord | None,
        operation_label: str,
    ) -> None:
        """No project concept at the platform layer."""
        return

    def require_review_scope(self, permission_code: str, entries: list[TimeEntry]) -> None:
        """No module-owned review scope at the platform layer."""
        return


__all__ = ["PlatformTimeAccessPolicy",]
