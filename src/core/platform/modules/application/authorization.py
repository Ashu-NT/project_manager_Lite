from __future__ import annotations

from core.platform.common.exceptions import BusinessRuleError
from src.core.platform.modules.contracts import SupportsModuleEntitlements


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
    if entitlement.runtime_enabled:
        return
    label = entitlement.label or module_code.replace("_", " ").title()
    operation = (operation_label or "access this feature").strip()
    lifecycle_status = getattr(entitlement, "lifecycle_status", "inactive")
    if lifecycle_status == "suspended":
        message = f"{label} is suspended for this organization, so you cannot {operation}."
    elif lifecycle_status == "expired":
        message = f"{label} has expired for this organization, so you cannot {operation}."
    elif lifecycle_status == "trial":
        message = f"{label} is in trial but not enabled for runtime use, so you cannot {operation}."
    else:
        message = f"{label} is not enabled for this installation, so you cannot {operation}."
    raise BusinessRuleError(
        message,
        code="MODULE_DISABLED",
    )


__all__ = ["require_module_enabled"]
