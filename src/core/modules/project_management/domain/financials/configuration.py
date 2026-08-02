from __future__ import annotations

import re
from dataclasses import field
from datetime import date, datetime, timezone
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.finance.money.currency import CurrencyCode


_COST_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")


class FinancialProfileStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    CLOSED = "closed"


class BillingMethod(str, Enum):
    NON_BILLABLE = "non_billable"
    TIME_AND_MATERIALS = "time_and_materials"
    FIXED_PRICE = "fixed_price"
    COST_PLUS = "cost_plus"


class BudgetControlMode(str, Enum):
    NONE = "none"
    WARN = "warn"
    BLOCK = "block"


class CostCodePolicy(str, Enum):
    ALL_ACTIVE = "all_active"
    RESTRICTED = "restricted"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_timestamp(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("A valid timestamp is required.", code=code)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _required_identifier(value: object, *, label: str, code: str) -> str:
    return normalize_required_text(
        value,
        message=f"{label} is required.",
        code=code,
    )


@validated_dataclass
class ProjectFinancialProfile:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    currency_code: str
    status: FinancialProfileStatus = FinancialProfileStatus.ACTIVE
    billing_method: BillingMethod = BillingMethod.NON_BILLABLE
    budget_control_mode: BudgetControlMode = BudgetControlMode.WARN
    cost_code_policy: CostCodePolicy = CostCodePolicy.ALL_ACTIVE
    financial_start_date: date | None = None
    financial_end_date: date | None = None
    is_funded: bool = False
    is_billable: bool = False
    default_cost_code_id: str | None = None
    version: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator("id", "tenant_id", "organization_id", "project_id", mode="before")
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return _required_identifier(
            value,
            label=info.field_name.replace("_", " ").title(),
            code=f"FINANCIAL_PROFILE_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("default_cost_code_id", mode="before")
    @classmethod
    def _normalize_default_cost_code(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("currency_code", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                "Financial profile version must be positive.",
                code="FINANCIAL_PROFILE_VERSION_INVALID",
            )
        return resolved

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime:
        return _normalize_timestamp(
            value,
            code=f"FINANCIAL_PROFILE_{info.field_name.upper()}_INVALID",
        )

    @model_validator(mode="after")
    def _validate_policy(self) -> "ProjectFinancialProfile":
        if (
            self.financial_start_date
            and self.financial_end_date
            and self.financial_end_date < self.financial_start_date
        ):
            raise ValidationError(
                "Financial end date cannot be before financial start date.",
                code="FINANCIAL_PROFILE_DATE_RANGE_INVALID",
            )
        if self.is_billable and self.billing_method == BillingMethod.NON_BILLABLE:
            raise ValidationError(
                "A billable project requires a billing method.",
                code="FINANCIAL_PROFILE_BILLING_METHOD_REQUIRED",
            )
        if not self.is_billable and self.billing_method != BillingMethod.NON_BILLABLE:
            raise ValidationError(
                "A non-billable project cannot use a billing method.",
                code="FINANCIAL_PROFILE_BILLING_METHOD_INVALID",
            )
        return self

    def transition_to(self, target: FinancialProfileStatus) -> None:
        resolved = FinancialProfileStatus(target)
        allowed = {
            FinancialProfileStatus.DRAFT: {FinancialProfileStatus.ACTIVE},
            FinancialProfileStatus.ACTIVE: {
                FinancialProfileStatus.ON_HOLD,
                FinancialProfileStatus.CLOSED,
            },
            FinancialProfileStatus.ON_HOLD: {
                FinancialProfileStatus.ACTIVE,
                FinancialProfileStatus.CLOSED,
            },
            FinancialProfileStatus.CLOSED: set(),
        }
        if resolved == self.status:
            return
        if resolved not in allowed[self.status]:
            raise BusinessRuleError(
                f"Financial profile cannot transition from {self.status.value} to {resolved.value}.",
                code="FINANCIAL_PROFILE_TRANSITION_INVALID",
            )
        self.status = resolved
        self.updated_at = _utc_now()

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        currency_code: str,
        **values,
    ) -> "ProjectFinancialProfile":
        return ProjectFinancialProfile(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            currency_code=currency_code,
            **values,
        )


@validated_dataclass
class ProjectCostCode:
    id: str
    tenant_id: str
    organization_id: str
    code: str
    name: str
    description: str = ""
    parent_id: str | None = None
    external_system: str | None = None
    external_reference: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool = True
    version: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator("id", "tenant_id", "organization_id", mode="before")
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return _required_identifier(
            value,
            label=info.field_name.replace("_", " ").title(),
            code=f"PROJECT_COST_CODE_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, value: object) -> str:
        normalized = normalize_optional_text(value).upper()
        if not _COST_CODE_PATTERN.fullmatch(normalized):
            raise ValidationError(
                "Cost code must use 1-64 uppercase letters, numbers, dots, underscores, or hyphens.",
                code="PROJECT_COST_CODE_INVALID",
            )
        return normalized

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Cost-code name is required.",
            code="PROJECT_COST_CODE_NAME_REQUIRED",
        )

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("parent_id", "external_system", "external_reference", mode="before")
    @classmethod
    def _normalize_optional_fields(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                "Cost-code version must be positive.",
                code="PROJECT_COST_CODE_VERSION_INVALID",
            )
        return resolved

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime:
        return _normalize_timestamp(
            value,
            code=f"PROJECT_COST_CODE_{info.field_name.upper()}_INVALID",
        )

    @model_validator(mode="after")
    def _validate_hierarchy_and_dates(self) -> "ProjectCostCode":
        if self.parent_id == self.id:
            raise ValidationError(
                "A cost code cannot be its own parent.",
                code="PROJECT_COST_CODE_PARENT_SELF",
            )
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError(
                "Cost-code effective end cannot be before its start.",
                code="PROJECT_COST_CODE_EFFECTIVE_RANGE_INVALID",
            )
        if bool(self.external_system) != bool(self.external_reference):
            raise ValidationError(
                "External system and external reference must be supplied together.",
                code="PROJECT_COST_CODE_EXTERNAL_MAPPING_INCOMPLETE",
            )
        return self

    def is_effective_on(self, value: date) -> bool:
        return (
            self.is_active
            and (self.effective_from is None or self.effective_from <= value)
            and (self.effective_to is None or value <= self.effective_to)
        )

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        code: str,
        name: str,
        **values,
    ) -> "ProjectCostCode":
        return ProjectCostCode(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            code=code,
            name=name,
            **values,
        )


@validated_dataclass
class ProjectCostCodeRestriction:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    cost_code_id: str
    created_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id",
        "tenant_id",
        "organization_id",
        "project_id",
        "cost_code_id",
        mode="before",
    )
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return _required_identifier(
            value,
            label=info.field_name.replace("_", " ").title(),
            code=f"PROJECT_COST_CODE_RESTRICTION_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: object) -> datetime:
        return _normalize_timestamp(
            value,
            code="PROJECT_COST_CODE_RESTRICTION_CREATED_AT_INVALID",
        )

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        cost_code_id: str,
    ) -> "ProjectCostCodeRestriction":
        return ProjectCostCodeRestriction(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            cost_code_id=cost_code_id,
        )


__all__ = [
    "BillingMethod",
    "BudgetControlMode",
    "CostCodePolicy",
    "FinancialProfileStatus",
    "ProjectCostCode",
    "ProjectCostCodeRestriction",
    "ProjectFinancialProfile",
]
