from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from src.core.platform.integration.canonical_json import canonical_json_sha256


class FinancialSourceModule(str, Enum):
    PROJECT_MANAGEMENT = "project_management"
    PLATFORM_TIME = "platform_time"
    INVENTORY_PROCUREMENT = "inventory_procurement"


class FinancialSourceType(str, Enum):
    TIME_ENTRY = "time_entry"
    PURCHASE_ORDER_LINE = "purchase_order_line"
    RECEIPT_LINE = "receipt_line"
    MANUAL_COMMAND = "manual_command"


class FinancialPostingPurpose(str, Enum):
    LABOR_ACTUAL = "labor_actual"
    PURCHASE_COMMITMENT = "purchase_commitment"
    RECEIPT_ACCRUAL = "receipt_accrual"
    MANUAL_ACTUAL = "manual_actual"


_ALLOWED_SOURCE_COMBINATIONS = {
    (
        FinancialSourceModule.PLATFORM_TIME,
        FinancialSourceType.TIME_ENTRY,
        FinancialPostingPurpose.LABOR_ACTUAL,
    ),
    (
        FinancialSourceModule.INVENTORY_PROCUREMENT,
        FinancialSourceType.PURCHASE_ORDER_LINE,
        FinancialPostingPurpose.PURCHASE_COMMITMENT,
    ),
    (
        FinancialSourceModule.INVENTORY_PROCUREMENT,
        FinancialSourceType.RECEIPT_LINE,
        FinancialPostingPurpose.RECEIPT_ACCRUAL,
    ),
    (
        FinancialSourceModule.PROJECT_MANAGEMENT,
        FinancialSourceType.MANUAL_COMMAND,
        FinancialPostingPurpose.MANUAL_ACTUAL,
    ),
}


def _required_text(value: object, *, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{label} is required")
    return normalized


class _FinancialSourceContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FinancialSourceReference(_FinancialSourceContract):
    """Scoped semantic identity used independently of message delivery identity."""

    tenant_id: str
    organization_id: str
    project_id: str
    source_module: FinancialSourceModule
    source_type: FinancialSourceType
    source_id: str
    source_line_id: str | None = None
    source_revision: str
    content_hash: str
    posting_purpose: FinancialPostingPurpose

    @field_validator(
        "tenant_id",
        "organization_id",
        "project_id",
        "source_id",
        "source_revision",
        mode="before",
    )
    @classmethod
    def _validate_required_text(cls, value: object, info) -> str:
        return _required_text(value, label=info.field_name.replace("_", " ").capitalize())

    @field_validator("source_line_id", mode="before")
    @classmethod
    def _normalize_source_line_id(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @field_validator("content_hash", mode="before")
    @classmethod
    def _validate_content_hash(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("Content hash must be a lowercase SHA-256 digest")
        return normalized

    @model_validator(mode="after")
    def _validate_source_combination(self) -> "FinancialSourceReference":
        combination = (self.source_module, self.source_type, self.posting_purpose)
        if combination not in _ALLOWED_SOURCE_COMBINATIONS:
            raise ValueError("Source module, type, and posting purpose are incompatible")
        if self.source_type in {
            FinancialSourceType.PURCHASE_ORDER_LINE,
            FinancialSourceType.RECEIPT_LINE,
        } and not self.source_line_id:
            raise ValueError("Line-based financial sources require a source line ID")
        return self

    @property
    def idempotency_key(self) -> str:
        # Project and content are excluded so a conflicting reassignment/replay
        # collides with the original semantic source and can be quarantined.
        identity = {
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "source_module": self.source_module.value,
            "source_type": self.source_type.value,
            "source_id": self.source_id,
            "source_line_id": self.source_line_id,
            "source_revision": self.source_revision,
            "posting_purpose": self.posting_purpose.value,
        }
        return f"pfin:v1:{canonical_json_sha256(identity)}"


def financial_source_content_hash(payload: BaseModel | Mapping[str, object]) -> str:
    """Hash the immutable source snapshot body before constructing its reference."""

    return canonical_json_sha256(payload)


FinancialSourceT = TypeVar("FinancialSourceT", bound=_FinancialSourceContract)


class FinancialSourcePage(_FinancialSourceContract, Generic[FinancialSourceT]):
    items: tuple[FinancialSourceT, ...]
    next_cursor: str | None = None

    @field_validator("next_cursor", mode="before")
    @classmethod
    def _normalize_next_cursor(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None


__all__ = [
    "FinancialPostingPurpose",
    "FinancialSourceModule",
    "FinancialSourcePage",
    "FinancialSourceReference",
    "FinancialSourceType",
    "financial_source_content_hash",
]
