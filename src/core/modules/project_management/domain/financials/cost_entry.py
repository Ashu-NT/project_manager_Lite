from __future__ import annotations

from dataclasses import field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceReference,
    FinancialSourceType,
)
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.finance import (
    EXCHANGE_RATE_STORAGE,
    MONEY_STORAGE,
    CurrencyCode,
    Money,
)


class ProjectCostEntryStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    POSTED = "posted"
    REVERSED = "reversed"


class ProjectCostEntryKind(str, Enum):
    ACTUAL = "actual"
    ADJUSTMENT = "adjustment"
    REVERSAL = "reversal"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _required_identifier(value: object, *, field_name: str) -> str:
    return normalize_required_text(
        value,
        message=f"{field_name.replace('_', ' ').title()} is required.",
        code=f"PROJECT_COST_ENTRY_{field_name.upper()}_REQUIRED",
    )


def _aware_utc(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(
            f"{field_name.replace('_', ' ').title()} must be a valid timestamp.",
            code=f"PROJECT_COST_ENTRY_{field_name.upper()}_INVALID",
        )
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@validated_dataclass
class ProjectCostEntry:
    """Canonical signed actual-cost ledger entry.

    Draft entries may be edited. Submission freezes their financial facts;
    posting captures the accounting period and base-currency conversion.
    Posted entries are corrected only by an equal, opposite reversal entry.
    """

    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    description: str
    entry_kind: ProjectCostEntryKind
    amount: Decimal
    currency_code: str
    transaction_date: date
    cost_code_id: str
    source_module: FinancialSourceModule
    source_type: FinancialSourceType
    source_id: str
    source_revision: str
    source_content_hash: str
    posting_purpose: FinancialPostingPurpose
    idempotency_key: str
    source_line_id: str | None = None
    task_id: str | None = None
    resource_id: str | None = None
    status: ProjectCostEntryStatus = ProjectCostEntryStatus.DRAFT
    base_amount: Decimal | None = None
    base_currency_code: str | None = None
    exchange_rate: Decimal | None = None
    exchange_rate_date: date | None = None
    exchange_rate_source: str | None = None
    exchange_rate_captured_at: datetime | None = None
    posting_date: date | None = None
    financial_period_id: str | None = None
    reverses_entry_id: str | None = None
    reversed_by_entry_id: str | None = None
    row_version: int = 1
    created_by: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    updated_by: str = ""
    updated_at: datetime = field(default_factory=_utc_now)
    submitted_by: str | None = None
    submitted_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    rejection_notes: str = ""
    posted_by: str | None = None
    posted_at: datetime | None = None
    reversed_by: str | None = None
    reversed_at: datetime | None = None

    @field_validator(
        "id",
        "tenant_id",
        "organization_id",
        "project_id",
        "cost_code_id",
        "source_id",
        "source_revision",
        "idempotency_key",
        "created_by",
        "updated_by",
        mode="before",
    )
    @classmethod
    def _validate_required_identifiers(cls, value: object, info) -> str:
        return _required_identifier(value, field_name=info.field_name)

    @field_validator(
        "source_line_id",
        "task_id",
        "resource_id",
        "financial_period_id",
        "reverses_entry_id",
        "reversed_by_entry_id",
        "submitted_by",
        "approved_by",
        "rejected_by",
        "posted_by",
        "reversed_by",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("description", mode="before")
    @classmethod
    def _validate_description(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Cost entry description is required.",
            code="PROJECT_COST_ENTRY_DESCRIPTION_REQUIRED",
        )

    @field_validator("exchange_rate_source", mode="before")
    @classmethod
    def _normalize_rate_source(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("rejection_notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("amount", mode="before")
    @classmethod
    def _validate_amount(cls, value: object) -> Decimal:
        return MONEY_STORAGE.validate(value)

    @field_validator("base_amount", mode="before")
    @classmethod
    def _validate_base_amount(cls, value: object) -> Decimal | None:
        return None if value is None else MONEY_STORAGE.validate(value)

    @field_validator("exchange_rate", mode="before")
    @classmethod
    def _validate_exchange_rate(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        rate = EXCHANGE_RATE_STORAGE.validate(value)
        if rate <= 0:
            raise ValidationError(
                "Exchange rate must be positive.",
                code="PROJECT_COST_ENTRY_EXCHANGE_RATE_INVALID",
            )
        return rate

    @field_validator("currency_code", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("base_currency_code", mode="before")
    @classmethod
    def _validate_optional_currency(cls, value: object) -> str | None:
        if value is None or not str(value).strip():
            return None
        currency = CurrencyCode(str(value))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("row_version", mode="before")
    @classmethod
    def _validate_row_version(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                "Cost entry row version must be positive.",
                code="PROJECT_COST_ENTRY_ROW_VERSION_INVALID",
            )
        return resolved

    @field_validator(
        "created_at",
        "updated_at",
        "submitted_at",
        "approved_at",
        "rejected_at",
        "exchange_rate_captured_at",
        "posted_at",
        "reversed_at",
        mode="before",
    )
    @classmethod
    def _normalize_timestamps(cls, value: object, info) -> datetime | None:
        if value is None and info.field_name not in {"created_at", "updated_at"}:
            return None
        return _aware_utc(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _validate_ledger_invariants(self) -> "ProjectCostEntry":
        self._validate_sign_and_reversal()
        self._validate_source_reference()
        self._validate_posting_snapshot()
        return self

    @property
    def money(self) -> Money:
        return Money.of(self.amount, self.currency_code)

    @property
    def base_money(self) -> Money | None:
        if self.base_amount is None or self.base_currency_code is None:
            return None
        return Money.of(self.base_amount, self.base_currency_code)

    @property
    def source_reference(self) -> FinancialSourceReference:
        return FinancialSourceReference(
            tenant_id=self.tenant_id,
            organization_id=self.organization_id,
            project_id=self.project_id,
            source_module=self.source_module,
            source_type=self.source_type,
            source_id=self.source_id,
            source_line_id=self.source_line_id,
            source_revision=self.source_revision,
            content_hash=self.source_content_hash,
            posting_purpose=self.posting_purpose,
        )

    @property
    def is_draft(self) -> bool:
        return self.status == ProjectCostEntryStatus.DRAFT

    def update_draft(
        self,
        *,
        description: str,
        amount: Decimal,
        currency_code: str,
        transaction_date: date,
        cost_code_id: str,
        task_id: str | None,
        resource_id: str | None,
        source_content_hash: str,
        updated_by: str,
        updated_at: datetime,
    ) -> None:
        self._require_status(ProjectCostEntryStatus.DRAFT, code="PROJECT_COST_ENTRY_NOT_DRAFT")
        candidate = ProjectCostEntry(
            **{
                **self.__dict__,
                "description": description,
                "amount": amount,
                "currency_code": currency_code,
                "transaction_date": transaction_date,
                "cost_code_id": cost_code_id,
                "task_id": task_id,
                "resource_id": resource_id,
                "source_content_hash": source_content_hash,
                "updated_by": updated_by,
                "updated_at": updated_at,
            }
        )
        self._copy_from(candidate)

    def submit(self, *, actor_id: str, occurred_at: datetime) -> None:
        self._require_status(ProjectCostEntryStatus.DRAFT, code="PROJECT_COST_ENTRY_SUBMIT_INVALID")
        self.status = ProjectCostEntryStatus.SUBMITTED
        self.submitted_by = actor_id
        self.submitted_at = occurred_at
        self.updated_by = actor_id
        self.updated_at = occurred_at

    def approve(self, *, actor_id: str, occurred_at: datetime) -> None:
        self._require_status(
            ProjectCostEntryStatus.SUBMITTED,
            code="PROJECT_COST_ENTRY_APPROVE_INVALID",
        )
        self.status = ProjectCostEntryStatus.APPROVED
        self.approved_by = actor_id
        self.approved_at = occurred_at
        self.updated_by = actor_id
        self.updated_at = occurred_at

    def reject(self, *, actor_id: str, occurred_at: datetime, notes: str = "") -> None:
        self._require_status(
            ProjectCostEntryStatus.SUBMITTED,
            code="PROJECT_COST_ENTRY_REJECT_INVALID",
        )
        self.status = ProjectCostEntryStatus.DRAFT
        self.rejected_by = actor_id
        self.rejected_at = occurred_at
        self.rejection_notes = notes
        self.updated_by = actor_id
        self.updated_at = occurred_at

    def post(
        self,
        *,
        actor_id: str,
        occurred_at: datetime,
        posting_date: date,
        financial_period_id: str,
        base_money: Money,
        exchange_rate: Decimal,
        exchange_rate_date: date,
        exchange_rate_source: str,
        exchange_rate_captured_at: datetime,
    ) -> None:
        self._require_status(ProjectCostEntryStatus.APPROVED, code="PROJECT_COST_ENTRY_POST_INVALID")
        if base_money.amount.is_zero():
            raise BusinessRuleError(
                "Posted base amount cannot be zero.",
                code="PROJECT_COST_ENTRY_BASE_AMOUNT_ZERO",
            )
        candidate = ProjectCostEntry(
            **{
                **self.__dict__,
                "status": ProjectCostEntryStatus.POSTED,
                "base_amount": base_money.amount,
                "base_currency_code": base_money.currency.code,
                "exchange_rate": exchange_rate,
                "exchange_rate_date": exchange_rate_date,
                "exchange_rate_source": exchange_rate_source,
                "exchange_rate_captured_at": exchange_rate_captured_at,
                "posting_date": posting_date,
                "financial_period_id": financial_period_id,
                "posted_by": actor_id,
                "posted_at": occurred_at,
                "updated_by": actor_id,
                "updated_at": occurred_at,
            }
        )
        self._copy_from(candidate)

    def mark_reversed(
        self,
        *,
        reversal_entry_id: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> None:
        self._require_status(
            ProjectCostEntryStatus.POSTED,
            code="PROJECT_COST_ENTRY_REVERSE_INVALID",
        )
        if self.entry_kind == ProjectCostEntryKind.REVERSAL:
            raise BusinessRuleError(
                "A reversal entry cannot itself be reversed.",
                code="PROJECT_COST_ENTRY_REVERSAL_OF_REVERSAL_FORBIDDEN",
            )
        self.status = ProjectCostEntryStatus.REVERSED
        self.reversed_by_entry_id = reversal_entry_id
        self.reversed_by = actor_id
        self.reversed_at = occurred_at
        self.updated_by = actor_id
        self.updated_at = occurred_at

    @classmethod
    def create_draft(
        cls,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        description: str,
        kind: ProjectCostEntryKind,
        money: Money,
        transaction_date: date,
        cost_code_id: str,
        source: FinancialSourceReference,
        task_id: str | None,
        resource_id: str | None,
        actor_id: str,
        occurred_at: datetime,
    ) -> "ProjectCostEntry":
        if kind == ProjectCostEntryKind.REVERSAL:
            raise ValidationError(
                "Draft entries cannot be created as reversals.",
                code="PROJECT_COST_ENTRY_DRAFT_REVERSAL_FORBIDDEN",
            )
        return cls(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            description=description,
            entry_kind=kind,
            amount=money.amount,
            currency_code=money.currency.code,
            transaction_date=transaction_date,
            cost_code_id=cost_code_id,
            task_id=task_id,
            resource_id=resource_id,
            source_module=source.source_module,
            source_type=source.source_type,
            source_id=source.source_id,
            source_line_id=source.source_line_id,
            source_revision=source.source_revision,
            source_content_hash=source.content_hash,
            posting_purpose=source.posting_purpose,
            idempotency_key=source.idempotency_key,
            created_by=actor_id,
            created_at=occurred_at,
            updated_by=actor_id,
            updated_at=occurred_at,
        )

    @classmethod
    def create_posted_reversal(
        cls,
        *,
        original: "ProjectCostEntry",
        reversal_id: str,
        description: str,
        source: FinancialSourceReference,
        posting_date: date,
        financial_period_id: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> "ProjectCostEntry":
        if original.status != ProjectCostEntryStatus.POSTED:
            raise BusinessRuleError(
                "Only a posted cost entry can be reversed.",
                code="PROJECT_COST_ENTRY_REVERSE_INVALID",
            )
        if original.entry_kind == ProjectCostEntryKind.REVERSAL:
            raise BusinessRuleError(
                "A reversal entry cannot itself be reversed.",
                code="PROJECT_COST_ENTRY_REVERSAL_OF_REVERSAL_FORBIDDEN",
            )
        if original.base_amount is None:
            raise BusinessRuleError(
                "Posted original entry is missing its base amount.",
                code="PROJECT_COST_ENTRY_POSTING_SNAPSHOT_INCOMPLETE",
            )
        return cls(
            id=reversal_id,
            tenant_id=original.tenant_id,
            organization_id=original.organization_id,
            project_id=original.project_id,
            description=description,
            entry_kind=ProjectCostEntryKind.REVERSAL,
            amount=-original.amount,
            currency_code=original.currency_code,
            transaction_date=posting_date,
            cost_code_id=original.cost_code_id,
            task_id=original.task_id,
            resource_id=original.resource_id,
            source_module=source.source_module,
            source_type=source.source_type,
            source_id=source.source_id,
            source_line_id=source.source_line_id,
            source_revision=source.source_revision,
            source_content_hash=source.content_hash,
            posting_purpose=source.posting_purpose,
            idempotency_key=source.idempotency_key,
            status=ProjectCostEntryStatus.POSTED,
            base_amount=-original.base_amount,
            base_currency_code=original.base_currency_code,
            exchange_rate=original.exchange_rate,
            exchange_rate_date=original.exchange_rate_date,
            exchange_rate_source=original.exchange_rate_source,
            exchange_rate_captured_at=original.exchange_rate_captured_at,
            posting_date=posting_date,
            financial_period_id=financial_period_id,
            reverses_entry_id=original.id,
            created_by=actor_id,
            created_at=occurred_at,
            updated_by=actor_id,
            updated_at=occurred_at,
            approved_by=actor_id,
            approved_at=occurred_at,
            posted_by=actor_id,
            posted_at=occurred_at,
        )

    def _validate_sign_and_reversal(self) -> None:
        if self.entry_kind == ProjectCostEntryKind.ACTUAL and self.amount <= 0:
            raise ValidationError(
                "Actual cost amount must be positive.",
                code="PROJECT_COST_ENTRY_ACTUAL_AMOUNT_INVALID",
            )
        if self.entry_kind == ProjectCostEntryKind.ADJUSTMENT and self.amount == 0:
            raise ValidationError(
                "Adjustment amount cannot be zero.",
                code="PROJECT_COST_ENTRY_ADJUSTMENT_AMOUNT_INVALID",
            )
        if self.entry_kind == ProjectCostEntryKind.REVERSAL:
            if self.amount >= 0 or not self.reverses_entry_id:
                raise ValidationError(
                    "Reversal entries require a negative amount and an original entry.",
                    code="PROJECT_COST_ENTRY_REVERSAL_INVALID",
                )
        elif self.reverses_entry_id:
            raise ValidationError(
                "Only reversal entries may reference an original entry.",
                code="PROJECT_COST_ENTRY_REVERSAL_REFERENCE_INVALID",
            )

    def _validate_source_reference(self) -> None:
        source = self.source_reference
        if source.idempotency_key != self.idempotency_key:
            raise ValidationError(
                "Cost entry idempotency key does not match its source identity.",
                code="PROJECT_COST_ENTRY_IDEMPOTENCY_KEY_INVALID",
            )

    def _validate_posting_snapshot(self) -> None:
        snapshot = (
            self.base_amount,
            self.base_currency_code,
            self.exchange_rate,
            self.exchange_rate_date,
            self.exchange_rate_source,
            self.exchange_rate_captured_at,
            self.posting_date,
            self.financial_period_id,
            self.posted_by,
            self.posted_at,
        )
        if self.status in {ProjectCostEntryStatus.POSTED, ProjectCostEntryStatus.REVERSED}:
            if any(value is None for value in snapshot):
                raise ValidationError(
                    "Posted cost entries require a complete accounting snapshot.",
                    code="PROJECT_COST_ENTRY_POSTING_SNAPSHOT_INCOMPLETE",
                )
            if self.base_amount == 0 or self.amount * self.base_amount <= 0:
                raise ValidationError(
                    "Transaction and base amounts must have the same non-zero sign.",
                    code="PROJECT_COST_ENTRY_BASE_AMOUNT_SIGN_INVALID",
                )
        elif any(value is not None for value in snapshot):
            raise ValidationError(
                "Unposted cost entries cannot contain an accounting snapshot.",
                code="PROJECT_COST_ENTRY_PREMATURE_POSTING_SNAPSHOT",
            )

    def _require_status(self, expected: ProjectCostEntryStatus, *, code: str) -> None:
        if self.status != expected:
            raise BusinessRuleError(
                f"Cost entry must be {expected.value}; current status is {self.status.value}.",
                code=code,
            )

    def _copy_from(self, candidate: "ProjectCostEntry") -> None:
        for name, value in candidate.__dict__.items():
            object.__setattr__(self, name, value)


__all__ = [
    "ProjectCostEntry",
    "ProjectCostEntryKind",
    "ProjectCostEntryStatus",
]
