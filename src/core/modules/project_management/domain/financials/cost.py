from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import field_validator

from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.finance.money.currency import CurrencyCode


class CommitmentStatus(str, Enum):
    UNCOMMITTED = "uncommitted"  # planned/estimated only, no purchase order
    COMMITTED = "committed"      # purchase order raised; cost is obligated
    INVOICED = "invoiced"        # invoice received from vendor
    PAID = "paid"                # payment released


@validated_dataclass
class CostItem:
    id: str
    project_id: str
    task_id: str | None
    description: str
    planned_amount: float
    code: str = ""
    cost_type: CostType = CostType.OVERHEAD
    committed_amount: float = 0.0
    actual_amount: float = 0.0
    forecast_amount: float | None = None   # manual ETC override for this item
    commitment_status: CommitmentStatus = CommitmentStatus.UNCOMMITTED
    vendor_reference: str | None = None    # PO number, invoice number, contract ref
    incurred_date: date | None = None
    currency_code: str | None = None
    version: int = 1

    @field_validator("project_id", mode="before")
    @classmethod
    def _validate_project_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Project ID is required.",
            code="COST_PROJECT_REQUIRED",
        )

    @field_validator("task_id", mode="before")
    @classmethod
    def _normalize_task_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("description", mode="before")
    @classmethod
    def _validate_description(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Cost description cannot be empty.",
            code="COST_DESCRIPTION_EMPTY",
        )

    @field_validator("code", mode="before")
    @classmethod
    def _normalize_code(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("vendor_reference", mode="before")
    @classmethod
    def _normalize_vendor_reference(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("planned_amount", mode="before")
    @classmethod
    def _validate_planned_amount(cls, value: object) -> float:
        if value in (None, ""):
            raise ValidationError(
                "Planned amount is required.",
                code="COST_PLANNED_AMOUNT_REQUIRED",
            )
        resolved = float(value)
        if resolved < 0:
            raise ValidationError(
                "Planned amount cannot be negative.",
                code="COST_PLANNED_AMOUNT_INVALID",
            )
        return resolved

    @field_validator("committed_amount", "actual_amount", mode="before")
    @classmethod
    def _validate_amount_fields(cls, value: object, info) -> float:
        resolved = float(value if value not in (None, "") else 0.0)
        if resolved < 0:
            label = info.field_name.replace("_", " ")
            raise ValidationError(
                f"{label.capitalize()} cannot be negative.",
                code=f"COST_{info.field_name.upper()}_INVALID",
            )
        return resolved

    @field_validator("forecast_amount", mode="before")
    @classmethod
    def _validate_forecast_amount(cls, value: object) -> float | None:
        if value in (None, ""):
            return None
        resolved = float(value)
        if resolved < 0:
            raise ValidationError(
                "Forecast amount cannot be negative.",
                code="COST_FORECAST_AMOUNT_INVALID",
            )
        return resolved

    @field_validator("cost_type", mode="before")
    @classmethod
    def _validate_cost_type(cls, value: object) -> CostType:
        if isinstance(value, CostType):
            return value
        raw = normalize_optional_text(value).upper() or CostType.OVERHEAD.value
        try:
            return CostType(raw)
        except ValueError as exc:
            raise ValidationError(
                "Cost type is invalid.",
                code="COST_TYPE_INVALID",
            ) from exc

    @field_validator("commitment_status", mode="before")
    @classmethod
    def _validate_commitment_status(cls, value: object) -> CommitmentStatus:
        if isinstance(value, CommitmentStatus):
            return value
        raw = normalize_optional_text(value).lower() or CommitmentStatus.UNCOMMITTED.value
        try:
            return CommitmentStatus(raw)
        except ValueError as exc:
            raise ValidationError(
                "Commitment status is invalid.",
                code="COST_COMMITMENT_STATUS_INVALID",
            ) from exc

    @field_validator("incurred_date", mode="before")
    @classmethod
    def _validate_incurred_date(cls, value: object) -> date | None:
        if value in (None, ""):
            return None
        if not isinstance(value, date):
            raise ValidationError(
                "Incurred date must be a valid date.",
                code="COST_INCURRED_DATE_INVALID",
            )
        return value

    @field_validator("currency_code", mode="before")
    @classmethod
    def _normalize_currency_code(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        if not normalized:
            return None
        try:
            currency = CurrencyCode(normalized)
            currency.minor_unit_quantum()
        except ValidationError as exc:
            raise ValidationError(
                "Cost currency must be an active ISO 4217 currency with defined minor units.",
                code="COST_CURRENCY_INVALID",
            ) from exc
        return currency.code

    @staticmethod
    def create(
        project_id: str,
        description: str,
        planned_amount: float,
        task_id: str | None = None,
        cost_type: CostType = CostType.OVERHEAD,
        committed_amount: float = 0.0,
        actual_amount: float = 0.0,
        forecast_amount: float | None = None,
        commitment_status: CommitmentStatus = CommitmentStatus.UNCOMMITTED,
        vendor_reference: str | None = None,
        incurred_date: date | None = None,
        currency_code: str | None = None,
        code: str = "",
    ) -> "CostItem":
        return CostItem(
            id=generate_id(),
            project_id=project_id,
            task_id=task_id,
            code=code,
            description=description,
            planned_amount=planned_amount,
            cost_type=cost_type,
            committed_amount=committed_amount,
            actual_amount=actual_amount,
            forecast_amount=forecast_amount,
            commitment_status=commitment_status,
            vendor_reference=vendor_reference,
            incurred_date=incurred_date,
            currency_code=currency_code,
        )

    @property
    def remaining_committed(self) -> float:
        """Committed spend not yet invoiced."""
        if self.commitment_status == CommitmentStatus.COMMITTED:
            return max(0.0, self.committed_amount - self.actual_amount)
        return 0.0

    @property
    def effective_forecast(self) -> float:
        """Return the manual forecast_amount if set, otherwise fall back to planned_amount."""
        if self.forecast_amount is not None:
            return self.forecast_amount
        return self.planned_amount


__all__ = ["CommitmentStatus", "CostItem"]
