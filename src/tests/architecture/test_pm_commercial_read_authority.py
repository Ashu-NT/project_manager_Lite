from __future__ import annotations

import inspect

from src.core.modules.project_management.application.financials.invoicing.preparation_service import (
    ProjectBillingPreparationService,
)
from src.core.modules.project_management.application.financials.revenue.commercial_projection_query import (
    CommercialProjectionQuery,
)
from src.core.modules.project_management.application.financials.revenue.profitability_calculator import (
    ProjectProfitabilityCalculator,
)
from src.core.modules.project_management.infrastructure.reporting.builders.profitability import (
    ReportingProfitabilityMixin,
)


def test_commercial_projection_has_one_bounded_managerial_read_path() -> None:
    source = inspect.getsource(CommercialProjectionQuery)
    assert "CommercialProjectionQuery(" in inspect.getsource(ReportingProfitabilityMixin)
    assert "approved_preparation_amount(" in source
    assert "list_preparations(" not in source
    assert "list_external_events(" not in source
    assert "externally_invoiced_amount" not in source
    assert "externally_paid_amount" not in source
    assert "date.today(" not in source
    assert "float(" not in source


def test_billable_time_uses_billing_rate_and_canonical_decimal_margin() -> None:
    time_source = inspect.getsource(ProjectBillingPreparationService.add_approved_time_source)
    margin_source = inspect.getsource(ProjectProfitabilityCalculator.calculate)
    assert "RateType.BILLING" in time_source
    assert "RateType.COST" not in time_source
    assert "hourly_rate" not in time_source
    assert "float(" not in margin_source
    assert "forecast_cost_at_completion" in margin_source


def test_commercial_application_authority_has_no_clock_orm_or_rate_revaluation():
    source = inspect.getsource(CommercialProjectionQuery)
    for forbidden in ("sqlalchemy", "date.today(", "datetime.now(", "float(", "hourly_rate", "RateType.", "list_preparations("):
        assert forbidden not in source
    assert "ProjectProfitabilityCalculator.calculate(" in source
    assert "estimate_at_completion" in source
