from __future__ import annotations

from dataclasses import field
from datetime import datetime, timezone
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
from src.core.platform.finance.money.money import Money


class BudgetStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    CLOSED = "closed"


_ALLOWED_TRANSITIONS: dict[BudgetStatus, frozenset[BudgetStatus]] = {
    BudgetStatus.DRAFT: frozenset({BudgetStatus.SUBMITTED}),
    BudgetStatus.SUBMITTED: frozenset({BudgetStatus.APPROVED, BudgetStatus.REJECTED}),
    BudgetStatus.APPROVED: frozenset({BudgetStatus.SUPERSEDED, BudgetStatus.CLOSED}),
    BudgetStatus.REJECTED: frozenset(),
    BudgetStatus.SUPERSEDED: frozenset(),
    BudgetStatus.CLOSED: frozenset(),
}


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


def _require_transition(
    current: BudgetStatus, target: BudgetStatus, *, code: str
) -> None:
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise BusinessRuleError(
            f"Budget cannot transition from {current.value} to {target.value}.",
            code=code,
        )


@validated_dataclass
class ProjectBudget:
    """One versioned iteration of a project's budget authorization.

    ``revision`` is the business version within the project (v1, v2, v3...)
    — assigned once at creation and never changed afterward; a rejected or
    superseded iteration is never revised in place, only replaced by a new
    ``ProjectBudget`` row with the next revision. ``row_version`` is a
    separate, plain optimistic-concurrency token that increments on every
    field-level update (including line mutations against this budget — see
    ``touch()``). These two numbers must never be conflated: updating this
    budget's name must not change which "version" it represents.
    """

    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    name: str
    currency_code: str
    status: BudgetStatus = BudgetStatus.DRAFT
    revision: int = 1
    row_version: int = 1
    submitted_by: str | None = None
    submitted_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    superseded_by: str | None = None
    superseded_at: datetime | None = None
    closed_by: str | None = None
    closed_at: datetime | None = None
    notes: str = ""
    submission_notes: str = ""
    approval_notes: str = ""
    rejection_notes: str = ""
    closure_notes: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator("id", "tenant_id", "organization_id", "project_id", mode="before")
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return _required_identifier(
            value,
            label=info.field_name.replace("_", " ").title(),
            code=f"PROJECT_BUDGET_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Budget name is required.",
            code="PROJECT_BUDGET_NAME_REQUIRED",
        )

    @field_validator("currency_code", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator(
        "submitted_by", "approved_by", "rejected_by", "superseded_by", "closed_by",
        mode="before",
    )
    @classmethod
    def _normalize_optional_actor(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("revision", "row_version", mode="before")
    @classmethod
    def _validate_positive_int(cls, value: object, info) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                f"Budget {info.field_name.replace('_', ' ')} must be positive.",
                code=f"PROJECT_BUDGET_{info.field_name.upper()}_INVALID",
            )
        return resolved

    @field_validator(
        "submitted_at", "approved_at", "rejected_at", "superseded_at", "closed_at",
        mode="before",
    )
    @classmethod
    def _validate_optional_timestamps(cls, value: object, info) -> datetime | None:
        if value is None:
            return None
        return _normalize_timestamp(
            value,
            code=f"PROJECT_BUDGET_{info.field_name.upper()}_INVALID",
        )

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime:
        return _normalize_timestamp(
            value,
            code=f"PROJECT_BUDGET_{info.field_name.upper()}_INVALID",
        )

    @property
    def is_mutable(self) -> bool:
        return self.status == BudgetStatus.DRAFT

    def ensure_mutable(self) -> None:
        """Only DRAFT is mutable — SUBMITTED is frozen too. A reviewer who
        wants changes rejects it; the next iteration is a new DRAFT
        revision, never a reopen. Unlike ``ProjectBaseline``, which never
        enforces this structurally, this is a real, testable guard."""
        if not self.is_mutable:
            raise BusinessRuleError(
                f"Budget cannot be modified in status '{self.status.value}'.",
                code="PROJECT_BUDGET_IMMUTABLE",
            )

    def rename(self, name: str) -> None:
        self.name = name

    def update_notes(self, notes: str) -> None:
        self.notes = notes

    def touch(self, *, updated_at: datetime) -> None:
        """Marks the aggregate root as changed with no status transition —
        called by every ``BudgetLine`` mutation so the parent's
        ``row_version`` advances alongside its lines, closing the race
        where a concurrent submit and a final-line deletion could
        otherwise both succeed against stale, non-conflicting versions."""
        self.updated_at = updated_at

    def submit(
        self, *, submitted_by: str, submitted_at: datetime, notes: str = ""
    ) -> None:
        _require_transition(
            self.status, BudgetStatus.SUBMITTED,
            code="PROJECT_BUDGET_SUBMIT_STATUS_INVALID",
        )
        self.status = BudgetStatus.SUBMITTED
        self.submitted_by = submitted_by
        self.submitted_at = submitted_at
        self.submission_notes = notes
        self.updated_at = submitted_at

    def approve(
        self, *, approved_by: str, approved_at: datetime, notes: str = ""
    ) -> None:
        _require_transition(
            self.status, BudgetStatus.APPROVED,
            code="PROJECT_BUDGET_APPROVE_STATUS_INVALID",
        )
        self.status = BudgetStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = approved_at
        self.approval_notes = notes
        self.updated_at = approved_at

    def reject(
        self, *, rejected_by: str, rejected_at: datetime, notes: str = ""
    ) -> None:
        _require_transition(
            self.status, BudgetStatus.REJECTED,
            code="PROJECT_BUDGET_REJECT_STATUS_INVALID",
        )
        self.status = BudgetStatus.REJECTED
        self.rejected_by = rejected_by
        self.rejected_at = rejected_at
        self.rejection_notes = notes
        self.updated_at = rejected_at

    def supersede(self, *, superseded_by: str, superseded_at: datetime) -> None:
        _require_transition(
            self.status, BudgetStatus.SUPERSEDED,
            code="PROJECT_BUDGET_SUPERSEDE_STATUS_INVALID",
        )
        self.status = BudgetStatus.SUPERSEDED
        self.superseded_by = superseded_by
        self.superseded_at = superseded_at
        self.updated_at = superseded_at

    def close(self, *, closed_by: str, closed_at: datetime, notes: str = "") -> None:
        _require_transition(
            self.status, BudgetStatus.CLOSED,
            code="PROJECT_BUDGET_CLOSE_STATUS_INVALID",
        )
        self.status = BudgetStatus.CLOSED
        self.closed_by = closed_by
        self.closed_at = closed_at
        self.closure_notes = notes
        self.updated_at = closed_at

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        name: str,
        currency_code: str,
        revision: int = 1,
        created_at: datetime | None = None,
        **values,
    ) -> "ProjectBudget":
        now = created_at or _utc_now()
        return ProjectBudget(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            name=name,
            currency_code=currency_code,
            revision=revision,
            created_at=now,
            updated_at=now,
            **values,
        )


@validated_dataclass
class BudgetLine:
    id: str
    tenant_id: str
    organization_id: str
    budget_id: str
    project_id: str
    cost_code_id: str
    task_id: str | None = None
    description: str = ""
    amount: Decimal = Decimal("0")
    currency_code: str = ""
    row_version: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "budget_id", "project_id",
        "cost_code_id",
        mode="before",
    )
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return _required_identifier(
            value,
            label=info.field_name.replace("_", " ").title(),
            code=f"PROJECT_BUDGET_LINE_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("task_id", mode="before")
    @classmethod
    def _normalize_task_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("currency_code", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("amount", mode="before")
    @classmethod
    def _validate_amount(cls, value: object) -> Decimal:
        resolved = Decimal(str(value if value not in (None, "") else "0"))
        if resolved < 0:
            raise ValidationError(
                "Budget line amount cannot be negative.",
                code="PROJECT_BUDGET_LINE_AMOUNT_INVALID",
            )
        return resolved

    @field_validator("row_version", mode="before")
    @classmethod
    def _validate_row_version(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                "Budget line row version must be positive.",
                code="PROJECT_BUDGET_LINE_ROW_VERSION_INVALID",
            )
        return resolved

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime:
        return _normalize_timestamp(
            value,
            code=f"PROJECT_BUDGET_LINE_{info.field_name.upper()}_INVALID",
        )

    @property
    def money(self) -> Money:
        return Money.of(self.amount, self.currency_code)

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        budget_id: str,
        project_id: str,
        cost_code_id: str,
        amount: Decimal,
        currency_code: str,
        created_at: datetime | None = None,
        **values,
    ) -> "BudgetLine":
        now = created_at or _utc_now()
        return BudgetLine(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            budget_id=budget_id,
            project_id=project_id,
            cost_code_id=cost_code_id,
            amount=amount,
            currency_code=currency_code,
            created_at=now,
            updated_at=now,
            **values,
        )


__all__ = ["BudgetLine", "BudgetStatus", "ProjectBudget"]
