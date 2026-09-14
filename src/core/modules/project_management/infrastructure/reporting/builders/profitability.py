"""Profitability mixin — thin reporting delegate.

Computes managerial commercial/profitability projections. Preparation
aggregation uses the bounded Finance Billing Reader; cost
composition reads the existing canonical CostPolicyEngine result
(CostControlTotals.estimate_at_completion). Margin arithmetic itself lives
in financials/revenue/profitability_calculator.py, which is pure and does
no I/O -- this mixin only gathers inputs and applies redaction.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from src.core.modules.project_management.application.financials.models.finance_models import (
    ProjectCommercialProjection,
)
from src.core.modules.project_management.application.financials.revenue.profitability_calculator import (
    ProfitabilityInputs,
    ProjectProfitabilityCalculator,
)
from src.core.modules.project_management.contracts.reads.financials.finance_billing_reader import (
    FinanceBillingReader,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.platform.common.exceptions import NotFoundError


class ReportingProfitabilityMixin:
    _billing_repo: ProjectBillingRepository
    _billing_reader: FinanceBillingReader
    _project_repo: ProjectRepository
    _financial_profile_repo: ProjectFinancialProfileRepository

    def get_project_commercial_projection(
        self, project_id: str, *, as_of_date: date | None = None
    ) -> ProjectCommercialProjection:
        # Forecast-revenue/margin figures are further redacted without
        # finance.read_profitability, matching get_project_kpis's mixed-content pattern.
        self._require_finance_view(
            "view project commercial projection", project_id=project_id
        )
        if self._project_repo.get(project_id) is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        resolved_as_of = as_of_date or datetime.now(timezone.utc).astimezone().date()
        profile = self._billing_repo.get_profile(project_id)
        approved_preparation_amount = Decimal(0)
        if profile is not None:
            scope = self._tenant_context_service.require_active_scope_ids(
                operation_label="view commercial projection"
            )
            approved_preparation_amount = self._billing_reader.approved_preparation_amount(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project_id,
            )

        profitability_detail_included = self._has_profitability_view(project_id)
        forecast_revenue: Decimal | None = None
        revenue_basis = ""
        margin_amount: Decimal | None = None
        margin_percent: Decimal | None = None
        if profitability_detail_included and profile is not None:
            # billing_method lives on ProjectFinancialProfile, a separate aggregate from
            # the ProjectBillingProfile this mixin otherwise reads from.
            financial_profile = self._financial_profile_repo.get_by_project(project_id)
            if financial_profile is not None:
                facts, policy = self._compose_finance_policy(
                    project_id, as_of=resolved_as_of
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
            approved_preparation_amount=approved_preparation_amount,
            forecast_revenue_at_completion=forecast_revenue,
            revenue_basis=revenue_basis,
            projected_margin_amount=margin_amount,
            projected_margin_percent=margin_percent,
            profitability_detail_included=profitability_detail_included,
        )

__all__ = ["ReportingProfitabilityMixin"]
