from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.core.modules.project_management.application.financials.forecasts import (
    ManualEtcEstimate,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
)
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError


def test_stale_forecast_submit_is_rejected(services) -> None:
    project = services["project_service"].create_project(
        "Stale Forecast submit", financial_currency_code="USD"
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="R6C-STALE-SUBMIT", name="Stale submit"
    )
    forecasts = services["forecast_version_service"]
    forecast = forecasts.create_forecast(
        project.id,
        name="Stale candidate",
        as_of_date=date(2026, 9, 1),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )
    stale_version = forecast.row_version
    forecasts.add_line(
        forecast.id,
        cost_code_id=cost_code.id,
        description="Updated after the stale read",
        amount=Decimal("10.00"),
        source_kind=ForecastLineSourceKind.MANUAL,
        source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin",
        expected_forecast_version=stale_version,
    )

    with pytest.raises(ConcurrencyError) as exc:
        forecasts.submit_forecast(
            forecast.id,
            submitted_by="admin",
            expected_version=stale_version,
        )
    assert exc.value.code == "STALE_WRITE"


def test_generation_cannot_create_a_second_open_forecast(services) -> None:
    project = services["project_service"].create_project(
        "Single open Forecast", financial_currency_code="USD"
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="R6C-ONE-OPEN", name="One open Forecast"
    )
    generator = services["forecast_generation_service"]
    estimate = ManualEtcEstimate(
        cost_code_id=cost_code.id,
        description="Remaining estimate",
        amount=Decimal("25.00"),
    )
    generator.generate_draft(
        project.id,
        name="First open Forecast",
        as_of_date=date(2026, 9, 1),
        generated_by="admin",
        manual_estimates=(estimate,),
    )

    with pytest.raises(BusinessRuleError) as exc:
        generator.generate_draft(
            project.id,
            name="Conflicting open Forecast",
            as_of_date=date(2026, 9, 2),
            generated_by="admin",
            manual_estimates=(estimate,),
        )
    assert exc.value.code == "PROJECT_FORECAST_OPEN_VERSION_EXISTS"
