"""Calendar shift pattern operations."""

from __future__ import annotations

from typing import Any

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    NotFoundError,
)
from src.core.platform.contract.repositories.time_management.calendar.contracts import (
    ShiftPatternRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    ShiftPattern,
    ShiftPatternDay,
)


class ShiftPatternQueryHandler:
    """Read-only lookups for shift pattern."""

    def __init__(
        self,
        *,
        pattern_repo: ShiftPatternRepository,
        user_session: Any = None,
        tenant_context_service: TenantContextService | None = None,
    ) -> None:
        self._pattern_repo = pattern_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def _active_org_id(self) -> str:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_organization_id(
            operation_label="shift pattern access",
        )

    def list_shift_patterns(
        self, *, active_only: bool | None = None
    ) -> list[ShiftPattern]:
        require_permission(
            self._user_session, "calendar.read", operation_label="list shift patterns"
        )
        org_id = self._active_org_id()
        return self._pattern_repo.list_for_organization(org_id, active_only=active_only)

    def get_shift_pattern(self, pattern_id: str) -> ShiftPattern:
        require_permission(
            self._user_session, "calendar.read", operation_label="get shift pattern"
        )
        return self._require_pattern_in_active_organization(pattern_id)

    def list_days(self, pattern_id: str) -> list[ShiftPatternDay]:
        require_permission(
            self._user_session,
            "calendar.read",
            operation_label="list shift pattern days",
        )
        self._require_pattern_in_active_organization(pattern_id)
        return self._pattern_repo.list_days(pattern_id)

    def _require_pattern_in_active_organization(self, pattern_id: str) -> ShiftPattern:
        org_id = self._active_org_id()
        pattern = self._pattern_repo.get(pattern_id)
        if pattern is None or pattern.organization_id != org_id:
            raise NotFoundError(f"Shift pattern '{pattern_id}' not found.")
        return pattern


__all__ = ["ShiftPatternQueryHandler"]
