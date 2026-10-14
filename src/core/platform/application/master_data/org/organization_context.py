from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.common.exceptions import BusinessRuleError

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth.session import UserSessionContext


def require_current_tenant_id(
    user_session: UserSessionContext | None, *, operation_label: str
) -> str:
    if user_session is None:
        raise BusinessRuleError(
            f"Tenant context is required to {operation_label}.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    tenant_id = str(user_session.active_tenant_id() or "").strip()
    if not tenant_id:
        raise BusinessRuleError(
            f"Tenant context is required to {operation_label}.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    return tenant_id


__all__ = ["require_current_tenant_id"]
