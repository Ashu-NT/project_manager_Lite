from __future__ import annotations

from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.modules import SupportsModuleEntitlements, require_module_enabled


def enforce_runtime_access(
    *,
    module_catalog_service: SupportsModuleEntitlements | None,
    user_session: UserSessionContext | None,
    module_code: str,
    permission_code: str,
    operation_label: str,
) -> None:
    normalized_module_code = str(module_code or "").strip()
    normalized_permission_code = str(permission_code or "").strip()
    if module_catalog_service is not None and normalized_module_code:
        require_module_enabled(
            module_catalog_service,
            normalized_module_code,
            operation_label=operation_label,
        )
    if user_session is not None and normalized_permission_code:
        require_permission(
            user_session,
            normalized_permission_code,
            operation_label=operation_label,
        )


__all__ = ["enforce_runtime_access"]
