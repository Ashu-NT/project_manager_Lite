from __future__ import annotations

from datetime import date

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.finance.money.currency import CurrencyCode


@validated_dataclass
class Project:
    id: str
    name: str
    code: str = ""
    description: str = ""
    start_date: date | None = None
    end_date: date | None = None
    status: ProjectStatus = ProjectStatus.PLANNED
    client_name: str | None = None
    client_contact: str | None = None
    planned_budget: float | None = None
    currency: str | None = None
    organization_id: str | None = None
    site_id: str | None = None
    client_party_id: str | None = None
    manager_user_id: str | None = None
    version: int = 1

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        normalized = normalize_required_text(
            value,
            message="Project name cannot be empty.",
            code="PROJECT_NAME_EMPTY",
        )
        if len(normalized) < 3:
            raise ValidationError(
                "Project name must be at least 3 characters.",
                code="PROJECT_NAME_TOO_SHORT",
            )
        return normalized

    @field_validator("code", "description", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator(
        "client_name",
        "client_contact",
        "organization_id",
        "site_id",
        "client_party_id",
        "manager_user_id",
        mode="before",
    )
    @classmethod
    def _normalize_identifier_fields(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: object) -> str | None:
        normalized = normalize_optional_identifier(value)
        if not normalized:
            return None
        try:
            currency = CurrencyCode(normalized)
            currency.minor_unit_quantum()
        except ValidationError as exc:
            raise ValidationError(
                "Project currency must be an active ISO 4217 currency with defined minor units.",
                code="PROJECT_CURRENCY_INVALID",
            ) from exc
        return currency.code

    @field_validator("planned_budget", mode="before")
    @classmethod
    def _validate_planned_budget(cls, value: object) -> float | None:
        if value in (None, ""):
            return None
        resolved = float(value)
        if resolved < 0:
            raise ValidationError(
                "Planned budget cannot be negative.",
                code="PROJECT_PLANNED_BUDGET_INVALID",
            )
        return resolved

    @model_validator(mode="after")
    def _validate_date_range(self) -> "Project":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                "Project end date cannot be before start date.",
                code="PROJECT_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(name: str, description: str = "", **extra) -> "Project":
        return Project(
            id=generate_id(),
            name=name,
            description=description,
            **extra,
        )


@validated_dataclass
class ProjectResource:
    id: str
    project_id: str
    resource_id: str
    hourly_rate: float | None = None
    currency_code: str | None = None
    planned_hours: float = 0.0
    is_active: bool = True

    @field_validator("project_id", mode="before")
    @classmethod
    def _validate_project_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Project ID is required.",
            code="PROJECT_RESOURCE_PROJECT_REQUIRED",
        )

    @field_validator("resource_id", mode="before")
    @classmethod
    def _validate_resource_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource ID is required.",
            code="PROJECT_RESOURCE_RESOURCE_REQUIRED",
        )

    @field_validator("currency_code", mode="before")
    @classmethod
    def _normalize_currency_code(cls, value: object) -> str | None:
        normalized = normalize_optional_identifier(value)
        if not normalized:
            return None
        try:
            currency = CurrencyCode(normalized)
            currency.minor_unit_quantum()
        except ValidationError as exc:
            raise ValidationError(
                "Project resource currency must be an active ISO 4217 currency with defined minor units.",
                code="PROJECT_RESOURCE_CURRENCY_INVALID",
            ) from exc
        return currency.code

    @field_validator("hourly_rate", mode="before")
    @classmethod
    def _validate_hourly_rate(cls, value: object) -> float | None:
        if value in (None, ""):
            return None
        resolved = float(value)
        if resolved < 0:
            raise ValidationError(
                "Hourly rate cannot be negative.",
                code="PROJECT_RESOURCE_HOURLY_RATE_INVALID",
            )
        return resolved

    @field_validator("planned_hours", mode="before")
    @classmethod
    def _validate_planned_hours(cls, value: object) -> float:
        resolved = float(value if value not in (None, "") else 0.0)
        if resolved < 0:
            raise ValidationError(
                "planned_hours cannot be negative.",
                code="PROJECT_RESOURCE_PLANNED_HOURS_INVALID",
            )
        return resolved

    @staticmethod
    def create(
        project_id: str,
        resource_id: str,
        hourly_rate: float | None = None,
        currency_code: str | None = None,
        planned_hours: float = 0.0,
        is_active: bool = True,
    ) -> "ProjectResource":
        return ProjectResource(
            id=generate_id(),
            project_id=project_id,
            resource_id=resource_id,
            hourly_rate=hourly_rate,
            currency_code=currency_code,
            planned_hours=planned_hours,
            is_active=is_active,
        )
