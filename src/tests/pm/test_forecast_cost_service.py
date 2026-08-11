"""Unit tests for forecasts over the canonical finance snapshot."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.core.modules.project_management.application.financials.forecasts.forecast_service import (
    EACMethod,
    ForecastCostService,
)
from src.core.modules.project_management.application.financials.models.finance_models import (
    FinanceLedgerRow,
)

_PERMISSION_MODULE = (
    "src.core.modules.project_management.application.financials.forecasts.forecast_service"
)


def _ledger_row(*, stage: str, amount: float, cost_type: str = "MATERIAL") -> FinanceLedgerRow:
    return FinanceLedgerRow(
        project_id="p1",
        source_key="CANONICAL",
        source_label="Canonical finance",
        cost_type=cost_type,
        stage=stage,
        amount=amount,
        currency="EUR",
        occurred_on=date(2026, 8, 1),
        reference_type="finance_fact",
        reference_id=f"{stage}-1",
        reference_label=stage.title(),
        task_id=None,
        task_name=None,
        resource_id=None,
        resource_name=None,
        included_in_policy=True,
    )


def _service(
    *,
    planned: float = 1000.0,
    committed: float = 0.0,
    actual: float = 0.0,
    ledger: list[FinanceLedgerRow] | None = None,
) -> ForecastCostService:
    finance = MagicMock()
    finance.get_finance_snapshot.return_value = SimpleNamespace(
        planned=planned,
        committed=committed,
        actual=actual,
    )
    finance.list_cost_ledger.return_value = ledger or []
    projects = MagicMock()
    projects.get.return_value = SimpleNamespace(id="p1", name="Test Project")
    return ForecastCostService(finance, projects)


def _without_permissions():
    return patch.multiple(
        _PERMISSION_MODULE,
        require_permission=MagicMock(),
        require_project_permission=MagicMock(),
    )


def test_commitment_summary_uses_canonical_snapshot_totals() -> None:
    service = _service(planned=3800.0, committed=2500.0, actual=300.0)

    with _without_permissions():
        summary = service.get_commitment_summary("p1")

    assert summary.planned_total == 3800.0
    assert summary.uncommitted_total == 1300.0
    assert summary.committed_total == 2500.0
    assert summary.actual_total == 300.0
    assert summary.exposure == 2200.0


def test_material_rollup_filters_canonical_ledger_by_type_and_stage() -> None:
    rows = [
        _ledger_row(stage="planned", amount=500.0),
        _ledger_row(stage="committed", amount=450.0),
        _ledger_row(stage="actual", amount=200.0),
        _ledger_row(stage="planned", amount=900.0, cost_type="LABOR"),
    ]
    service = _service(ledger=rows)

    with _without_permissions():
        rollup = service.get_material_rollup("p1")

    assert rollup.planned == 500.0
    assert rollup.committed == 450.0
    assert rollup.actual == 200.0
    assert rollup.forecast == 500.0
    assert len(rollup.items) == 3


@pytest.mark.parametrize(
    ("method", "actual", "expected_eac"),
    [
        (EACMethod.BAC_OVER_CPI, 400.0, 800.0),
        (EACMethod.AC_PLUS_ETC_AT_PLAN, 400.0, 900.0),
        (EACMethod.AC_PLUS_ETC_AT_CPI, 400.0, 800.0),
        (EACMethod.MANUAL, 400.0, 1000.0),
    ],
)
def test_compute_forecast_uses_canonical_planned_and_actual(
    method: EACMethod,
    actual: float,
    expected_eac: float,
) -> None:
    service = _service(planned=1000.0, actual=actual)

    with _without_permissions():
        result = service.compute_forecast("p1", 0.5, method=method)

    assert result.bac == 1000.0
    assert result.ac == actual
    assert result.ev == 500.0
    assert result.eac == pytest.approx(expected_eac)


def test_threshold_compares_forecast_to_canonical_plan() -> None:
    service = _service(planned=1000.0)

    with _without_permissions():
        assert service.check_cost_threshold("p1", 1150.0)
        assert not service.check_cost_threshold("p1", 1050.0)
