from __future__ import annotations

from dataclasses import field
from datetime import date, datetime, timezone
from decimal import Decimal
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


class FinancialChangeStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPLIED = "applied"
    REJECTED = "rejected"


class FinancialChangeImpactType(str, Enum):
    BUDGET = "budget"
    FORECAST = "forecast"
    SCHEDULE = "schedule"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("A valid timestamp is required.", code=code)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@validated_dataclass
class FinancialChangeRequest:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    title: str
    reason: str
    effective_date: date
    currency_code: str
    created_by: str
    revision: int = 1
    status: FinancialChangeStatus = FinancialChangeStatus.DRAFT
    description: str = ""
    base_budget_id: str | None = None
    base_budget_revision: int | None = None
    base_forecast_id: str | None = None
    base_forecast_revision: int | None = None
    approval_request_id: str | None = None
    applied_budget_id: str | None = None
    applied_forecast_id: str | None = None
    applied_schedule_count: int = 0
    submitted_by: str | None = None
    submitted_at: datetime | None = None
    applied_by: str | None = None
    applied_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    rejection_notes: str = ""
    row_version: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "project_id", "created_by",
        mode="before",
    )
    @classmethod
    def _required_identifiers(cls, value: object, info) -> str:
        return normalize_required_text(
            value,
            message=f"{info.field_name.replace('_', ' ').title()} is required.",
            code=f"FINANCIAL_CHANGE_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("title", "reason", mode="before")
    @classmethod
    def _required_text(cls, value: object, info) -> str:
        return normalize_required_text(
            value,
            message=f"Financial change {info.field_name} is required.",
            code=f"FINANCIAL_CHANGE_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("description", "rejection_notes", mode="before")
    @classmethod
    def _optional_text(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator(
        "base_budget_id", "base_forecast_id", "approval_request_id",
        "applied_budget_id", "applied_forecast_id", "submitted_by",
        "applied_by", "rejected_by",
        mode="before",
    )
    @classmethod
    def _optional_identifiers(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("currency_code", mode="before")
    @classmethod
    def _currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("revision", "row_version", mode="before")
    @classmethod
    def _positive_versions(cls, value: object, info) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                f"Financial change {info.field_name.replace('_', ' ')} must be positive.",
                code=f"FINANCIAL_CHANGE_{info.field_name.upper()}_INVALID",
            )
        return resolved

    @field_validator("applied_schedule_count", mode="before")
    @classmethod
    def _schedule_count(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 0:
            raise ValidationError(
                "Applied schedule count cannot be negative.",
                code="FINANCIAL_CHANGE_SCHEDULE_COUNT_INVALID",
            )
        return resolved

    @field_validator("base_budget_revision", "base_forecast_revision", mode="before")
    @classmethod
    def _optional_positive_revision(cls, value: object, info) -> int | None:
        if value is None:
            return None
        resolved = int(value)
        if resolved < 1:
            raise ValidationError(
                f"Financial change {info.field_name.replace('_', ' ')} must be positive.",
                code=f"FINANCIAL_CHANGE_{info.field_name.upper()}_INVALID",
            )
        return resolved

    @field_validator(
        "submitted_at", "applied_at", "rejected_at", mode="before"
    )
    @classmethod
    def _optional_timestamps(cls, value: object, info) -> datetime | None:
        if value is None:
            return None
        return _timestamp(value, code=f"FINANCIAL_CHANGE_{info.field_name.upper()}_INVALID")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _timestamps(cls, value: object, info) -> datetime:
        return _timestamp(value, code=f"FINANCIAL_CHANGE_{info.field_name.upper()}_INVALID")

    @model_validator(mode="after")
    def _base_pairs(self) -> "FinancialChangeRequest":
        if (self.base_budget_id is None) != (self.base_budget_revision is None):
            raise ValidationError(
                "Financial change base budget id and revision must be provided together.",
                code="FINANCIAL_CHANGE_BASE_BUDGET_INCOMPLETE",
            )
        if (self.base_forecast_id is None) != (self.base_forecast_revision is None):
            raise ValidationError(
                "Financial change base forecast id and revision must be provided together.",
                code="FINANCIAL_CHANGE_BASE_FORECAST_INCOMPLETE",
            )
        return self

    def ensure_draft(self) -> None:
        if self.status is not FinancialChangeStatus.DRAFT:
            raise BusinessRuleError(
                "Only draft financial changes can be modified.",
                code="FINANCIAL_CHANGE_IMMUTABLE",
            )

    def touch(self, *, updated_at: datetime) -> None:
        self.updated_at = updated_at

    def update_draft(
        self,
        *,
        title: str,
        reason: str,
        description: str,
        effective_date: date,
        updated_at: datetime,
    ) -> None:
        self.ensure_draft()
        self.title = title
        self.reason = reason
        self.description = description
        self.effective_date = effective_date
        self.updated_at = updated_at

    def submit(
        self,
        *,
        approval_request_id: str,
        submitted_by: str,
        submitted_at: datetime,
    ) -> None:
        self.ensure_draft()
        self.status = FinancialChangeStatus.PENDING_APPROVAL
        self.approval_request_id = approval_request_id
        self.submitted_by = submitted_by
        self.submitted_at = submitted_at
        self.updated_at = submitted_at

    def apply(
        self,
        *,
        applied_by: str,
        applied_at: datetime,
        applied_budget_id: str | None,
        applied_forecast_id: str | None,
        applied_schedule_count: int,
    ) -> None:
        if self.status is not FinancialChangeStatus.PENDING_APPROVAL:
            raise BusinessRuleError(
                "Only a pending financial change can be applied.",
                code="FINANCIAL_CHANGE_APPLY_STATUS_INVALID",
            )
        self.status = FinancialChangeStatus.APPLIED
        self.applied_by = applied_by
        self.applied_at = applied_at
        self.applied_budget_id = applied_budget_id
        self.applied_forecast_id = applied_forecast_id
        self.applied_schedule_count = applied_schedule_count
        self.updated_at = applied_at

    def reject(self, *, rejected_by: str, rejected_at: datetime, notes: str = "") -> None:
        if self.status is not FinancialChangeStatus.PENDING_APPROVAL:
            raise BusinessRuleError(
                "Only a pending financial change can be rejected.",
                code="FINANCIAL_CHANGE_REJECT_STATUS_INVALID",
            )
        self.status = FinancialChangeStatus.REJECTED
        self.rejected_by = rejected_by
        self.rejected_at = rejected_at
        self.rejection_notes = notes
        self.updated_at = rejected_at

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        title: str,
        reason: str,
        effective_date: date,
        currency_code: str,
        created_by: str,
        revision: int,
        created_at: datetime | None = None,
        **values,
    ) -> "FinancialChangeRequest":
        now = created_at or _utc_now()
        return FinancialChangeRequest(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            title=title,
            reason=reason,
            effective_date=effective_date,
            currency_code=currency_code,
            created_by=created_by,
            revision=revision,
            created_at=now,
            updated_at=now,
            **values,
        )


@validated_dataclass
class FinancialChangeImpact:
    id: str
    tenant_id: str
    organization_id: str
    change_request_id: str
    project_id: str
    impact_type: FinancialChangeImpactType
    description: str
    amount: Decimal = Decimal("0")
    currency_code: str | None = None
    cost_code_id: str | None = None
    task_id: str | None = None
    target_line_id: str | None = None
    target_task_version: int | None = None
    schedule_start: date | None = None
    schedule_finish: date | None = None
    applied_reference_type: str | None = None
    applied_reference_id: str | None = None
    row_version: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "change_request_id", "project_id",
        mode="before",
    )
    @classmethod
    def _required_identifiers(cls, value: object, info) -> str:
        return normalize_required_text(
            value,
            message=f"{info.field_name.replace('_', ' ').title()} is required.",
            code=f"FINANCIAL_CHANGE_IMPACT_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("description", mode="before")
    @classmethod
    def _description(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Financial change impact description is required.",
            code="FINANCIAL_CHANGE_IMPACT_DESCRIPTION_REQUIRED",
        )

    @field_validator(
        "cost_code_id", "task_id", "target_line_id", "applied_reference_type",
        "applied_reference_id",
        mode="before",
    )
    @classmethod
    def _optional_identifiers(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("amount", mode="before")
    @classmethod
    def _decimal(cls, value: object) -> Decimal:
        return Decimal(str(value if value not in (None, "") else "0"))

    @field_validator("currency_code", mode="before")
    @classmethod
    def _optional_currency(cls, value: object) -> str | None:
        if value is None or not str(value).strip():
            return None
        currency = CurrencyCode(str(value))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _created_timestamp(cls, value: object, info) -> datetime:
        return _timestamp(
            value, code=f"FINANCIAL_CHANGE_IMPACT_{info.field_name.upper()}_INVALID"
        )

    @field_validator("row_version", mode="before")
    @classmethod
    def _row_version(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                "Financial change impact version must be positive.",
                code="FINANCIAL_CHANGE_IMPACT_VERSION_INVALID",
            )
        return resolved

    @field_validator("target_task_version", mode="before")
    @classmethod
    def _target_version(cls, value: object) -> int | None:
        if value is None:
            return None
        resolved = int(value)
        if resolved < 1:
            raise ValidationError(
                "Schedule impact target task version must be positive.",
                code="FINANCIAL_CHANGE_SCHEDULE_VERSION_INVALID",
            )
        return resolved

    @model_validator(mode="after")
    def _typed_shape(self) -> "FinancialChangeImpact":
        monetary = {
            FinancialChangeImpactType.BUDGET,
            FinancialChangeImpactType.FORECAST,
        }
        if self.impact_type in monetary:
            if self.amount == 0 or not self.currency_code or not self.cost_code_id:
                raise ValidationError(
                    "Monetary change impacts require a non-zero amount, currency, and cost code.",
                    code="FINANCIAL_CHANGE_IMPACT_MONETARY_FIELDS_REQUIRED",
                )
        if self.impact_type is FinancialChangeImpactType.SCHEDULE:
            if (
                not self.task_id
                or self.target_task_version is None
                or (self.schedule_start is None and self.schedule_finish is None)
            ):
                raise ValidationError(
                    "Schedule impacts require a versioned task and a start or finish date.",
                    code="FINANCIAL_CHANGE_SCHEDULE_FIELDS_REQUIRED",
                )
            if self.amount != 0 or self.currency_code or self.cost_code_id or self.target_line_id:
                raise ValidationError(
                    "Schedule impacts cannot carry financial-line dimensions; use a separate "
                    "budget or forecast impact for cost effects.",
                    code="FINANCIAL_CHANGE_SCHEDULE_FINANCIAL_FIELDS_INVALID",
                )
        elif self.target_task_version is not None:
            raise ValidationError(
                "Only schedule impacts may snapshot a task version.",
                code="FINANCIAL_CHANGE_TARGET_TASK_VERSION_INVALID",
            )
        if self.schedule_start and self.schedule_finish and self.schedule_finish < self.schedule_start:
            raise ValidationError(
                "Schedule impact finish cannot precede start.",
                code="FINANCIAL_CHANGE_SCHEDULE_PERIOD_INVALID",
            )
        if self.amount < 0 and not self.target_line_id and self.impact_type in {
            FinancialChangeImpactType.BUDGET,
            FinancialChangeImpactType.FORECAST,
        }:
            raise ValidationError(
                "Negative budget or forecast impacts require an exact target line.",
                code="FINANCIAL_CHANGE_NEGATIVE_TARGET_REQUIRED",
            )
        if bool(self.applied_reference_type) != bool(self.applied_reference_id):
            raise ValidationError(
                "Applied reference type and id must be provided together.",
                code="FINANCIAL_CHANGE_APPLIED_REFERENCE_INCOMPLETE",
            )
        return self

    def update_draft(
        self,
        *,
        description: str,
        amount: Decimal,
        currency_code: str | None,
        cost_code_id: str | None,
        task_id: str | None,
        target_line_id: str | None,
        target_task_version: int | None,
        schedule_start: date | None,
        schedule_finish: date | None,
        updated_at: datetime,
    ) -> None:
        candidate = FinancialChangeImpact(
            id=self.id,
            tenant_id=self.tenant_id,
            organization_id=self.organization_id,
            change_request_id=self.change_request_id,
            project_id=self.project_id,
            impact_type=self.impact_type,
            description=description,
            amount=amount,
            currency_code=currency_code,
            cost_code_id=cost_code_id,
            task_id=task_id,
            target_line_id=target_line_id,
            target_task_version=target_task_version,
            schedule_start=schedule_start,
            schedule_finish=schedule_finish,
            row_version=self.row_version,
            created_at=self.created_at,
            updated_at=updated_at,
        )
        self.description = candidate.description
        self.amount = candidate.amount
        self.currency_code = candidate.currency_code
        self.cost_code_id = candidate.cost_code_id
        self.task_id = candidate.task_id
        self.target_line_id = candidate.target_line_id
        self.target_task_version = candidate.target_task_version
        self.schedule_start = candidate.schedule_start
        self.schedule_finish = candidate.schedule_finish
        self.updated_at = candidate.updated_at

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        change_request_id: str,
        project_id: str,
        impact_type: FinancialChangeImpactType,
        description: str,
        created_at: datetime | None = None,
        **values,
    ) -> "FinancialChangeImpact":
        now = created_at or _utc_now()
        return FinancialChangeImpact(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            change_request_id=change_request_id,
            project_id=project_id,
            impact_type=impact_type,
            description=description,
            created_at=now,
            updated_at=now,
            **values,
        )


__all__ = [
    "FinancialChangeImpact",
    "FinancialChangeImpactType",
    "FinancialChangeRequest",
    "FinancialChangeStatus",
]
