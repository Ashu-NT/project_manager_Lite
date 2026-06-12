from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.identifiers import generate_id


class CommitmentStatus(str, Enum):
    UNCOMMITTED = "uncommitted"  # planned/estimated only, no purchase order
    COMMITTED = "committed"      # purchase order raised; cost is obligated
    INVOICED = "invoiced"        # invoice received from vendor
    PAID = "paid"                # payment released


@dataclass
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
