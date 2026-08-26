from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.api.desktop.financials.builders import (
    commitment_builder,
    forecast_builder,
)


class _FinanceService:
    def get_finance_snapshot(self, project_id):
        assert project_id == "project-1"
        return SimpleNamespace(
            budget=Decimal("1000"),
            actual=Decimal("400"),
            committed=Decimal("150"),
            available=Decimal("450"),
            forecast_etc=Decimal("500"),
            estimate_at_completion=Decimal("900"),
            variance_at_completion=Decimal("100"),
            approved_forecast_revision=3,
            approved_forecast_as_of=date(2026, 8, 1),
            commitment_rate_percent=Decimal("15"),
        )


class _CommitmentService:
    def list_for_project(
        self,
        project_id,
        *,
        offset,
        limit,
        sort_key,
        sort_direction,
    ):
        assert project_id == "project-1"
        assert (offset, limit) == (10, 20)
        assert (sort_key, sort_direction) == ("metaText", "desc")
        return [
            SimpleNamespace(
                id="commitment-line-1",
                purchase_order_line_id="po-line-1",
                state=SimpleNamespace(value="partially_received"),
                amount=1000,
                matched_amount=400,
                remaining_money=SimpleNamespace(amount=600),
                currency_code="EUR",
                task_id="task-1",
                ordered_quantity=10,
                quantity_unit="EA",
                order_date=None,
                expected_delivery_date=None,
                source_revision=3,
            )
        ], 50


def _api(**dependencies) -> ProjectManagementFinancialsDesktopApi:
    return ProjectManagementFinancialsDesktopApi(
        finance_service=_FinanceService(),
        financial_configuration_service=SimpleNamespace(
            get_profile=lambda _project_id: SimpleNamespace(currency_code="EUR")
        ),
        **dependencies,
    )


def test_financial_desktop_maps_approved_forecast_and_commitment_controls() -> None:
    api = _api()

    forecast = api.get_cost_forecast("project-1")
    commitment = api.get_commitment_summary("project-1")

    assert forecast.basis == "approved_forecast"
    assert forecast.eac_label == "EUR 900.00"
    assert forecast.forecast_revision == 3
    assert commitment.commitment_rate_pct == 15.0
    assert commitment.available_after_commitment_label == "EUR 450.00"


def test_financial_desktop_requires_canonical_finance_service() -> None:
    api = ProjectManagementFinancialsDesktopApi()

    with pytest.raises(RuntimeError, match="finance service"):
        api.get_cost_forecast("project-1")
    with pytest.raises(RuntimeError, match="finance service"):
        api.get_commitment_summary("project-1")


def test_financial_desktop_maps_paged_canonical_commitment_lines() -> None:
    page = _api(commitment_service=_CommitmentService()).list_commitments(
        "project-1", offset=10, limit=20
    )

    assert page.total == 50
    assert page.offset == 10
    assert page.limit == 20
    assert page.sort_key == "metaText"
    assert page.sort_direction == "desc"
    assert page.items[0].state == "partially_received"
    assert page.items[0].amount_label == "EUR 1,000.00"
    assert page.items[0].matched_amount_label == "EUR 400.00"
    assert page.items[0].remaining_amount_label == "EUR 600.00"


def test_desktop_finance_builders_are_mapping_only() -> None:
    source = inspect.getsource(forecast_builder) + inspect.getsource(commitment_builder)

    assert "max(" not in source
    assert "_compute_etc_eac" not in source
    assert "ForecastCostService" not in source
