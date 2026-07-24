from __future__ import annotations

from pydantic import field_validator

from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


@validated_dataclass
class Resource:
    id: str
    name: str
    code: str = ""
    role: str = ""
    hourly_rate: float = 0.0
    is_active: bool = True
    cost_type: CostType = CostType.LABOR
    currency_code: str | None = None
    version: int = 1
    capacity_percent: float = 100.0
    address: str = ""
    contact: str = ""
    worker_type: WorkerType = WorkerType.EXTERNAL
    employee_id: str | None = None
    organization_id: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource name cannot be empty.",
            code="RESOURCE_NAME_EMPTY",
        )

    @field_validator("code", "role", "address", "contact", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("employee_id", "organization_id", mode="before")
    @classmethod
    def _normalize_identifier_fields(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("hourly_rate", mode="before")
    @classmethod
    def _validate_hourly_rate(cls, value: object) -> float:
        resolved = float(value if value not in (None, "") else 0.0)
        if resolved < 0:
            raise ValidationError(
                "Hourly rate cannot be negative.",
                code="RESOURCE_HOURLY_RATE_INVALID",
            )
        return resolved

    @field_validator("capacity_percent", mode="before")
    @classmethod
    def _validate_capacity_percent(cls, value: object) -> float:
        resolved = float(value if value not in (None, "") else 100.0)
        if resolved <= 0.0:
            raise ValidationError(
                "Capacity percent must be greater than zero.",
                code="RESOURCE_CAPACITY_INVALID",
            )
        return resolved

    @field_validator("currency_code", mode="before")
    @classmethod
    def _normalize_currency_code(cls, value: object) -> str | None:
        normalized = normalize_optional_identifier(value)
        return normalized.upper() if normalized else None

    @field_validator("cost_type", mode="before")
    @classmethod
    def _validate_cost_type(cls, value: object) -> CostType:
        if isinstance(value, CostType):
            return value
        raw = normalize_optional_text(value).upper() or CostType.LABOR.value
        try:
            return CostType(raw)
        except ValueError as exc:
            raise ValidationError(
                "Cost type is invalid.",
                code="RESOURCE_COST_TYPE_INVALID",
            ) from exc

    @field_validator("worker_type", mode="before")
    @classmethod
    def _validate_worker_type(cls, value: object) -> WorkerType:
        if isinstance(value, WorkerType):
            return value
        raw = normalize_optional_text(value).upper() or WorkerType.EXTERNAL.value
        try:
            return WorkerType(raw)
        except ValueError as exc:
            raise ValidationError(
                "Worker type is invalid.",
                code="RESOURCE_WORKER_TYPE_INVALID",
            ) from exc

    @staticmethod
    def create(
        name: str,
        role: str = "",
        hourly_rate: float = 0.0,
        is_active: bool = True,
        cost_type: CostType = CostType.LABOR,
        currency_code: str | None = None,
        capacity_percent: float = 100.0,
        address: str = "",
        contact: str = "",
        worker_type: WorkerType = WorkerType.EXTERNAL,
        employee_id: str | None = None,
        code: str = "",
        organization_id: str | None = None,
    ) -> "Resource":
        return Resource(
            id=generate_id(),
            name=name,
            code=code,
            role=role,
            hourly_rate=hourly_rate,
            is_active=is_active,
            cost_type=cost_type,
            currency_code=currency_code,
            capacity_percent=capacity_percent,
            address=address,
            contact=contact,
            worker_type=worker_type,
            employee_id=employee_id,
            organization_id=organization_id,
        )


__all__ = ["Resource"]
