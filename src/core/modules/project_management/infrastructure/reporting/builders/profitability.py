"""Profitability mixin — thin reporting delegate.

Computes the ADR-PF-010 commercial/profitability projections (contract,
billable, externally invoiced, externally paid, projected margin). Billing
aggregation reads the existing canonical ProjectBillingRepository; cost
composition reads the existing canonical CostPolicyEngine result
(CostControlTotals.estimate_at_completion). Margin arithmetic itself lives
in financials/revenue/profitability_calculator.py, which is pure and does
no I/O -- this mixin only gathers inputs and applies redaction.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.core.modules.project_management.application.financials.models.finance_models import (
    ProjectCommercialProjection,
)
from src.core.modules.project_management.application.financials.revenue.profitability_calculator import (
    ProfitabilityInputs,
    ProjectProfitabilityCalculator,
)
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillingExternalEventType,
    BillingPreparationStatus,
    ProjectBillingPreparation,
)
from src.core.platform.common.exceptions import NotFoundError

_BILLABLE_STATUSES = frozenset(
    {
        BillingPreparationStatus.APPROVED,
        BillingPreparationStatus.DELIVERY_PENDING,
        BillingPreparationStatus.DELIVERED,
        BillingPreparationStatus.ACKNOWLEDGED,
        BillingPreparationStatus.RECONCILED,
    }
)
_PREPARATION_PAGE_SIZE = 100


class ReportingProfitabilityMixin:
    _billing_repo: ProjectBillingRepository
    _project_repo: ProjectRepository
    _financial_profile_repo: ProjectFinancialProfileRepository

    def get_project_commercial_projection(
        self, project_id: str
    ) -> ProjectCommercialProjection:
        # contract/billable/invoiced/paid are ordinary Project Finance
        # authority data (finance.read); the forecast-revenue/margin figures
        # are further redacted without finance.read_profitability, matching
        # the get_project_kpis mixed-content pattern.
        self._require_finance_view(
            "view project commercial projection", project_id=project_id
        )
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        profile = self._billing_repo.get_profile(project_id)
        # list_preparations requires an existing billing profile, so avoid the
        # repository call when commercial billing has not been configured.
        preparations = self._all_billing_preparations(project_id) if profile else []

        billable_amount = Decimal("0")
        externally_invoiced_amount = Decimal("0")
        externally_paid_amount = Decimal("0")
        any_external_event = False
        for preparation in preparations:
            if preparation.status in _BILLABLE_STATUSES:
                billable_amount += preparation.total_amount
            # A preparation's invoice reference and its reconciliation are
            # set on *different* events, not carried forward onto whichever
            # event happens to be latest -- checking only the latest event
            # (as a current-status projection does) would silently lose the invoice reference
            # once a later RECONCILED event supersedes it. Aggregation needs
            # the full history: has this preparation *ever* been invoiced /
            # *ever* been reconciled.
            events = self._billing_repo.list_external_events(preparation.id)
            if not events:
                continue
            any_external_event = True
            if any(event.external_invoice_reference for event in events):
                externally_invoiced_amount += preparation.total_amount
            if any(
                event.event_type is BillingExternalEventType.RECONCILED
                for event in events
            ):
                externally_paid_amount += preparation.total_amount

        profitability_detail_included = self._has_profitability_view(project_id)
        forecast_revenue: Decimal | None = None
        revenue_basis = ""
        margin_amount: Decimal | None = None
        margin_percent: Decimal | None = None
        if profitability_detail_included and profile is not None:
            # billing_method lives on ProjectFinancialProfile, not on the
            # ProjectBillingProfile this mixin otherwise reads from --
            # commercial billing method and finance configuration are
            # separate aggregates.
            financial_profile = self._financial_profile_repo.get_by_project(project_id)
            if financial_profile is not None:
                facts, policy = self._compose_finance_policy(
                    project_id, as_of=date.today()
                )
                del facts
                calculation = ProjectProfitabilityCalculator.calculate(
                    ProfitabilityInputs(
                        billing_method=financial_profile.billing_method,
                        contract_value=profile.contract_value,
                        forecast_cost_at_completion=policy.totals.estimate_at_completion,
                    )
                )
                forecast_revenue = calculation.forecast_revenue_at_completion
                revenue_basis = calculation.revenue_basis
                margin_amount = calculation.projected_margin_amount
                margin_percent = calculation.projected_margin_percent

        return ProjectCommercialProjection(
            project_id=project_id,
            project_currency=profile.currency_code if profile else None,
            contract_value=profile.contract_value if profile else None,
            billable_amount=billable_amount,
            externally_invoiced_amount=externally_invoiced_amount,
            externally_paid_amount=externally_paid_amount,
            external_accounting_data_available=any_external_event,
            forecast_revenue_at_completion=forecast_revenue,
            revenue_basis=revenue_basis,
            projected_margin_amount=margin_amount,
            projected_margin_percent=margin_percent,
            profitability_detail_included=profitability_detail_included,
        )

    def _all_billing_preparations(
        self, project_id: str
    ) -> list[ProjectBillingPreparation]:
        results: list[ProjectBillingPreparation] = []
        offset = 0
        while True:
            page, total = self._billing_repo.list_preparations(
                project_id, offset=offset, limit=_PREPARATION_PAGE_SIZE
            )
            results.extend(page)
            offset += len(page)
            if not page or offset >= total:
                break
        return results


__all__ = ["ReportingProfitabilityMixin"]
