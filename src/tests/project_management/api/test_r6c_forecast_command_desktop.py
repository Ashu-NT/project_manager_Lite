from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.application.financials.forecasts.commands.generation import (
    ForecastGenerationCommands,
)
from src.core.modules.project_management.application.financials.forecasts.dto.commands.forecast_generation import (
    FinancialGenerateForecastCommand,
    FinancialManualEtcCommand,
    FinancialRiskContingencyCommand,
)
from src.core.modules.project_management.application.financials.forecasts.dto.commands.forecast_lifecycle import (
    FinancialVersionedForecastCommand,
)
from src.core.modules.project_management.application.financials.forecasts.dto.responses.mutations import (
    FinancialForecastMutationDto,
)
from src.core.platform.common.exceptions import ValidationError


class _ForecastActor:
    def __init__(self, user_session, calls) -> None:
        self._user_session = user_session
        self.calls = calls

    @property
    def current_actor_user_id(self):
        principal = self._user_session.principal
        return getattr(principal, "user_id", None)


class _GenerationCommands(_ForecastActor):
    def generate_draft(
        self, command: FinancialGenerateForecastCommand
    ) -> FinancialForecastMutationDto:
        self.calls["generated"] = command
        return FinancialForecastMutationDto(
            forecast_id="forecast-1",
            project_id=command.project_id,
            status="draft",
            row_version=1,
        )


class _LifecycleCommands(_ForecastActor):
    def submit_forecast(
        self, command: FinancialVersionedForecastCommand
    ) -> FinancialForecastMutationDto:
        self.calls["versioned"] = ("submit", command)
        return FinancialForecastMutationDto(
            forecast_id=command.forecast_id,
            project_id="project-1",
            status="submitted",
            row_version=4,
        )


class _ApprovalCommands(_ForecastActor):
    def request_forecast_approval(
        self, command: FinancialVersionedForecastCommand
    ) -> FinancialForecastMutationDto:
        self.calls["versioned"] = ("request", command)
        return FinancialForecastMutationDto(
            forecast_id=command.forecast_id,
            project_id="project-1",
            status="submitted",
            row_version=4,
            approval_request_id="approval-1",
        )


class _Boundary:
    def __init__(self) -> None:
        self._user_session = SimpleNamespace(
            principal=SimpleNamespace(user_id="actor-1")
        )
        self.calls = {"generated": None, "versioned": None}
        self.generation = _GenerationCommands(self._user_session, self.calls)
        self.lifecycle = _LifecycleCommands(self._user_session, self.calls)
        self.approval = _ApprovalCommands(self._user_session, self.calls)

    @property
    def generated(self):
        return self.calls["generated"]

    @property
    def versioned(self):
        return self.calls["versioned"]

    def forecast_generation(self, command):
        return command(self.generation)

    def forecast_lifecycle(self, command):
        return command(self.lifecycle)

    def forecast_approval(self, command):
        return command(self.approval)


def test_generate_forecast_passes_command_unchanged_to_boundary() -> None:
    boundary = _Boundary()
    api = ProjectManagementFinancialsDesktopApi(
        finance_governance_commands=boundary  # type: ignore[arg-type]
    )

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

    command = boundary.generated
    assert command.project_id == "project-1"
    assert command.manual_estimates[0].amount == "1250.50"
    assert command.risk_contingencies[0].amount == "400.00"
    assert command.as_of_date == "2026-09-01"
    assert result.forecast_id == "forecast-1"
    assert result == FinancialForecastMutationDto("forecast-1", "project-1", "draft", 1)


def test_submit_and_request_approval_preserve_expected_version() -> None:
    boundary = _Boundary()
    api = ProjectManagementFinancialsDesktopApi(
        finance_governance_commands=boundary  # type: ignore[arg-type]
    )
    command = FinancialVersionedForecastCommand(
        forecast_id="forecast-1", expected_version=3, notes="Ready"
    )

    submitted = api.submit_forecast(command)
    assert boundary.versioned == ("submit", command)
    assert boundary.versioned[1] is command
    assert submitted.status == "submitted"

    requested = api.request_forecast_approval(command)
    assert boundary.versioned == ("request", command)
    assert boundary.versioned[1] is command
    assert requested.approval_request_id == "approval-1"
    assert requested.status == "submitted"


@pytest.mark.parametrize("amount", ("NaN", "Infinity", "not-money"))
def test_generate_forecast_rejects_non_canonical_or_non_finite_money(
    amount: str,
) -> None:
    boundary = _Boundary()
    handler = object.__new__(ForecastGenerationCommands)
    handler._user_session = boundary._user_session  # type: ignore[assignment]
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
        handler.generate_draft(command)
    assert exc.value.code == "PROJECT_FORECAST_AMOUNT_INVALID"


def test_generate_forecast_requires_authenticated_actor() -> None:
    boundary = _Boundary()
    boundary._user_session.principal = None
    handler = object.__new__(ForecastGenerationCommands)
    handler._user_session = boundary._user_session  # type: ignore[assignment]

    with pytest.raises(ValidationError) as exc:
        handler.generate_draft(
            FinancialGenerateForecastCommand(
                project_id="project-1",
                name="Unauthenticated forecast",
                as_of_date="2026-09-01",
            )
        )
    assert exc.value.code == "FORECAST_ACTOR_REQUIRED"
