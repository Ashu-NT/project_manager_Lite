from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import Enum

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from pydantic import field_validator, model_validator


class BaselineStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


def _coerce_optional_text(value: object) -> str | None:
    normalized = normalize_optional_text(value)
    return normalized or None


def _coerce_required_date(value: object, *, message: str, code: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, date):
        raise ValidationError(message, code=code)
    return value


def _coerce_optional_date(value: object, *, code: str) -> date | None:
    if value in (None, ""):
        return None
    return _coerce_required_date(
        value,
        message="Baseline dates must be valid dates.",
        code=code,
    )


def _coerce_non_negative_int(value: object, *, message: str, code: str) -> int:
    try:
        resolved = int(value if value not in (None, "") else 0)
    except (TypeError, ValueError) as exc:
        raise ValidationError(message, code=code) from exc
    if resolved < 0:
        raise ValidationError(message, code=code)
    return resolved


def _coerce_float(value: object, *, message: str, code: str) -> float:
    try:
        return float(value if value not in (None, "") else 0.0)
    except (TypeError, ValueError) as exc:
        raise ValidationError(message, code=code) from exc


def _coerce_non_negative_float(value: object, *, message: str, code: str) -> float:
    resolved = _coerce_float(value, message=message, code=code)
    if resolved < 0:
        raise ValidationError(message, code=code)
    return resolved


def coerce_baseline_status(value: BaselineStatus | str | None) -> BaselineStatus:
    if isinstance(value, BaselineStatus):
        return value
    raw = normalize_optional_text(value).lower() or BaselineStatus.DRAFT.value
    try:
        return BaselineStatus(raw)
    except ValueError as exc:
        raise ValidationError("Baseline status is invalid.", code="BASELINE_STATUS_INVALID") from exc


@validated_dataclass
class ProjectBaseline:
    id: str
    project_id: str
    name: str
    created_at: date
    status: BaselineStatus = BaselineStatus.DRAFT
    version: int = 1
    submitted_by: str | None = None
    submitted_at: date | None = None
    approved_by: str | None = None
    approved_at: date | None = None
    notes: str = ""

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Baseline ID is required.",
            code="BASELINE_ID_REQUIRED",
        )

    @field_validator("project_id", mode="before")
    @classmethod
    def _validate_project_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Project ID is required.",
            code="BASELINE_PROJECT_REQUIRED",
        )

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        normalized = normalize_optional_text(value)
        return normalized or "Baseline"

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: object) -> date:
        return _coerce_required_date(
            value,
            message="Baseline creation date is required.",
            code="BASELINE_CREATED_AT_INVALID",
        )

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: BaselineStatus | str | None) -> BaselineStatus:
        return coerce_baseline_status(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        resolved = _coerce_non_negative_int(
            value if value not in (None, "") else 1,
            message="Baseline version must be positive.",
            code="BASELINE_VERSION_INVALID",
        )
        if resolved <= 0:
            raise ValidationError("Baseline version must be positive.", code="BASELINE_VERSION_INVALID")
        return resolved

    @field_validator("submitted_by", "approved_by", mode="before")
    @classmethod
    def _normalize_optional_people(cls, value: object) -> str | None:
        return _coerce_optional_text(value)

    @field_validator("submitted_at", "approved_at", mode="before")
    @classmethod
    def _validate_optional_dates(cls, value: object) -> date | None:
        return _coerce_optional_date(value, code="BASELINE_DATE_INVALID")

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> str:
        return normalize_optional_text(value)

    @model_validator(mode="after")
    def _validate_lifecycle_metadata(self) -> "ProjectBaseline":
        if self.status in {
            BaselineStatus.SUBMITTED,
            BaselineStatus.APPROVED,
            BaselineStatus.REJECTED,
            BaselineStatus.SUPERSEDED,
        } and (self.submitted_by is None or self.submitted_at is None):
            raise ValidationError(
                "Submitted baselines require submitter and submitted date.",
                code="BASELINE_SUBMISSION_METADATA_REQUIRED",
            )
        if self.status in {BaselineStatus.APPROVED, BaselineStatus.SUPERSEDED} and (
            self.approved_by is None or self.approved_at is None
        ):
            raise ValidationError(
                "Approved baselines require approver and approval date.",
                code="BASELINE_APPROVAL_METADATA_REQUIRED",
            )
        if (
            self.submitted_at is not None
            and self.approved_at is not None
            and self.approved_at < self.submitted_at
        ):
            raise ValidationError(
                "Baseline approval date cannot be before the submitted date.",
                code="BASELINE_APPROVAL_DATE_INVALID",
            )
        return self

    def _apply_validated_changes(self, **changes: object) -> None:
        candidate = replace(self, **changes)
        for field_name in self.__dataclass_fields__:
            object.__setattr__(self, field_name, getattr(candidate, field_name))

    @property
    def can_submit(self) -> bool:
        return self.status == BaselineStatus.DRAFT

    @property
    def can_approve(self) -> bool:
        return self.status == BaselineStatus.SUBMITTED

    @property
    def can_reject(self) -> bool:
        return self.status == BaselineStatus.SUBMITTED

    @staticmethod
    def create(project_id: str, name: str) -> "ProjectBaseline":
        return ProjectBaseline(
            id=generate_id(),
            project_id=project_id,
            name=name.strip() or "Baseline",
            created_at=date.today(),
            status=BaselineStatus.DRAFT,
            version=1,
        )

    def submit(self, submitted_by: str, notes: str = "") -> None:
        if not self.can_submit:
            raise ValidationError(
                f"Cannot submit baseline in status '{self.status.value}'.",
                code="BASELINE_SUBMIT_STATUS_INVALID",
            )
        changes: dict[str, object] = {
            "status": BaselineStatus.SUBMITTED,
            "submitted_by": submitted_by,
            "submitted_at": date.today(),
        }
        normalized_notes = normalize_optional_text(notes)
        if normalized_notes:
            changes["notes"] = normalized_notes
        self._apply_validated_changes(**changes)

    def approve(self, approved_by: str, notes: str = "") -> None:
        if not self.can_approve:
            raise ValidationError(
                f"Cannot approve baseline in status '{self.status.value}'.",
                code="BASELINE_APPROVE_STATUS_INVALID",
            )
        changes: dict[str, object] = {
            "status": BaselineStatus.APPROVED,
            "approved_by": approved_by,
            "approved_at": date.today(),
        }
        normalized_notes = normalize_optional_text(notes)
        if normalized_notes:
            changes["notes"] = normalized_notes
        self._apply_validated_changes(**changes)

    def reject(self, notes: str = "") -> None:
        if not self.can_reject:
            raise ValidationError(
                f"Cannot reject baseline in status '{self.status.value}'.",
                code="BASELINE_REJECT_STATUS_INVALID",
            )
        changes: dict[str, object] = {"status": BaselineStatus.REJECTED}
        normalized_notes = normalize_optional_text(notes)
        if normalized_notes:
            changes["notes"] = normalized_notes
        self._apply_validated_changes(**changes)

    def supersede(self) -> None:
        if self.status != BaselineStatus.APPROVED:
            raise ValidationError(
                f"Cannot supersede baseline in status '{self.status.value}'.",
                code="BASELINE_SUPERSEDE_STATUS_INVALID",
            )
        self._apply_validated_changes(status=BaselineStatus.SUPERSEDED)


@validated_dataclass
class BaselineTask:
    id: str
    baseline_id: str
    task_id: str
    task_name: str | None
    baseline_start: date | None
    baseline_finish: date | None
    baseline_duration_days: int
    baseline_planned_cost: float = 0.0

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Baseline task ID is required.",
            code="BASELINE_TASK_ID_REQUIRED",
        )

    @field_validator("baseline_id", mode="before")
    @classmethod
    def _validate_baseline_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Baseline ID is required.",
            code="BASELINE_TASK_BASELINE_REQUIRED",
        )

    @field_validator("task_id", mode="before")
    @classmethod
    def _validate_task_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Task ID is required.",
            code="BASELINE_TASK_TASK_REQUIRED",
        )

    @field_validator("task_name", mode="before")
    @classmethod
    def _normalize_task_name(cls, value: object) -> str | None:
        return _coerce_optional_text(value)

    @field_validator("baseline_start", "baseline_finish", mode="before")
    @classmethod
    def _validate_optional_dates(cls, value: object) -> date | None:
        return _coerce_optional_date(value, code="BASELINE_TASK_DATE_INVALID")

    @field_validator("baseline_duration_days", mode="before")
    @classmethod
    def _validate_duration(cls, value: object) -> int:
        return _coerce_non_negative_int(
            value,
            message="Baseline task duration must be zero or greater.",
            code="BASELINE_TASK_DURATION_INVALID",
        )

    @field_validator("baseline_planned_cost", mode="before")
    @classmethod
    def _validate_planned_cost(cls, value: object) -> float:
        return _coerce_non_negative_float(
            value,
            message="Baseline planned cost cannot be negative.",
            code="BASELINE_TASK_PLANNED_COST_INVALID",
        )

    @model_validator(mode="after")
    def _validate_date_range(self) -> "BaselineTask":
        if (
            self.baseline_start is not None
            and self.baseline_finish is not None
            and self.baseline_finish < self.baseline_start
        ):
            raise ValidationError(
                "Baseline finish date cannot be before the start date.",
                code="BASELINE_TASK_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        baseline_id: str,
        task_id: str,
        task_name: str | None,
        baseline_start: date | None,
        baseline_finish: date | None,
        baseline_duration_days: int,
        baseline_planned_cost: float,
    ) -> "BaselineTask":
        return BaselineTask(
            id=generate_id(),
            baseline_id=baseline_id,
            task_id=task_id,
            task_name=task_name,
            baseline_start=baseline_start,
            baseline_finish=baseline_finish,
            baseline_duration_days=baseline_duration_days,
            baseline_planned_cost=baseline_planned_cost,
        )


@validated_dataclass
class BaselineVarianceRecord:
    """
    Per-task variance snapshot created when a new baseline is approved.

    Compares each task's dates and cost in the new baseline against the
    superseded approved baseline, providing a permanent audit trail of
    how the plan has shifted over time.
    """
    id: str
    project_id: str
    new_baseline_id: str
    superseded_baseline_id: str
    task_id: str
    task_name: str | None
    start_variance_days: int    # (new_start - old_start).days; positive = later
    finish_variance_days: int   # (new_finish - old_finish).days
    cost_variance: float        # new_planned_cost - old_planned_cost
    created_at: date

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Baseline variance record ID is required.",
            code="BASELINE_VARIANCE_ID_REQUIRED",
        )

    @field_validator("project_id", mode="before")
    @classmethod
    def _validate_project_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Project ID is required.",
            code="BASELINE_VARIANCE_PROJECT_REQUIRED",
        )

    @field_validator("new_baseline_id", mode="before")
    @classmethod
    def _validate_new_baseline_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="New baseline ID is required.",
            code="BASELINE_VARIANCE_NEW_BASELINE_REQUIRED",
        )

    @field_validator("superseded_baseline_id", mode="before")
    @classmethod
    def _validate_superseded_baseline_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Superseded baseline ID is required.",
            code="BASELINE_VARIANCE_SUPERSEDED_BASELINE_REQUIRED",
        )

    @field_validator("task_id", mode="before")
    @classmethod
    def _validate_task_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Task ID is required.",
            code="BASELINE_VARIANCE_TASK_REQUIRED",
        )

    @field_validator("task_name", mode="before")
    @classmethod
    def _normalize_task_name(cls, value: object) -> str | None:
        return _coerce_optional_text(value)

    @field_validator("start_variance_days", mode="before")
    @classmethod
    def _validate_start_variance_days(cls, value: object) -> int:
        try:
            return int(value if value not in (None, "") else 0)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Start variance days must be a whole number.",
                code="BASELINE_VARIANCE_START_DAYS_INVALID",
            ) from exc

    @field_validator("finish_variance_days", mode="before")
    @classmethod
    def _validate_finish_variance_days(cls, value: object) -> int:
        try:
            return int(value if value not in (None, "") else 0)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Finish variance days must be a whole number.",
                code="BASELINE_VARIANCE_FINISH_DAYS_INVALID",
            ) from exc

    @field_validator("cost_variance", mode="before")
    @classmethod
    def _validate_cost_variance(cls, value: object) -> float:
        return _coerce_float(
            value,
            message="Cost variance must be numeric.",
            code="BASELINE_VARIANCE_COST_INVALID",
        )

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: object) -> date:
        return _coerce_required_date(
            value,
            message="Variance record creation date is required.",
            code="BASELINE_VARIANCE_CREATED_AT_INVALID",
        )

    @staticmethod
    def create(
        project_id: str,
        new_baseline_id: str,
        superseded_baseline_id: str,
        task_id: str,
        task_name: str | None,
        start_variance_days: int,
        finish_variance_days: int,
        cost_variance: float,
    ) -> "BaselineVarianceRecord":
        return BaselineVarianceRecord(
            id=generate_id(),
            project_id=project_id,
            new_baseline_id=new_baseline_id,
            superseded_baseline_id=superseded_baseline_id,
            task_id=task_id,
            task_name=task_name,
            start_variance_days=start_variance_days,
            finish_variance_days=finish_variance_days,
            cost_variance=cost_variance,
            created_at=date.today(),
        )


__all__ = [
    "BaselineStatus",
    "BaselineVarianceRecord",
    "BaselineTask",
    "ProjectBaseline",
]
