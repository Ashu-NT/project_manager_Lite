"""Versioned, computed labor-planned-cost snapshots.

Provides task-level planned-cost visibility from the current state of
``TaskAssignment.allocated_planned_hours``/``ProjectResource.planned_hours``. This is
NOT an approved labor-planning baseline and must not be treated as one by EVM or
financial posting workflows -- nothing here is submitted for review or approved by a
second principal; a snapshot is a computed fact, recalculated on demand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import field_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.finance.money.currency import CurrencyCode


class PlannedCostVersionStatus(str, Enum):
    CURRENT = "current"
    SUPERSEDED = "superseded"


# Resource-allocation diagnostic reason codes (ResourceAllocationDiagnostic).
PLANNED_HOURS_FULLY_ALLOCATED = "PLANNED_HOURS_FULLY_ALLOCATED"
PLANNED_HOURS_PARTIALLY_ALLOCATED = "PLANNED_HOURS_PARTIALLY_ALLOCATED"
PLANNED_HOURS_OVERALLOCATED = "PLANNED_HOURS_OVERALLOCATED"
PROJECT_RESOURCE_ENVELOPE_MISSING = "PROJECT_RESOURCE_ENVELOPE_MISSING"

# Line-exclusion diagnostic reason codes (returned alongside a snapshot,
# not persisted — see PlannedCostService.calculate_snapshot).
PLANNED_COST_RATE_NOT_FOUND = "PLANNED_COST_RATE_NOT_FOUND"
PLANNED_COST_CURRENCY_MISMATCH = "PLANNED_COST_CURRENCY_MISMATCH"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_timestamp(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("A valid timestamp is required.", code=code)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _required_identifier(value: object, *, label: str, code: str) -> str:
    return normalize_required_text(value, message=f"{label} is required.", code=code)


@dataclass(frozen=True, slots=True)
class ResourceAllocationDiagnostic:
    """Transient, computed-at-calculation-time diagnostic"""

    project_resource_id: str
    resource_id: str
    envelope_hours: Decimal
    allocated_hours: Decimal
    unallocated_hours: Decimal
    reason_code: str


@validated_dataclass
class ProjectPlannedCostVersion:
    """One versioned, computed labor-planned-cost snapshot for a project.

    No DRAFT/SUBMIT/APPROVE lifecycle -- a snapshot is either ``CURRENT`` or
    ``SUPERSEDED`` by a newer one. ``revision`` is the calculation number, assigned once;
    ``row_version`` is a separate optimistic-concurrency token that advances only when
    superseded.

    Completeness is tracked as three independent flags, since a snapshot can have fully
    resolved rates while still reporting incomplete allocation:

    - ``rates_complete``: every eligible assignment's resource rate resolved in the
      project's currency.
    - ``allocations_complete``: every ``ProjectResource`` envelope with hours is fully
      distributed across its assignments, none overallocated or missing.
    - ``cost_codes_complete``: every line has a resolved cost code (always ``True`` in
      this tactical slice once the default-cost-code gate passes -- see
      ``unclassified_line_count``).
    """

    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    revision: int = 1
    status: PlannedCostVersionStatus = PlannedCostVersionStatus.CURRENT
    currency_code: str = ""
    as_of: date = field(default_factory=lambda: datetime.now(timezone.utc).date())
    calculated_by: str = ""
    calculated_at: datetime = field(default_factory=_utc_now)
    rates_complete: bool = True
    allocations_complete: bool = True
    cost_codes_complete: bool = True
    unresolved_rate_count: int = 0
    partially_allocated_resource_count: int = 0
    # Always 0 in this tactical slice (see cost_codes_complete above). Kept as a real
    # field so a future per-task cost-code source can populate it without a schema change.
    unclassified_line_count: int = 0
    superseded_by: str | None = None
    superseded_at: datetime | None = None
    row_version: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator("id", "tenant_id", "organization_id", "project_id", mode="before")
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return _required_identifier(
            value,
            label=info.field_name.replace("_", " ").title(),
            code=f"PLANNED_COST_VERSION_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("calculated_by", mode="before")
    @classmethod
    def _validate_calculated_by(cls, value: object) -> str:
        return _required_identifier(
            value,
            label="Calculated by",
            code="PLANNED_COST_VERSION_CALCULATED_BY_REQUIRED",
        )

    @field_validator("currency_code", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("superseded_by", mode="before")
    @classmethod
    def _normalize_superseded_by(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("revision", "row_version", mode="before")
    @classmethod
    def _validate_positive_int(cls, value: object, info) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                f"Planned-cost version {info.field_name.replace('_', ' ')} must be positive.",
                code=f"PLANNED_COST_VERSION_{info.field_name.upper()}_INVALID",
            )
        return resolved

    @field_validator(
        "unresolved_rate_count",
        "partially_allocated_resource_count",
        "unclassified_line_count",
        mode="before",
    )
    @classmethod
    def _validate_nonnegative_count(cls, value: object, info) -> int:
        resolved = int(value or 0)
        if resolved < 0:
            raise ValidationError(
                f"Planned-cost version {info.field_name.replace('_', ' ')} cannot be negative.",
                code=f"PLANNED_COST_VERSION_{info.field_name.upper()}_INVALID",
            )
        return resolved

    @field_validator("superseded_at", mode="before")
    @classmethod
    def _validate_superseded_at(cls, value: object) -> datetime | None:
        if value is None:
            return None
        return _normalize_timestamp(
            value, code="PLANNED_COST_VERSION_SUPERSEDED_AT_INVALID"
        )

    @field_validator("calculated_at", "created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime:
        return _normalize_timestamp(
            value,
            code=f"PLANNED_COST_VERSION_{info.field_name.upper()}_INVALID",
        )

    def supersede(self, *, superseded_by: str, superseded_at: datetime) -> None:
        if self.status != PlannedCostVersionStatus.CURRENT:
            raise BusinessRuleError(
                "Only the current planned-cost version can be superseded.",
                code="PLANNED_COST_VERSION_SUPERSEDE_STATUS_INVALID",
            )
        self.status = PlannedCostVersionStatus.SUPERSEDED
        self.superseded_by = superseded_by
        self.superseded_at = superseded_at
        self.updated_at = superseded_at

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        currency_code: str,
        as_of: date,
        calculated_by: str,
        calculated_at: datetime | None = None,
        revision: int = 1,
        **values,
    ) -> "ProjectPlannedCostVersion":
        now = calculated_at or _utc_now()
        return ProjectPlannedCostVersion(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            currency_code=currency_code,
            as_of=as_of,
            calculated_by=calculated_by,
            calculated_at=now,
            revision=revision,
            created_at=now,
            updated_at=now,
            **values,
        )


@validated_dataclass
class ProjectPlannedCostLine:
    """One resource+task planned-labor line within a snapshot version.

    Write-once: unlike ``BudgetLine``, never individually updated or deleted after its
    version is calculated -- only a new snapshot calculation changes its contents.

    ``source_assignment_id`` is an immutable, snapshotted identifier, not a live foreign
    key -- the line's hours/rate/amount/currency are already self-contained, so deleting
    the operational ``TaskAssignment`` later must not be blocked or erase provenance.
    """

    id: str
    tenant_id: str
    organization_id: str
    version_id: str
    project_id: str
    task_id: str
    resource_id: str
    project_resource_id: str
    cost_code_id: str
    source_assignment_id: str
    planned_hours: Decimal = Decimal("0")
    rate_amount: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")
    currency_code: str = ""
    rate_card_id: str = ""
    rate_line_id: str = ""
    rate_card_version: int = 1
    rate_line_version: int | None = None
    rate_modifier: str | None = None
    rate_modifier_multiplier: Decimal | None = None
    created_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "version_id", "project_id",
        "task_id", "resource_id", "project_resource_id", "cost_code_id",
        "source_assignment_id",
        mode="before",
    )
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return _required_identifier(
            value,
            label=info.field_name.replace("_", " ").title(),
            code=f"PLANNED_COST_LINE_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("currency_code", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("planned_hours", "rate_amount", "amount", mode="before")
    @classmethod
    def _validate_decimal_nonnegative(cls, value: object, info) -> Decimal:
        resolved = Decimal(str(value if value not in (None, "") else "0"))
        if resolved < 0:
            raise ValidationError(
                f"Planned-cost line {info.field_name} cannot be negative.",
                code=f"PLANNED_COST_LINE_{info.field_name.upper()}_INVALID",
            )
        return resolved

    @field_validator("rate_card_version", mode="before")
    @classmethod
    def _validate_rate_card_version(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                "Planned-cost line rate_card_version must be positive.",
                code="PLANNED_COST_LINE_RATE_CARD_VERSION_INVALID",
            )
        return resolved

    @field_validator("rate_line_version", mode="before")
    @classmethod
    def _validate_rate_line_version(cls, value: object) -> int | None:
        if value is None:
            return None
        resolved = int(value)
        if resolved < 1:
            raise ValidationError(
                "Planned-cost line rate_line_version must be positive.",
                code="PLANNED_COST_LINE_RATE_LINE_VERSION_INVALID",
            )
        return resolved

    @field_validator("rate_modifier", mode="before")
    @classmethod
    def _normalize_rate_modifier(cls, value: object) -> str | None:
        normalized = str(value or "").strip().lower()
        return normalized or None

    @field_validator("rate_modifier_multiplier", mode="before")
    @classmethod
    def _validate_modifier_multiplier(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        resolved = Decimal(str(value))
        if resolved < 0:
            raise ValidationError(
                "Planned-cost rate modifier cannot be negative.",
                code="PLANNED_COST_LINE_RATE_MODIFIER_INVALID",
            )
        return resolved

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: object) -> datetime:
        return _normalize_timestamp(
            value, code="PLANNED_COST_LINE_CREATED_AT_INVALID"
        )

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        version_id: str,
        project_id: str,
        task_id: str,
        resource_id: str,
        project_resource_id: str,
        cost_code_id: str,
        source_assignment_id: str,
        planned_hours: Decimal,
        rate_amount: Decimal,
        amount: Decimal,
        currency_code: str,
        created_at: datetime | None = None,
        **values,
    ) -> "ProjectPlannedCostLine":
        now = created_at or _utc_now()
        return ProjectPlannedCostLine(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            version_id=version_id,
            project_id=project_id,
            task_id=task_id,
            resource_id=resource_id,
            project_resource_id=project_resource_id,
            cost_code_id=cost_code_id,
            source_assignment_id=source_assignment_id,
            planned_hours=planned_hours,
            rate_amount=rate_amount,
            amount=amount,
            currency_code=currency_code,
            created_at=now,
            **values,
        )


__all__ = [
    "PLANNED_COST_CURRENCY_MISMATCH",
    "PLANNED_COST_RATE_NOT_FOUND",
    "PLANNED_HOURS_FULLY_ALLOCATED",
    "PLANNED_HOURS_OVERALLOCATED",
    "PLANNED_HOURS_PARTIALLY_ALLOCATED",
    "PROJECT_RESOURCE_ENVELOPE_MISSING",
    "PlannedCostVersionStatus",
    "ProjectPlannedCostLine",
    "ProjectPlannedCostVersion",
    "ResourceAllocationDiagnostic",
]
