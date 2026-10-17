from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CommitmentLineResponse:
    id: str
    purchase_order_line_id: str
    state: str
    amount: Decimal
    matched_amount: Decimal
    remaining_amount: Decimal
    currency_code: str
    task_id: str | None
    ordered_quantity: Decimal
    quantity_unit: str
    order_date: date | None
    expected_delivery_date: date | None
    source_revision: int


@dataclass(frozen=True, slots=True)
class CommitmentPage:
    items: tuple[CommitmentLineResponse, ...] = ()
    total: int = 0
    offset: int = 0
    limit: int = 50
    sort_key: str = "metaText"
    sort_direction: str = "desc"
