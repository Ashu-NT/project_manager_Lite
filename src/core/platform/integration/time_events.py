from __future__ import annotations

from datetime import date, datetime, timezone

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator

from src.core.platform.finance import DecimalQuantityPayload


APPROVED_TIME_ENTRY_EVENT_TYPE = "platform_time.time_entry.approved.v1"


class ApprovedTimeEntryEventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    approved_snapshot_id: str
    timesheet_period_id: str
    time_entry_id: str
    work_allocation_id: str
    resource_id: str
    project_id: str
    organization_id: str
    source_revision: int
    source_content_hash: str
    work_date: date
    approved_at: AwareDatetime
    hours: DecimalQuantityPayload
    employee_id: str | None = None
    assignment_id: str | None = None
    task_id: str | None = None
    correction_of_revision: int | None = None

    @field_validator(
        "approved_snapshot_id", "timesheet_period_id", "time_entry_id",
        "work_allocation_id", "resource_id", "project_id", "organization_id",
        mode="before",
    )
    @classmethod
    def _required(cls, value: object) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Approved Time event identifiers are required")
        return normalized

    @field_validator("source_content_hash", mode="before")
    @classmethod
    def _hash(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
            raise ValueError("Approved Time source content hash must be SHA-256")
        return normalized

    @field_validator("source_revision", mode="before")
    @classmethod
    def _revision(cls, value: object) -> int:
        revision = int(value)
        if revision < 1:
            raise ValueError("Approved Time source revision must be positive")
        return revision

    @field_validator("correction_of_revision", mode="before")
    @classmethod
    def _correction(cls, value: object) -> int | None:
        if value in (None, ""):
            return None
        revision = int(value)
        if revision < 1:
            raise ValueError("Approved Time correction revision must be positive")
        return revision

    @field_validator("approved_at", mode="after")
    @classmethod
    def _approved_at(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


__all__ = ["APPROVED_TIME_ENTRY_EVENT_TYPE", "ApprovedTimeEntryEventPayload"]
