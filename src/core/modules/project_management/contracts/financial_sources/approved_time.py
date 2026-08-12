from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, field_validator, model_validator

from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceReference,
    FinancialSourceType,
    _FinancialSourceContract,
    _required_text,
)
from src.core.platform.finance.money.serialization import DecimalQuantityPayload


class ApprovedTimeFinancialSource(_FinancialSourceContract):
    reference: FinancialSourceReference
    approval_status: Literal["APPROVED"] = "APPROVED"
    approved_snapshot_id: str
    timesheet_period_id: str
    time_entry_id: str
    work_allocation_id: str
    resource_id: str
    employee_id: str | None = None
    assignment_id: str | None = None
    task_id: str | None = None
    work_date: date
    approved_at: AwareDatetime
    hours: DecimalQuantityPayload
    correction_of_revision: str | None = None

    @field_validator(
        "approved_snapshot_id",
        "timesheet_period_id",
        "time_entry_id",
        "work_allocation_id",
        "resource_id",
        mode="before",
    )
    @classmethod
    def _validate_required_text(cls, value: object, info) -> str:
        return _required_text(value, label=info.field_name.replace("_", " ").capitalize())

    @field_validator("employee_id", "assignment_id", "task_id", "correction_of_revision", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @field_validator("approved_at", mode="after")
    @classmethod
    def _normalize_approved_at(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _validate_time_source(self) -> "ApprovedTimeFinancialSource":
        reference = self.reference
        if (
            reference.source_module != FinancialSourceModule.PLATFORM_TIME
            or reference.source_type != FinancialSourceType.TIME_ENTRY
            or reference.posting_purpose != FinancialPostingPurpose.LABOR_ACTUAL
        ):
            raise ValueError("Approved Time source reference is incompatible")
        if reference.source_id != self.time_entry_id:
            raise ValueError("Time entry ID must match the source reference")
        if self.hours.unit != "HOUR" or Decimal(self.hours.value) <= 0:
            raise ValueError("Approved Time hours must be a positive HOUR quantity")
        return self


__all__ = ["ApprovedTimeFinancialSource"]
