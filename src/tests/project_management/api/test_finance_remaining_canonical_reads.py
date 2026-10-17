from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.contracts.reads.financials.budgets.models.budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.invoicing.models.billing_facts import (
    FinanceBillingWorkspaceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.overview.models.overview_facts import (
    FinanceOverviewFacts,
)
from src.core.modules.project_management.contracts.reads.financials.performance.models.performance_facts import (
    CostPhasingFacts,
    CostPhasingPeriodFact,
    CostPhasingSeriesAvailabilityFact,
    PerformanceEvmFact,
    PerformanceVarianceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.snapshot.models.snapshot_facts import (
    FinanceControlFact,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.ui_qml.modules.project_management.presenters.financials.commitments.commitment_builder import (
    build_commitment_summary,
)
from src.ui_qml.modules.project_management.presenters.financials.invoicing.billing_workspace_builder import (
    build_billing_workspace_views,
)
from src.ui_qml.modules.project_management.presenters.financials.reporting.performance_builder import (
    build_cost_phasing_views,
    build_evm_views,
    build_variance_views,
)
from src.ui_qml.modules.project_management.presenters.financials.shared.overview_builder import (
    build_overview,
)

DAY = date(2026, 10, 17)


def _overview():
    return FinanceOverviewFacts(
        tenant_id="tenant", organization_id="org", project_id="project", as_of=DAY,
        currency_code="KWD", control=FinanceControlFact(Decimal("0.000"), Decimal("-1.234"), Decimal("1.234"), None),
        approved_budget_id="budget", approved_budget_revision=0, approved_budget_at=None,
        approved_forecast_id=None, approved_forecast_revision=None, approved_forecast_as_of=None,
    )


def _evm():
    return PerformanceEvmFact(
        project_id="project", as_of_date=DAY, availability="forecast_unavailable",
        unavailable_reason="No approved forecast", baseline_id="baseline", budget_revision=0,
        forecast_revision=None, forecast_as_of=None, currency_code="KWD",
        bac=Decimal("1234.567"), pv=Decimal("0"), ev=Decimal("0"), ac=Decimal("0"),
        cv=Decimal("0"), sv=Decimal("0"), cpi=None, spi=None, etc=None, eac=None,
        vac=None, tcpi_bac=Decimal("1.23456789"), tcpi_eac=None, notes="Authority note",
    )


def _variance():
    return PerformanceVarianceFacts(
        project_id="project", as_of_date=DAY, currency_code="KWD", budget_revision=0,
        forecast_revision=None, forecast_as_of=None, selected_baseline_id="",
        selected_baseline_label="", compared_baseline_id="", baseline_versions=(),
        baseline_records=(), metrics=(),
    )


def _phasing():
    return CostPhasingFacts(
        tenant_id="tenant", organization_id="org", project_id="project", as_of_date=DAY,
        date_from=DAY, date_to=DAY, granularity="month", currency_code="KWD",
        approved_budget_id="budget", approved_budget_revision=0, approved_forecast_id=None,
        approved_forecast_revision=None, approved_forecast_as_of=None,
        periods=(CostPhasingPeriodFact("2026-10", DAY, DAY, Decimal("1234.567"), Decimal(0),
                    Decimal("-1.234"), Decimal(0), Decimal("-1.234"), "KWD"),),
        series_availability=(CostPhasingSeriesAvailabilityFact("forecast", "unavailable", "Not approved"),),
    )


def _billing():
    return FinanceBillingWorkspaceFacts(None, "", None, _page(), _page(), _page())


def _page():
    return FinancePageFacts((), 0, 2, 5, "metaText", "desc")


CASES = [
    ("get_finance_overview", "finance_snapshot_query", "get_finance_overview", _overview, {}),
    ("get_commitment_summary", "finance_snapshot_query", "get_finance_overview", _overview, {}),
    ("get_performance_evm", "finance_performance_query", "get_evm", _evm, {"as_of_date": DAY, "baseline_id": "baseline"}),
    ("get_performance_variance", "finance_performance_query", "get_variance", _variance, {"as_of_date": DAY, "selected_baseline_id": "baseline"}),
    ("get_cost_phasing", "finance_performance_query", "get_cost_phasing", _phasing, {"date_from": DAY, "date_to": DAY, "granularity": "month", "as_of_date": DAY}),
    ("get_billing_read_workspace", "finance_workspace_query", "get_billing_read_workspace", _billing, {}),
    ("get_accounting_statuses", "finance_workspace_query", "get_accounting_statuses", _page, {}),
]


@pytest.mark.parametrize(("method", "dependency", "operation", "factory", "kwargs"), CASES)
def test_reads_return_exact_canonical_result_and_preserve_denial(method, dependency, operation, factory, kwargs):
    query = Mock()
    source = factory()
    getattr(query, operation).return_value = source
    api = ProjectManagementFinancialsDesktopApi(**{dependency: query})
    assert getattr(api, method)("project", **kwargs) is source
    getattr(query, operation).assert_called_once()
    assert getattr(query, operation).call_args.args == ("project",)
    if dependency != "finance_workspace_query":
        assert getattr(query, operation).call_args.kwargs == kwargs
    error = BusinessRuleError("Denied", code="PERMISSION_DENIED")
    getattr(query, operation).side_effect = error
    with pytest.raises(BusinessRuleError) as raised:
        getattr(api, method)("project", **kwargs)
    assert raised.value is error


def test_absent_project_never_queries_and_does_not_manufacture_zero():
    query = Mock()
    api = ProjectManagementFinancialsDesktopApi(finance_snapshot_query=query, finance_performance_query=query,
                                               finance_workspace_query=query)
    assert api.get_finance_overview("") is None
    assert api.get_performance_evm("") is None
    assert api.get_performance_variance("") is None
    assert api.get_cost_phasing("", date_from=DAY, date_to=DAY) is None
    assert api.get_accounting_statuses("").items == ()
    assert api.get_billing_read_workspace("").profile is None
    assert query.mock_calls == []
    overview = build_overview(project_options=(), selected_project_id="", snapshot=None)
    assert [metric.value for metric in overview.metrics[:4]] == ["Not available"] * 4
    assert build_evm_views(None)["evm_metrics"].items == ()
    assert build_variance_views(None)["baseline_variance"] == ()
    assert build_cost_phasing_views(None)["cost_phasing"].items == ()


def test_overview_preserves_approved_zero_absence_and_signed_minor_units():
    facts = _overview()
    view = build_overview(project_options=(), selected_project_id="project", snapshot=facts)
    values = {metric.label: metric for metric in view.metrics}
    assert values["Budget"].value == "KWD 0.000"
    assert values["Budget"].supporting_text == "Approved revision 0"
    assert values["Actual"].value == "KWD -1.234"
    assert values["Available"].value == "KWD 0.000"
    assert values["Forecast ETC"].value == "Not approved"
    assert values["EAC"].value == values["Budget headroom"].value == "Not available"
    unapproved = replace(facts, approved_budget_id=None)
    assert build_overview(project_options=(), selected_project_id="project", snapshot=unapproved).metrics[0].value == "Not approved"
    assert build_commitment_summary(unapproved).available_after_commitment_label == "Not budgeted"
    assert build_commitment_summary(facts).commitment_rate_pct is None
    assert isinstance(facts.posted_actual, Decimal)


def test_evm_and_phasing_presenters_keep_exact_state_and_unavailable_series():
    facts = _evm()
    views = build_evm_views(facts)
    metrics = {row.id: row for row in views["evm_metrics"].items}
    assert metrics["bac"].status_label == "KWD 1,234.567"
    assert metrics["bac"].state["value"] == "1234.567"
    assert metrics["ac"].status_label == "KWD 0.000"
    assert metrics["cpi"].state["value"] is None
    assert metrics["tcpi_bac"].status_label == "1.23456789"
    assert metrics["eac"].state["availability"] == "unavailable"
    phasing = _phasing()
    views = build_cost_phasing_views(phasing)
    row = views["cost_phasing"].items[0]
    assert row.subtitle == "Planned KWD 1,234.567 | Committed KWD 0.000"
    assert row.state["actual"] == "-1.234"
    assert views["cost_phasing_basis"].fields[-1].supporting_text == "Not approved"
    assert isinstance(phasing.periods[0].planned_cost, Decimal)
    with pytest.raises(FrozenInstanceError):
        phasing.periods[0].planned_cost = Decimal(0)


def test_billing_presenter_keeps_filters_and_server_empty_capabilities():
    source = _billing()
    views = build_billing_workspace_views(source, preparation_search="invoice", line_source_state="reserved")
    assert views["billing_preparation_search"] == "invoice"
    assert views["billing_line_source_state"] == "reserved"
    assert views["billing_preparations"].page == 2
    assert views["billing_preparations"].page_size == 5
    assert views["billing_profile"].state["canCreate"] is False
    assert views["selected_billing_preparation"].fields == ()
    assert views["billing_preparation_lines"].empty_state == "Select a Billing Preparation."
