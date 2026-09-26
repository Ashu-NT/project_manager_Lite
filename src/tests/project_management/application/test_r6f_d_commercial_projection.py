from __future__ import annotations

from dataclasses import MISSING, FrozenInstanceError, fields, replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.financials.models.billing import (
    FinancialCommercialProjectionDto,
)
from src.core.modules.project_management.api.desktop.financials.serializers.billing_serializer import (
    serialize_commercial_projection,
)
from src.core.modules.project_management.application.financials.models.finance_models import (
    ProjectCommercialProjection,
)
from src.core.modules.project_management.application.financials.revenue.commercial_projection_query import (
    CommercialProjectionQuery,
)
from src.core.modules.project_management.application.financials.revenue.profitability_calculator import (
    ProfitabilityInputs,
    ProfitabilityResult,
    ProjectProfitabilityCalculator,
)
from src.core.modules.project_management.contracts.reads.financials.commercial_metric_availability import (
    CommercialMetricAvailability as Availability,
)
from src.core.modules.project_management.contracts.reads.financials.commercial_metric_availability import (
    CommercialMetricUnavailableReason as Reason,
)
from src.core.modules.project_management.domain.financials.configuration import (
    BillingMethod,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.ui_qml.modules.project_management.presenters.financials.revenue.availability import (
    availability_label,
)


def inputs(**changes):
    return replace(
        ProfitabilityInputs(
            billing_method=BillingMethod.FIXED_PRICE,
            contract_value=Decimal(1000000),
            forecast_cost_at_completion=Decimal(750000),
            project_currency="XAF",
            contract_currency="XAF",
            cost_currency="XAF",
        ),
        **changes,
    )


@pytest.mark.parametrize(
    "eac,margin,percent",
    [
        ("750000", "250000", "25"),
        ("1000000", "0", "0"),
        ("1250000", "-250000", "-25"),
    ],
)
def test_exact_golden_scenarios(eac, margin, percent):
    result = ProjectProfitabilityCalculator.calculate(
        inputs(forecast_cost_at_completion=Decimal(eac))
    )
    assert result.forecast_revenue_at_completion == Decimal(1000000)
    assert result.projected_margin_amount == Decimal(margin)
    assert result.projected_margin_percent == Decimal(percent)
    assert result.margin_availability == "available"


@pytest.mark.parametrize(
    "changes,state",
    [
        ({"forecast_cost_at_completion": None}, "unavailable"),
        ({"contract_value": None}, "not_configured"),
        ({"contract_currency": "EUR"}, "unavailable"),
        ({"cost_currency": "EUR"}, "unavailable"),
        ({"billing_method": BillingMethod.TIME_AND_MATERIALS}, "unsupported"),
        ({"billing_method": BillingMethod.COST_PLUS}, "unsupported"),
        ({"billing_method": BillingMethod.NON_BILLABLE}, "not_applicable"),
    ],
)
def test_missing_unsupported_and_currency_are_not_zero(changes, state):
    result = ProjectProfitabilityCalculator.calculate(inputs(**changes))
    assert result.projected_margin_amount is None
    assert result.projected_margin_percent is None
    assert result.margin_availability == state
    if (
        "forecast_cost_at_completion" in changes
        or changes.get("cost_currency") == "EUR"
    ):
        assert result.forecast_revenue_at_completion == Decimal(1000000)


def test_zero_denominator_and_decimal_precision():
    result = ProjectProfitabilityCalculator.calculate(inputs(contract_value=Decimal(0)))
    assert result.projected_margin_amount == Decimal(-750000)
    assert result.projected_margin_percent is None
    assert result.percent_availability == "not_applicable"
    precise = ProjectProfitabilityCalculator.calculate(
        inputs(
            contract_value=Decimal("1.000001"),
            forecast_cost_at_completion=Decimal("0.000001"),
        )
    )
    assert precise.projected_margin_amount == Decimal("1.000000")
    assert precise.projected_margin_percent == Decimal("1.000000") / Decimal(
        "1.000001"
    ) * Decimal(100)


def test_float_authority_is_rejected():
    with pytest.raises(ValidationError):
        ProjectProfitabilityCalculator.calculate(inputs(contract_value=0.1))


def query_fixture(*, method=BillingMethod.FIXED_PRICE, foreign=None):
    scope = dict(tenant_id="tenant", organization_id="org", project_id="project")
    profile = SimpleNamespace(**scope, contract_value=Decimal(100), currency_code="XAF")
    if foreign:
        setattr(profile, foreign, "foreign")
    financial = SimpleNamespace(
        **scope, billing_method=method, is_billable=True, currency_code="XAF"
    )
    calls = []
    prepared = [Decimal(100)]

    def totals(project, cutoff):
        calls.append((project, cutoff))
        return SimpleNamespace(
            project_id=project,
            project_currency="XAF",
            estimate_at_completion=Decimal(75),
        )

    query = CommercialProjectionQuery(
        billing_repo=SimpleNamespace(get_profile=lambda _: profile),
        financial_profile_repo=SimpleNamespace(get_by_project=lambda _: financial),
        billing_reader=SimpleNamespace(
            approved_preparation_amount=lambda **kw: prepared[0]
        ),
        cost_totals=totals,
    )
    return (
        query,
        dict(**scope, as_of_date=date(2026, 8, 31), include_profitability=True),
        calls,
        prepared,
    )


@pytest.mark.parametrize("foreign", ["tenant_id", "organization_id", "project_id"])
def test_hostile_profile_scope_is_rejected(foreign):
    query, request, calls, _ = query_fixture(foreign=foreign)
    with pytest.raises(NotFoundError):
        query.read(**request)
    assert calls == []


def test_redaction_precedes_cost_query():
    query, request, calls, _ = query_fixture()
    result = query.read(**dict(request, include_profitability=False))
    assert result.revenue_availability == "restricted"
    assert result.forecast_revenue_at_completion is None
    assert result.projected_margin_amount is None
    assert calls == []


@pytest.mark.parametrize(
    "method",
    [
        BillingMethod.TIME_AND_MATERIALS,
        BillingMethod.COST_PLUS,
        BillingMethod.NON_BILLABLE,
    ],
)
def test_unsupported_volume_never_uses_cost_or_rates(method):
    query, request, calls, _ = query_fixture(method=method)
    assert query.read(**request).forecast_revenue_at_completion is None
    assert calls == []


def test_preparation_progress_does_not_become_revenue_and_fact_is_immutable():
    query, request, calls, prepared = query_fixture()
    first = query.read(**request)
    prepared[0] = Decimal(80)  # Approved signed correction against the original 100.
    second = query.read(**request)
    assert (
        first.forecast_revenue_at_completion
        == second.forecast_revenue_at_completion
        == Decimal(100)
    )
    assert (
        first.projected_margin_amount == second.projected_margin_amount == Decimal(25)
    )
    assert second.approved_preparation_amount == Decimal(80)
    assert second.as_of_date == request["as_of_date"]
    assert calls == [("project", request["as_of_date"])] * 2
    with pytest.raises(FrozenInstanceError):
        second.projected_margin_amount = Decimal(0)


@pytest.mark.parametrize(
    "model",
    [
        ProfitabilityResult,
        ProjectCommercialProjection,
        FinancialCommercialProjectionDto,
    ],
)
def test_availability_fields_are_required_without_defaults(model):
    by_name = {field.name: field for field in fields(model)}
    for name in ("revenue_availability", "margin_availability", "percent_availability"):
        assert by_name[name].default is MISSING
        assert by_name[name].default_factory is MISSING


@pytest.mark.parametrize(
    "contract,eac,expected_percent",
    [
        ("0", "0", None),
        ("100000", "100000", Decimal(0)),
    ],
)
def test_zero_metrics_are_typed_available_and_serialized(
    contract, eac, expected_percent
):
    calculated = ProjectProfitabilityCalculator.calculate(
        inputs(
            contract_value=Decimal(contract),
            forecast_cost_at_completion=Decimal(eac),
        )
    )
    query, request, _, _ = query_fixture()
    fact = replace(
        query.read(**request),
        forecast_revenue_at_completion=calculated.forecast_revenue_at_completion,
        projected_margin_amount=calculated.projected_margin_amount,
        projected_margin_percent=calculated.projected_margin_percent,
        revenue_availability=calculated.revenue_availability,
        margin_availability=calculated.margin_availability,
        percent_availability=calculated.percent_availability,
        revenue_reason=calculated.revenue_reason,
        margin_reason=calculated.margin_reason,
        percent_reason=calculated.percent_reason,
    )
    assert fact.revenue_availability is Availability.AVAILABLE
    assert fact.margin_availability is Availability.AVAILABLE
    assert fact.projected_margin_amount == Decimal(0)
    assert fact.projected_margin_percent == expected_percent
    dto = serialize_commercial_projection(fact)
    assert Decimal(dto.forecast_revenue_at_completion) == Decimal(contract)
    assert Decimal(dto.projected_margin_amount) == Decimal(0)
    if expected_percent is None:
        assert dto.percent_availability is Availability.NOT_APPLICABLE
        assert dto.percent_reason is Reason.ZERO_DENOMINATOR
        assert dto.projected_margin_percent == ""
    else:
        assert dto.percent_availability is Availability.AVAILABLE
        assert Decimal(dto.projected_margin_percent) == Decimal(0)


@pytest.mark.parametrize(
    "state,reason,label",
    [
        (Availability.AVAILABLE, None, "Available"),
        (Availability.NOT_CONFIGURED, Reason.BILLING_PROFILE_MISSING, "Not configured"),
        (
            Availability.UNSUPPORTED,
            Reason.T_AND_M_FORECAST_AUTHORITY_MISSING,
            "Projection unavailable for this billing method",
        ),
        (Availability.UNAVAILABLE, Reason.EAC_UNAVAILABLE, "Canonical EAC unavailable"),
        (
            Availability.RESTRICTED,
            Reason.PROFITABILITY_PERMISSION_REQUIRED,
            "Restricted",
        ),
        (Availability.NOT_APPLICABLE, Reason.ZERO_DENOMINATOR, "Not applicable"),
    ],
)
def test_serialization_and_presentation_preserve_each_state(state, reason, label):
    query, request, _, _ = query_fixture()
    result = replace(
        query.read(**request),
        revenue_availability=state,
        margin_availability=state,
        percent_availability=state,
        revenue_reason=reason,
        margin_reason=reason,
        percent_reason=reason,
    )
    dto = serialize_commercial_projection(result)
    assert dto.revenue_availability is state
    assert dto.margin_availability is state
    assert dto.percent_availability is state
    assert dto.margin_reason is reason
    assert availability_label(dto.margin_availability, dto.margin_reason) == label


def test_missing_eac_uses_unavailable_not_unsupported_or_restricted():
    result = ProjectProfitabilityCalculator.calculate(
        inputs(forecast_cost_at_completion=None)
    )
    assert result.revenue_availability is Availability.AVAILABLE
    assert result.margin_availability is Availability.UNAVAILABLE
    assert result.percent_availability is Availability.UNAVAILABLE
    assert result.margin_reason is Reason.EAC_UNAVAILABLE
    assert result.percent_reason is Reason.EAC_UNAVAILABLE
