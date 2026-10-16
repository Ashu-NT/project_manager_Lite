from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.core.modules.project_management.application.financials.forecasts.dto.commands.forecast_estimates import (
    ManualEtcEstimate,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
)
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError


def test_stale_forecast_submit_is_rejected(services) -> None:
    project = services["project_create"].create_project(ProjectCreateCommand(name="Stale Forecast submit", financial_currency_code="USD"))
    cost_code = services["finance_governance_commands"].cost_code(
        lambda handler: handler.create_cost_code(
            code="R6C-STALE-SUBMIT", name="Stale submit"
        )
    )
    services["forecast_version_query"]
    forecast = services["finance_governance_commands"].forecast_lifecycle(
        lambda handler: handler.create_forecast(
            project.id,
            name="Stale candidate",
            as_of_date=date(2026, 9, 1),
            generation_mode=ForecastGenerationMode.MANUAL,
            created_by="admin",
        )
    )
    stale_version = forecast.row_version
    services["finance_governance_commands"].forecast_lines(
        lambda handler: handler.add_line(
            forecast.id,
            cost_code_id=cost_code.id,
            description="Updated after the stale read",
            amount=Decimal("10.00"),
            source_kind=ForecastLineSourceKind.MANUAL,
            source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
            created_by="admin",
            expected_forecast_version=stale_version,
        )
    )

    with pytest.raises(ConcurrencyError) as exc:
        services["finance_governance_commands"].forecast_lifecycle(
            lambda handler: handler.submit_forecast(
                forecast.id,
                submitted_by="admin",
                expected_version=stale_version,
            )
        )
    assert exc.value.code == "STALE_WRITE"


def test_generation_cannot_create_a_second_open_forecast(services) -> None:
    project = services["project_create"].create_project(ProjectCreateCommand(name="Single open Forecast", financial_currency_code="USD"))
    cost_code = services["finance_governance_commands"].cost_code(
        lambda handler: handler.create_cost_code(
            code="R6C-ONE-OPEN", name="One open Forecast"
        )
    )
    services["finance_governance_commands"]
    estimate = ManualEtcEstimate(
        cost_code_id=cost_code.id,
        description="Remaining estimate",
        amount=Decimal("25.00"),
    )
    services["finance_governance_commands"].forecast_generation(
        lambda handler: handler.generate_draft(
            project.id,
            name="First open Forecast",
            as_of_date=date(2026, 9, 1),
            generated_by="admin",
            manual_estimates=(estimate,),
        )
    )

    with pytest.raises(BusinessRuleError) as exc:
        services["finance_governance_commands"].forecast_generation(
            lambda handler: handler.generate_draft(
                project.id,
                name="Conflicting open Forecast",
                as_of_date=date(2026, 9, 2),
                generated_by="admin",
                manual_estimates=(estimate,),
            )
        )
    assert exc.value.code == "PROJECT_FORECAST_OPEN_VERSION_EXISTS"
