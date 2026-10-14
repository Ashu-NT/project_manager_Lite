"""Shared reporting read-access policy (report.view / finance.* tiers)."""

from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class ReportingAccessPolicy:
    """One authorization policy shared by every report builder."""

    def __init__(self, user_session=None) -> None:
        self._user_session = user_session

    @property
    def user_session(self):
        return self._user_session

    def require_view(self, operation_label: str, *, project_id: str | None = None) -> None:
        require_permission(self._user_session, "report.view", operation_label=operation_label)
        if project_id is not None:
            require_project_permission(
                self._user_session,
                project_id,
                "report.view",
                operation_label=operation_label,
            )

    def require_finance_view(self, operation_label: str, *, project_id: str) -> None:
        """Gate for reports whose entire result is Project Finance authority
        data (EVM, cost breakdown, cost source breakdown, labor cost)."""
        require_permission(self._user_session, "finance.read", operation_label=operation_label)
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label=operation_label,
        )

    def require_finance_sensitive_view(self, operation_label: str, *, project_id: str) -> None:
        """Gate for reports exposing individually-identified resource labor
        rates/costs -- the ``finance.read_sensitive`` tier."""
        require_permission(
            self._user_session, "finance.read_sensitive", operation_label=operation_label
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read_sensitive",
            operation_label=operation_label,
        )

    def has_finance_view(self, project_id: str) -> bool:
        """Non-raising finance.read check for mixed financial/non-financial
        reports that must redact rather than deny outright."""
        return bool(
            self._user_session is not None
            and self._user_session.has_project_permission(project_id, "finance.read")
        )

    def has_profitability_view(self, project_id: str) -> bool:
        """Redact commercial margin independently of ordinary billing progress."""
        return bool(
            self._user_session is not None
            and self._user_session.has_project_permission(
                project_id, "finance.read_profitability"
            )
        )


__all__ = ["ReportingAccessPolicy"]
