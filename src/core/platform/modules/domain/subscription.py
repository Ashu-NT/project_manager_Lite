from __future__ import annotations

from pydantic import field_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import validated_dataclass
from src.core.platform.modules.domain.defaults import MODULE_LIFECYCLE_INACTIVE, normalize_lifecycle_status
from src.core.platform.modules.domain.module_codes import normalize_module_code


def normalize_module_entitlement_record_code(value: object) -> str:
    normalized = normalize_module_code(str(value or ""))
    if not normalized:
        raise ValidationError(
            "Module code is required.",
            code="MODULE_CODE_REQUIRED",
        )
    return normalized


def normalize_module_entitlement_record_lifecycle_status(value: object) -> str:
    raw = str(value or "").strip().lower() or MODULE_LIFECYCLE_INACTIVE
    return normalize_lifecycle_status(raw)


@validated_dataclass(frozen=True)
class ModuleEntitlementRecord:
    module_code: str
    licensed: bool
    enabled: bool
    lifecycle_status: str = "inactive"

    @field_validator("module_code", mode="before")
    @classmethod
    def _validate_module_code(cls, value: object) -> str:
        return normalize_module_entitlement_record_code(value)

    @field_validator("lifecycle_status", mode="before")
    @classmethod
    def _validate_lifecycle_status(cls, value: object) -> str:
        return normalize_module_entitlement_record_lifecycle_status(value)


__all__ = [
    "ModuleEntitlementRecord",
    "normalize_module_entitlement_record_code",
    "normalize_module_entitlement_record_lifecycle_status",
]
