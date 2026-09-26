"""Project profitability calculator — authoritative margin computation.

Forecast cost at completion is always CostPolicyEngine's canonical
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

from src.core.modules.project_management.contracts.reads.financials.commercial_metric_availability import (
    CommercialMetricAvailability as Availability,
)
from src.core.modules.project_management.contracts.reads.financials.commercial_metric_availability import (
    CommercialMetricUnavailableReason as Reason,
)
from src.core.modules.project_management.domain.financials.configuration import (
    BillingMethod,
)
from src.core.platform.domain.finance.money.money import Money


@dataclass(frozen=True)
class ProfitabilityInputs:
    billing_method: BillingMethod
    contract_value: Decimal | None
    forecast_cost_at_completion: Decimal | None
    project_currency: str
    contract_currency: str
    cost_currency: str | None


@dataclass(frozen=True)
class ProfitabilityResult:
    forecast_revenue_at_completion: Decimal | None
    revenue_basis: str
    projected_margin_amount: Decimal | None
    projected_margin_percent: Decimal | None
    revenue_availability: Availability
    margin_availability: Availability
    percent_availability: Availability
    revenue_reason: Reason | None
    margin_reason: Reason | None
    percent_reason: Reason | None


class ProjectProfitabilityCalculator:
    """Computes forecast_revenue_at_completion and projected_margin. Never
    recomposes cost -- forecast_cost_at_completion must already be
    CostPolicyEngine's canonical estimate_at_completion. Returns
    an explicit typed availability and reason for
    any billing method other than fixed-price."""

    @staticmethod
    def calculate(inputs: ProfitabilityInputs) -> ProfitabilityResult:
        if inputs.billing_method is not BillingMethod.FIXED_PRICE:
            state = (
                Availability.NOT_APPLICABLE
                if inputs.billing_method is BillingMethod.NON_BILLABLE
                else Availability.UNSUPPORTED
            )
            reason = {
                BillingMethod.NON_BILLABLE: Reason.NON_BILLABLE,
                BillingMethod.TIME_AND_MATERIALS: Reason.T_AND_M_FORECAST_AUTHORITY_MISSING,
                BillingMethod.COST_PLUS: Reason.RECOVERABLE_COST_AUTHORITY_MISSING,
            }[inputs.billing_method]
            return ProfitabilityResult(
                forecast_revenue_at_completion=None,
                revenue_basis="",
                projected_margin_amount=None,
                projected_margin_percent=None,
                revenue_availability=state,
                margin_availability=state,
                percent_availability=state,
                revenue_reason=reason,
                margin_reason=reason,
                percent_reason=reason,
            )

        if inputs.contract_value is None:
            return ProfitabilityResult(
                None,
                "contract_value_missing",
                None,
                None,
                Availability.NOT_CONFIGURED,
                Availability.NOT_CONFIGURED,
                Availability.NOT_CONFIGURED,
                Reason.CONTRACT_VALUE_MISSING,
                Reason.CONTRACT_VALUE_MISSING,
                Reason.CONTRACT_VALUE_MISSING,
            )
        if (
            not inputs.project_currency
            or inputs.contract_currency != inputs.project_currency
        ):
            return ProfitabilityResult(
                None,
                "currency_mismatch",
                None,
                None,
                Availability.UNAVAILABLE,
                Availability.UNAVAILABLE,
                Availability.UNAVAILABLE,
                Reason.CURRENCY_MISMATCH,
                Reason.CURRENCY_MISMATCH,
                Reason.CURRENCY_MISMATCH,
            )
        eac = inputs.forecast_cost_at_completion
        revenue = Money.of(inputs.contract_value, inputs.project_currency).amount
        if eac is None:
            return ProfitabilityResult(
                forecast_revenue_at_completion=revenue,
                revenue_basis="contract_value",
                projected_margin_amount=None,
                projected_margin_percent=None,
                revenue_availability=Availability.AVAILABLE,
                margin_availability=Availability.UNAVAILABLE,
                percent_availability=Availability.UNAVAILABLE,
                revenue_reason=None,
                margin_reason=Reason.EAC_UNAVAILABLE,
                percent_reason=Reason.EAC_UNAVAILABLE,
            )

        if inputs.cost_currency != inputs.project_currency:
            return ProfitabilityResult(
                revenue,
                "contract_value",
                None,
                None,
                Availability.AVAILABLE,
                Availability.UNAVAILABLE,
                Availability.UNAVAILABLE,
                None,
                Reason.CURRENCY_MISMATCH,
                Reason.CURRENCY_MISMATCH,
            )
        margin = (
            Money.of(revenue, inputs.project_currency)
            - Money.of(eac, inputs.cost_currency)
        ).amount
        percent = None if revenue == 0 else (margin / revenue) * Decimal(100)
        return ProfitabilityResult(
            forecast_revenue_at_completion=revenue,
            revenue_basis="contract_value",
            projected_margin_amount=margin,
            projected_margin_percent=percent,
            revenue_availability=Availability.AVAILABLE,
            margin_availability=Availability.AVAILABLE,
            percent_availability=Availability.NOT_APPLICABLE
            if revenue == 0
            else Availability.AVAILABLE,
            revenue_reason=None,
            margin_reason=None,
            percent_reason=Reason.ZERO_DENOMINATOR if revenue == 0 else None,
        )


__all__ = [
    "ProfitabilityInputs",
    "ProfitabilityResult",
    "ProjectProfitabilityCalculator",
]
