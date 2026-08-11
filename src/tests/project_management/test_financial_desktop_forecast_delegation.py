from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.api.desktop.financials.builders import (
    commitment_builder,
    forecast_builder,
)
from src.core.modules.project_management.application.financials import (
    CommitmentSummary,
    CostForecastResult,
    EACMethod,
)


class _ForecastService:
    def __init__(self) -> None:
        self.forecast_call: tuple | None = None
        self.commitment_call: str | None = None

    def compute_forecast(self, project_id, percent_complete, *, method, threshold_percent):
        self.forecast_call = (project_id, percent_complete, method, threshold_percent)
        return CostForecastResult(
            project_id=project_id,
            method=method,
            bac=1000.0,
            ac=400.0,
            ev=500.0,
            etc=500.0,
            eac=900.0,
            vac=100.0,
            cpi=1.25,
            exceeds_threshold=False,
            threshold_percent=threshold_percent,
        )

    def get_commitment_summary(self, project_id):
        self.commitment_call = project_id
        return CommitmentSummary(
            project_id=project_id,
            planned_total=1000.0,
            uncommitted_total=100.0,
            committed_total=600.0,
            invoiced_total=200.0,
            paid_total=150.0,
            actual_total=250.0,
        )


class _CommitmentService:
    def list_for_project(self, project_id, *, offset, limit):
        assert project_id == "project-1"
        assert (offset, limit) == (10, 20)
        return [
            SimpleNamespace(
                id="commitment-line-1",
                purchase_order_line_id="po-line-1",
                state=SimpleNamespace(value="partially_received"),
                amount=1000,
                matched_amount=400,
                currency_code="EUR",
                task_id="task-1",
                ordered_quantity=10,
                quantity_unit="EA",
                order_date=None,
                expected_delivery_date=None,
                source_revision=3,
            )
        ], 1

def test_financial_desktop_api_delegates_forecast_and_commitment_calculation() -> None:
    service = _ForecastService()
    configuration_service = SimpleNamespace(
        get_profile=lambda _project_id: SimpleNamespace(currency_code="EUR")
    )
    api = ProjectManagementFinancialsDesktopApi(
        financial_configuration_service=configuration_service,
        forecast_service=service,
    )

    forecast = api.get_cost_forecast(
        "project-1",
        percent_complete=0.5,
        method=" AC_ETC_CPI ",
        threshold_percent=12.0,
    )
    commitment = api.get_commitment_summary("project-1")

    assert service.forecast_call == (
        "project-1",
        0.5,
        EACMethod.AC_PLUS_ETC_AT_CPI,
        12.0,
    )
    assert service.commitment_call == "project-1"
    assert forecast.method == EACMethod.AC_PLUS_ETC_AT_CPI.value
    assert forecast.eac_label == "EUR 900.00"
    assert commitment.commitment_rate_pct == 60.0
    assert commitment.exposure_label == "EUR 350.00"


def test_financial_desktop_api_requires_canonical_forecast_service() -> None:
    api = ProjectManagementFinancialsDesktopApi()

    with pytest.raises(RuntimeError, match="forecast service"):
        api.get_cost_forecast("project-1")
    with pytest.raises(RuntimeError, match="forecast service"):
        api.get_commitment_summary("project-1")


def test_financial_desktop_api_maps_paged_canonical_commitment_lines() -> None:
    api = ProjectManagementFinancialsDesktopApi(
        commitment_service=_CommitmentService()
    )

    page = api.list_commitments("project-1", offset=10, limit=20)

    assert page.total == 1
    assert page.offset == 10
    assert page.limit == 20
    assert page.items[0].state == "partially_received"
    assert page.items[0].amount_label == "EUR 1,000.00"
    assert page.items[0].matched_amount_label == "EUR 400.00"
    assert page.items[0].remaining_amount_label == "EUR 600.00"


def test_desktop_forecast_builders_do_not_contain_application_formulas() -> None:
    source = inspect.getsource(forecast_builder) + inspect.getsource(commitment_builder)

    assert "list_cost_items_for_project" not in source
    assert "_compute_etc_eac" not in source
    assert "_build_from_cost_items" not in source
