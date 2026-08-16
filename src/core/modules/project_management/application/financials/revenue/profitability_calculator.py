"""Project profitability calculator — authoritative margin computation.

Implements ADR-PF-010's projected-margin projection. Forecast cost at
completion is always CostPolicyEngine's canonical
CostControlTotals.estimate_at_completion -- this module never recomposes
cost.

Only FIXED_PRICE produces a projected margin today. The other two supported
methods were investigated and rejected as unsafe or unproven, not merely
skipped:

- TIME_AND_MATERIALS: no forecast-billing-rate concept exists anywhere in
  this codebase (LaborCostEngine/CostPolicyEngine forecast *cost* rates,
  never billing rates project-wide). contract_value has no domain-enforced
  meaning for T&M (not a proven not-to-exceed ceiling, not a proven revenue
  forecast) -- using it as a stand-in forecast revenue would present an
  unproven number as if it were one. Profitability is explicitly
  unavailable until a forecast-billing-volume concept is built.
- COST_PLUS: add_cost_plus_source (preparation_service.py) selects billable
  cost one posted ProjectCostEntry at a time with no cost-code/category
  filter, and there is no recoverable/non-recoverable cost distinction
  anywhere in the domain. CostControlTotals.estimate_at_completion is
  whole-project forecast cost; nothing proves 100% of it is recoverable
  under this contract's markup. Applying markup to unfiltered EAC would
  silently overstate revenue for any project with non-recoverable cost
  mixed in. Profitability is explicitly unavailable until the domain can
  identify a recoverable-cost basis.
- FIXED_PRICE: the agreed contract value does not move with cost, so it
  already *is* the forecast revenue at completion -- exact, not an
  estimate. This is the only method where the projection is safe today.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.core.modules.project_management.domain.financials.configuration import BillingMethod

_UNAVAILABLE_REVENUE_BASIS: dict[BillingMethod, str] = {
    BillingMethod.TIME_AND_MATERIALS: "unavailable_time_and_materials_forecast_billing",
    BillingMethod.COST_PLUS: "unavailable_cost_plus_recoverability",
    BillingMethod.NON_BILLABLE: "unavailable_non_billable",
}


@dataclass(frozen=True)
class ProfitabilityInputs:
    billing_method: BillingMethod
    contract_value: Decimal
    forecast_cost_at_completion: Decimal | None


@dataclass(frozen=True)
class ProfitabilityResult:
    forecast_revenue_at_completion: Decimal | None
    revenue_basis: str
    projected_margin_amount: Decimal | None
    projected_margin_percent: Decimal | None


class ProjectProfitabilityCalculator:
    """Computes forecast_revenue_at_completion and projected_margin per
    ADR-PF-010. Never recomposes cost -- forecast_cost_at_completion must
    already be CostPolicyEngine's canonical estimate_at_completion. Returns
    an explicit "unavailable" result (revenue_basis names the reason) for
    any billing method other than fixed-price."""

    @staticmethod
    def calculate(inputs: ProfitabilityInputs) -> ProfitabilityResult:
        if inputs.billing_method is not BillingMethod.FIXED_PRICE:
            return ProfitabilityResult(
                forecast_revenue_at_completion=None,
                revenue_basis=_UNAVAILABLE_REVENUE_BASIS.get(
                    inputs.billing_method, "unavailable"
                ),
                projected_margin_amount=None,
                projected_margin_percent=None,
            )

        eac = inputs.forecast_cost_at_completion
        revenue = inputs.contract_value
        if eac is None:
            return ProfitabilityResult(
                forecast_revenue_at_completion=revenue,
                revenue_basis="contract_value",
                projected_margin_amount=None,
                projected_margin_percent=None,
            )

        margin = revenue - eac
        percent = None if revenue == 0 else (margin / revenue) * Decimal("100")
        return ProfitabilityResult(
            forecast_revenue_at_completion=revenue,
            revenue_basis="contract_value",
            projected_margin_amount=margin,
            projected_margin_percent=percent,
        )


__all__ = ["ProfitabilityInputs", "ProfitabilityResult", "ProjectProfitabilityCalculator"]
