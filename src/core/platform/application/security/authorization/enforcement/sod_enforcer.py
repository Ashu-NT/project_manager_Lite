from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    record_authorization_denial,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.security.authorization.enforcement.sod import (
    SeparationOfDutiesPolicy,
)
from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_ROLE_PERMISSIONS,
)

if TYPE_CHECKING:
    from src.core.platform.application.security.auth.queries.auth_queries import (
        AuthQueryHandler,
    )


class SeparationOfDutiesEnforcer:
    """Rejects role combinations whose default permissions conflict under the SoD policy."""

    def __init__(
        self,
        *,
        auth_queries: AuthQueryHandler,
        sod_policy: SeparationOfDutiesPolicy,
        user_session: UserSessionContext | None,
    ) -> None:
        self._auth_queries = auth_queries
        self._sod_policy = sod_policy
        self._user_session = user_session

    def enforce(self, role_names: Iterable[str]) -> None:
        normalized = tuple(
            str(r or "").strip().lower()
            for r in role_names
            if str(r or "").strip()
        )
        if "admin" in normalized:
            return
        permission_codes: set[str] = set()
        for role_name in normalized:
            role = self._auth_queries.require_role_by_name(role_name)
            permission_codes.update(DEFAULT_ROLE_PERMISSIONS.get(role.name, set()))
        conflicts = self._sod_policy.find_conflicts(permission_codes)
        if conflicts:
            record_authorization_denial(
                self._user_session,
                operation_label="validate role separation of duties",
                reason_code="ROLE_CONFLICT",
                required_permissions=permission_codes,
                target_scope_type="role",
                operation="authorization.sod.denied",
            )
            raise ValidationError(
                f"Role assignment violates separation of duties. {conflicts[0]}",
                code="ROLE_CONFLICT",
            )


__all__ = ["SeparationOfDutiesEnforcer"]
