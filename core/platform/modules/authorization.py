from __future__ import annotations

from core.platform.common.exceptions import BusinessRuleError
from core.platform.modules.contracts import SupportsModuleEntitlements


def require_module_enabled(
    module_catalog_service: SupportsModuleEntitlements | None,
    module_code: str,
    *,
    operation_label: str | None = None,
) -> None:
    if module_catalog_service is None:
        return
    entitlement = module_catalog_service.get_entitlement(module_code)
    if entitlement is None:
        return
    if entitlement.enabled:
        return
    label = entitlement.label or module_code.replace("_", " ").title()
    operation = (operation_label or "access this feature").strip()
    raise BusinessRuleError(
        f"{label} is not enabled for this installation, so you cannot {operation}.",
        code="MODULE_DISABLED",
    )


__all__ = ["require_module_enabled"]
