from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.core.modules.project_management.api.desktop.financials.serializers.performance_serializer import (
    serialize_performance_variance,
)
from src.core.modules.project_management.application.financials.performance_query import (
    ProjectFinancePerformanceQuery,
)


def _basis(**overrides):
    values = {
        "currency_code": "XAF",
        "approved_budget_id": "budget-1",
        "approved_budget": Decimal("100.00"),
        "approved_budget_revision": 2,
        "approved_forecast_revision": 3,
        "approved_forecast_as_of": date(2026, 8, 1),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _evm(**overrides):
    values = {
        "availability": "available",
        "unavailable_reason": "",
        "baseline_id": "baseline-1",
        "BAC": Decimal("100.00"),
        "PV": Decimal("40.00"),
        "EV": Decimal("50.00"),
        "AC": Decimal("45.00"),
        "CV": Decimal("5.00"),
        "SV": Decimal("10.00"),
        "CPI": Decimal("1.11"),
        "SPI": Decimal("1.25"),
        "ETC": Decimal("50.00"),
        "EAC": Decimal("95.00"),
        "VAC": Decimal("5.00"),
        "TCPI_to_BAC": Decimal("1"),
        "TCPI_to_EAC": Decimal("1"),
        "notes": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _query(monkeypatch, *, basis=None, evm=None):
    monkeypatch.setattr(
        "src.core.modules.project_management.application.financials.performance_query.require_permission",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.financials.performance_query.require_project_permission",
        lambda *_args, **_kwargs: None,
    )
    overview = MagicMock()
    overview.read_overview_facts.return_value = basis or _basis()
    context = MagicMock()
    context.require_active_scope_ids.return_value = SimpleNamespace(
        tenant_id="tenant-1", organization_id="org-1"
    )
    return ProjectFinancePerformanceQuery(
        performance_reader=MagicMock(),
        overview_reader=overview,
        earned_value_authority=SimpleNamespace(
            get_earned_value=MagicMock(return_value=evm or _evm())
        ),
        baseline_variance_authority=SimpleNamespace(list_baselines=lambda _project_id: ()),
        tenant_context_service=context,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (Decimal("1.00"), "favorable"),
        (Decimal("0.00"), "on_target"),
        (Decimal("-1.00"), "unfavorable"),
    ),
)
def test_evm_variance_favorability_is_authoritative(monkeypatch, value, expected) -> None:
    facts = _query(monkeypatch, evm=_evm(CV=value, SV=value, VAC=value)).get_variance(
        "project-1", as_of_date=date(2026, 8, 28)
    )
    metrics = {metric.metric_code: metric for metric in facts.metrics}

    assert metrics["cost_variance"].favorability == expected
    assert metrics["schedule_variance"].favorability == expected
    assert metrics["vac"].favorability == expected
    assert metrics["schedule_variance"].semantic_tooltip.endswith("not schedule days.")


def test_budget_pressure_uses_approved_budget_with_inverse_sign_semantics(monkeypatch) -> None:
    facts = _query(monkeypatch, evm=_evm(EAC=Decimal("100.10"))).get_variance(
        "project-1", as_of_date=date(2026, 8, 28)
    )
    pressure = next(metric for metric in facts.metrics if metric.metric_code == "budget_pressure")

    assert pressure.value == Decimal("0.10")
    assert pressure.favorability == "unfavorable"
    assert pressure.source_revision == "Budget r2 / Forecast r3"
    assert pressure.semantic_tooltip.startswith("Estimate at Completion")


def test_missing_forecast_preserves_independent_cv_and_sv(monkeypatch) -> None:
    facts = _query(
        monkeypatch,
        evm=_evm(
            availability="forecast_unavailable",
            unavailable_reason="No approved Forecast exists for this as-of date.",
            EAC=None,
            VAC=None,
        ),
    ).get_variance("project-1", as_of_date=date(2026, 8, 28))
    metrics = {metric.metric_code: metric for metric in facts.metrics}

    assert metrics["cost_variance"].availability == "available"
    assert metrics["schedule_variance"].availability == "available"
    assert metrics["vac"].availability == "forecast_unavailable"
    assert metrics["budget_pressure"].availability == "forecast_unavailable"
    assert metrics["budget_pressure"].value is None


def test_missing_approved_budget_makes_only_budget_pressure_unavailable(monkeypatch) -> None:
    facts = _query(monkeypatch, basis=_basis(approved_budget_id=None)).get_variance(
        "project-1", as_of_date=date(2026, 8, 28)
    )
    metrics = {metric.metric_code: metric for metric in facts.metrics}

    assert metrics["vac"].availability == "available"
    assert metrics["budget_pressure"].availability == "budget_unavailable"
    assert metrics["budget_pressure"].favorability == "unavailable"


def test_desktop_tone_consumes_authoritative_favorability(monkeypatch) -> None:
    facts = _query(monkeypatch, evm=_evm(CV=Decimal("-1"), EAC=Decimal("101"))).get_variance(
        "project-1", as_of_date=date(2026, 8, 28)
    )
    dto = serialize_performance_variance(facts)
    metrics = {metric.code: metric for metric in dto.metrics}

    assert metrics["cost_variance"].tone == "danger"
    assert metrics["budget_pressure"].tone == "danger"
    assert metrics["vac"].tone == "success"
