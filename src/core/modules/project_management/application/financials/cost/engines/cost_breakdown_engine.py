"""Cost breakdown engine — provides planned-vs-actual by (type, currency).

Delegates to CostPolicyEngine for consistent labor policy treatment.
Reporting delegates here rather than owning cost breakdown logic.
"""

from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.application.financials.cost.engines.cost_policy_engine import (
    CostPolicySnapshot,
)
from src.core.modules.project_management.application.financials.models.finance_models import (
    CostBreakdownRow,
)


class CostBreakdownEngine:
    """
    Build cost breakdown rows (planned vs actual by cost type and currency).

    Uses canonical cost-policy facts without substituting baseline authority.
    """

    def build_breakdown_from_snapshot(
        self,
        snapshot: CostPolicySnapshot,
    ) -> list[CostBreakdownRow]:
        """Build exact Decimal rows from one canonical policy snapshot."""
        planned_map = dict(snapshot.planned_map)
        actual_map = dict(snapshot.actual_map)

        rows: list[CostBreakdownRow] = []
        keys = set(planned_map.keys()) | set(actual_map.keys())
        for (cost_type, currency) in sorted(
            keys,
            key=lambda x: (x[0].value if hasattr(x[0], "value") else str(x[0]), x[1]),
        ):
            rows.append(
                CostBreakdownRow(
                    cost_type=cost_type.value if hasattr(cost_type, "value") else str(cost_type),
                    currency=currency,
                    planned=planned_map.get((cost_type, currency), Decimal(0)),
                    actual=actual_map.get((cost_type, currency), Decimal(0)),
                )
            )
        return rows


__all__ = ["CostBreakdownEngine"]
