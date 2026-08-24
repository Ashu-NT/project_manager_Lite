from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import field_validator

from src.core.modules.project_management.domain.enums import (
    CostType,
    ResourceKind,
    WorkerType,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


def _decimal(value: object) -> Decimal:
    try:
        resolved = Decimal(str(value if value not in (None, "") else "0"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(
            "Hourly rate must be a valid non-negative number.",
            code="RESOURCE_HOURLY_RATE_INVALID",
        ) from exc
    if not resolved.is_finite() or resolved < 0:
        raise ValidationError(
            "Hourly rate must be a valid non-negative number.",
            code="RESOURCE_HOURLY_RATE_INVALID",
        )
    return resolved


def _capacity(value: object) -> float:
    try:
        resolved = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Capacity modifier must be a valid number greater than zero.",
            code="RESOURCE_CAPACITY_INVALID",
        ) from exc
    if resolved <= 0:
        raise ValidationError(
            "Capacity modifier must be greater than zero.",
            code="RESOURCE_CAPACITY_INVALID",
        )
    return resolved


class _ResourceMasterCommandValidation:
    @field_validator("name", mode="before")
    @classmethod
    def _name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource name is required.",
            code="RESOURCE_NAME_EMPTY",
        )

    @field_validator("code", mode="before")
    @classmethod
    def _code(cls, value: object) -> str:
        return normalize_optional_text(value).upper()

    @field_validator("role", "address", "contact", mode="before")
    @classmethod
    def _text(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator(
        "currency_code",
        "employee_id",
        "department_id",
        "site_id",
        mode="before",
    )
    @classmethod
    def _optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, value: object) -> str:
        raw = str(getattr(value, "value", value) or "").strip().upper()
        try:
            return ResourceKind(raw).value
        except ValueError as exc:
            raise ValidationError("Resource kind is invalid.", code="RESOURCE_KIND_INVALID") from exc

    @field_validator("worker_type", mode="before")
    @classmethod
    def _worker_type(cls, value: object) -> str:
        raw = str(getattr(value, "value", value) or "").strip().upper()
        try:
            return WorkerType(raw).value
        except ValueError as exc:
            raise ValidationError(
                "Worker type is invalid.",
                code="RESOURCE_WORKER_TYPE_INVALID",
            ) from exc

    @field_validator("cost_type", mode="before")
    @classmethod
    def _cost_type(cls, value: object) -> str:
        raw = str(getattr(value, "value", value) or "").strip().upper()
        try:
            return CostType(raw).value
        except ValueError as exc:
            raise ValidationError("Cost type is invalid.", code="RESOURCE_COST_TYPE_INVALID") from exc

    @field_validator("hourly_rate", mode="before")
    @classmethod
    def _hourly_rate(cls, value: object) -> Decimal:
        return _decimal(value)

    @field_validator("capacity_percent", mode="before")
    @classmethod
    def _capacity_percent(cls, value: object) -> float:
        return _capacity(value)


@validated_dataclass
class ResourceCreateCommand(_ResourceMasterCommandValidation):
    name: str
    code: str = ""
    kind: str = ResourceKind.PERSON.value
    role: str = ""
    hourly_rate: Decimal = Decimal("0")
    cost_type: str = CostType.LABOR.value
    currency_code: str | None = None
    capacity_percent: float = 100.0
    address: str = ""
    contact: str = ""
    worker_type: str = WorkerType.EXTERNAL.value
    employee_id: str | None = None
    department_id: str | None = None
    site_id: str | None = None


@validated_dataclass
class ResourceUpdateCommand(_ResourceMasterCommandValidation):
    resource_id: str
    expected_version: int
    name: str
    code: str
    kind: str
    role: str
    hourly_rate: Decimal
    cost_type: str
    currency_code: str | None
    capacity_percent: float
    address: str
    contact: str
    worker_type: str
    employee_id: str | None
    department_id: str | None
    site_id: str | None

    @field_validator("resource_id", mode="before")
    @classmethod
    def _resource_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource ID is required for updates.",
            code="RESOURCE_ID_REQUIRED",
        )

    @field_validator("expected_version", mode="before")
    @classmethod
    def _expected_version(cls, value: object) -> int:
        if value in (None, ""):
            raise ValidationError(
                "Resource version is required.",
                code="RESOURCE_VERSION_REQUIRED",
            )
        resolved = int(value)
        if resolved < 1:
            raise ValidationError(
                "Resource version must be positive.",
                code="RESOURCE_VERSION_INVALID",
            )
        return resolved


@validated_dataclass
class ResourceLifecycleCommand:
    resource_id: str
    expected_version: int

    @field_validator("resource_id", mode="before")
    @classmethod
    def _resource_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource ID is required.",
            code="RESOURCE_ID_REQUIRED",
        )

    @field_validator("expected_version", mode="before")
    @classmethod
    def _expected_version(cls, value: object) -> int:
        if value in (None, ""):
            raise ValidationError(
                "Resource version is required.",
                code="RESOURCE_VERSION_REQUIRED",
            )
        resolved = int(value)
        if resolved < 1:
            raise ValidationError(
                "Resource version must be positive.",
                code="RESOURCE_VERSION_INVALID",
            )
        return resolved


@validated_dataclass
class ResourcePurgeCommand(ResourceLifecycleCommand):
    pass


__all__ = [
    "ResourceCreateCommand",
    "ResourceLifecycleCommand",
    "ResourcePurgeCommand",
    "ResourceUpdateCommand",
]
