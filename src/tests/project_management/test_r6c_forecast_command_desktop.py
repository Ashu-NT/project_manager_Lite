from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.api.desktop.financials.commands.forecasts import (
    FinancialGenerateForecastCommand,
    FinancialManualEtcCommand,
    FinancialRiskContingencyCommand,
    FinancialVersionedForecastCommand,
)
from src.core.platform.common.exceptions import ValidationError


class _Boundary:
    def __init__(self) -> None:
        self._user_session = SimpleNamespace(
            principal=SimpleNamespace(user_id="actor-1")
        )
        self.generation_service = SimpleNamespace(
            _user_session=SimpleNamespace(principal=SimpleNamespace(user_id="actor-1"))
        )
        self.version_service = SimpleNamespace(
            _user_session=SimpleNamespace(principal=SimpleNamespace(user_id="actor-1"))
        )
        self.generated = None
        self.versioned = None

    def forecast_generation(self, command, *, project_id):
        self.generated = (command, project_id)
        return command(self)

    def generate_draft(self, project_id, **kwargs):
        self.generated = (project_id, kwargs)
        return SimpleNamespace(
            forecast=SimpleNamespace(
                id="forecast-1",
                project_id=project_id,
                status=SimpleNamespace(value="draft"),
                row_version=1,
            )
        )

    def forecast_version(self, command, *, project_id=None):
        return command(self)

    def submit_forecast(self, forecast_id, **kwargs):
        self.versioned = ("submit", forecast_id, kwargs)
        return SimpleNamespace(
            id=forecast_id,
            project_id="project-1",
            status=SimpleNamespace(value="submitted"),
            row_version=4,
        )

    def request_forecast_approval(self, forecast_id, **kwargs):
        self.versioned = ("request", forecast_id, kwargs)
        return SimpleNamespace(
            forecast_id=forecast_id,
            project_id="project-1",
            forecast_status=SimpleNamespace(value="submitted"),
            row_version=4,
            approval_request_id="approval-1",
        )


def test_generate_forecast_maps_typed_decimal_and_dates_to_boundary() -> None:
    boundary = _Boundary()
    api = ProjectManagementFinancialsDesktopApi(finance_governance_commands=boundary)

    result = api.generate_forecast(
        FinancialGenerateForecastCommand(
            project_id="project-1",
            name="September Forecast",
            as_of_date="2026-09-01",
            manual_estimates=(
                FinancialManualEtcCommand(
                    cost_code_id="cc-1",
                    task_id="task-1",
                    description="Completion estimate",
                    amount="1250.50",
                ),
            ),
            risk_contingencies=(
                FinancialRiskContingencyCommand(
                    risk_id="risk-1",
                    cost_code_id="cc-2",
                    amount="400.00",
                ),
            ),
        )
    )

    project_id, values = boundary.generated
    assert project_id == "project-1"
    assert str(values["manual_estimates"][0].amount) == "1250.50"
    assert str(values["risk_contingencies"][0].amount) == "400.00"
    assert values["generated_by"] == "actor-1"
    assert result.forecast_id == "forecast-1"


def test_submit_and_request_approval_preserve_expected_version() -> None:
    boundary = _Boundary()
    api = ProjectManagementFinancialsDesktopApi(finance_governance_commands=boundary)
    command = FinancialVersionedForecastCommand(
        forecast_id="forecast-1", expected_version=3, notes="Ready"
    )

    submitted = api.submit_forecast(command)
    assert boundary.versioned == (
        "submit",
        "forecast-1",
        {"submitted_by": "actor-1", "expected_version": 3, "notes": "Ready"},
    )
    assert submitted.status == "submitted"

    requested = api.request_forecast_approval(command)
    assert boundary.versioned == (
        "request", "forecast-1", {"expected_version": 3, "notes": "Ready"}
    )
    assert requested.approval_request_id == "approval-1"


@pytest.mark.parametrize("amount", ("NaN", "Infinity", "not-money"))
def test_generate_forecast_rejects_non_canonical_or_non_finite_money(amount: str) -> None:
    boundary = _Boundary()
    api = ProjectManagementFinancialsDesktopApi(finance_governance_commands=boundary)
    command = FinancialGenerateForecastCommand(
        project_id="project-1",
        name="Invalid forecast",
        as_of_date="2026-09-01",
        manual_estimates=(
            FinancialManualEtcCommand(
                cost_code_id="cc-1",
                description="Invalid amount",
                amount=amount,
            ),
        ),
    )

    with pytest.raises(ValidationError) as exc:
        api.generate_forecast(command)
    assert exc.value.code == "PROJECT_FORECAST_AMOUNT_INVALID"


def test_generate_forecast_requires_authenticated_actor() -> None:
    boundary = _Boundary()
    boundary._user_session.principal = None
    api = ProjectManagementFinancialsDesktopApi(finance_governance_commands=boundary)

    with pytest.raises(ValidationError) as exc:
        api.generate_forecast(
            FinancialGenerateForecastCommand(
                project_id="project-1",
                name="Unauthenticated forecast",
                as_of_date="2026-09-01",
            )
        )
    assert exc.value.code == "FORECAST_ACTOR_REQUIRED"
