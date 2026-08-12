from __future__ import annotations

from dataclasses import field
from datetime import date, datetime
from typing import Literal, Protocol

from pydantic import field_validator

from src.core.platform.common.pydantic import normalize_required_text, validated_dataclass


@validated_dataclass(frozen=True)
class BillingPreparationLinePayload:
    line_id: str
    source_type: str
    source_id: str
    source_revision: str
    source_content_hash: str
    description: str
    source_date: date
    quantity: str
    unit: str
    unit_rate: str
    net_amount: str
    currency_code: str
    task_id: str | None = None
    resource_id: str | None = None

    @field_validator(
        "line_id", "source_type", "source_id", "source_revision",
        "source_content_hash", "description", "quantity", "unit", "unit_rate",
        "net_amount", "currency_code", mode="before",
    )
    @classmethod
    def _required(cls, value: object, info) -> str:
        return normalize_required_text(
            value,
            message=f"{info.field_name.replace('_', ' ').title()} is required.",
            code=f"BILLING_CONTRACT_{info.field_name.upper()}_REQUIRED",
        )


@validated_dataclass(frozen=True)
class ProjectBillingPreparationPayload:
    schema_name: Literal["project_billing_preparation.v1"]
    message_id: str
    tenant_id: str
    organization_id: str
    project_id: str
    preparation_id: str
    preparation_number: str
    billing_method: str
    period_start: date
    period_end: date
    currency_code: str
    customer_party_id: str
    contract_reference: str
    external_customer_reference: str | None
    purchase_order_reference: str | None
    payment_terms_days: int
    total_amount: str
    approved_by: str
    approved_at: datetime
    lines: tuple[BillingPreparationLinePayload, ...] = field(default_factory=tuple)

    @field_validator(
        "message_id", "tenant_id", "organization_id", "project_id",
        "preparation_id", "preparation_number", "billing_method", "currency_code",
        "customer_party_id", "contract_reference", "total_amount", "approved_by",
        mode="before",
    )
    @classmethod
    def _required(cls, value: object, info) -> str:
        return normalize_required_text(
            value,
            message=f"{info.field_name.replace('_', ' ').title()} is required.",
            code=f"BILLING_CONTRACT_{info.field_name.upper()}_REQUIRED",
        )


class ProjectBillingPreparationPublisher(Protocol):
    """External adapter port; Accounting decides whether/how to issue an invoice."""

    def publish(self, payload: ProjectBillingPreparationPayload) -> None: ...


__all__ = [
    "BillingPreparationLinePayload",
    "ProjectBillingPreparationPayload",
    "ProjectBillingPreparationPublisher",
]
