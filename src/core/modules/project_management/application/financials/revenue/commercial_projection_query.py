"""Canonical scoped commercial projection assembly, independent of UI adapters."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Callable

from src.core.modules.project_management.application.financials.cost.engines.cost_policy_engine import (
    CostControlTotals,
)
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
from src.core.modules.project_management.contracts.reads.financials.models.commercial_metric_availability import (
    CommercialMetricAvailability as Availability,
)
from src.core.modules.project_management.contracts.reads.financials.models.commercial_metric_availability import (
    CommercialMetricUnavailableReason as Reason,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.domain.financials.configuration import (
    BillingMethod,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError


class CommercialProjectionQuery:
    def __init__(
        self, *, billing_repo: ProjectBillingRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        billing_reader: FinanceBillingReader,
        cost_totals: Callable[[str, date], CostControlTotals],
    ) -> None:
        self._billing_repo = billing_repo
        self._financial_profile_repo = financial_profile_repo
        self._billing_reader = billing_reader
        self._cost_totals = cost_totals

    def read(
        self, *, tenant_id: str, organization_id: str, project_id: str,
        as_of_date: date, include_profitability: bool,
    ) -> ProjectCommercialProjection:
        if not all((tenant_id, organization_id, project_id)) or not isinstance(as_of_date, date):
            raise ValidationError("Commercial scope and analytical date are required.")
        profile = self._billing_repo.get_profile(project_id)
        financial = self._financial_profile_repo.get_by_project(project_id)
        for entity in (profile, financial):
            if entity is not None and (entity.tenant_id, entity.organization_id, entity.project_id) != (tenant_id, organization_id, project_id):
                raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        prepared = self._billing_reader.approved_preparation_amount(
            tenant_id=tenant_id, organization_id=organization_id, project_id=project_id,
        ) if profile is not None else Decimal(0)
        state = Availability.NOT_CONFIGURED if include_profitability else Availability.RESTRICTED
        reason = (Reason.FINANCIAL_PROFILE_MISSING if financial is None else Reason.BILLING_PROFILE_MISSING) if include_profitability else Reason.PROFITABILITY_PERMISSION_REQUIRED
        revenue_state = margin_state = percent_state = state
        revenue_reason = margin_reason = percent_reason = reason
        revenue = margin = percent = None
        basis = ""
        if include_profitability and financial is not None:
            method = financial.billing_method if financial.is_billable else BillingMethod.NON_BILLABLE
            # Unsupported methods do not need cost evidence or rate resolution.
            totals = self._cost_totals(project_id, as_of_date) if profile is not None and method is BillingMethod.FIXED_PRICE else None
            if totals is not None and totals.project_id != project_id:
                raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
            result = ProjectProfitabilityCalculator.calculate(ProfitabilityInputs(
                billing_method=method,
                contract_value=profile.contract_value if profile else None,
                forecast_cost_at_completion=totals.estimate_at_completion if totals else None,
                project_currency=financial.currency_code,
                contract_currency=profile.currency_code if profile else "",
                cost_currency=totals.project_currency if totals else None,
            ))
            revenue, margin, percent = result.forecast_revenue_at_completion, result.projected_margin_amount, result.projected_margin_percent
            basis = result.revenue_basis
            revenue_state, margin_state, percent_state = result.revenue_availability, result.margin_availability, result.percent_availability
            revenue_reason, margin_reason, percent_reason = result.revenue_reason, result.margin_reason, result.percent_reason
            if profile is None and method is BillingMethod.FIXED_PRICE:
                revenue_reason = margin_reason = percent_reason = Reason.BILLING_PROFILE_MISSING
        return ProjectCommercialProjection(
            project_id=project_id, tenant_id=tenant_id, organization_id=organization_id,
            as_of_date=as_of_date,
            project_currency=financial.currency_code if financial else None,
            contract_value=profile.contract_value if profile else None,
            approved_preparation_amount=prepared,
            forecast_revenue_at_completion=revenue, revenue_basis=basis,
            projected_margin_amount=margin, projected_margin_percent=percent,
            profitability_detail_included=include_profitability,
            revenue_availability=revenue_state, margin_availability=margin_state,
            percent_availability=percent_state,
            revenue_reason=revenue_reason, margin_reason=margin_reason, percent_reason=percent_reason,
        )
