from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt

from src.core.modules.project_management.api.desktop.financials import (
    FinancialCreateManualActualCommand,
    FinancialDecideActualCommand,
    FinancialPostActualCommand,
    FinancialReverseActualCommand,
    FinancialVersionedActualCommand,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.ui_qml.modules.project_management.controllers.financials.financials_workspace_controller import (
    ProjectManagementFinancialsWorkspaceController,
)
from src.ui_qml.modules.project_management.presenters.financials.command_handler import (
    approve_actual,
    post_actual,
    reject_actual,
    reverse_actual,
    submit_actual,
)


# ---------------------------------------------------------------------------
# Presenter / command_handler layer — payload -> desktop-API command mapping.
# ---------------------------------------------------------------------------


class _RecordingDesktopApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def submit_actual(self, command):
        self.calls.append(("submit_actual", command))

    def approve_actual(self, command):
        self.calls.append(("approve_actual", command))

    def reject_actual(self, command):
        self.calls.append(("reject_actual", command))

    def post_actual(self, command):
        self.calls.append(("post_actual", command))

    def reverse_actual(self, command):
        self.calls.append(("reverse_actual", command))


def test_submit_actual_builds_versioned_command():
    api = _RecordingDesktopApi()
    submit_actual(api, {"entryId": "entry-1", "rowVersion": 3})

    name, command = api.calls[0]
    assert name == "submit_actual"
    assert command == FinancialVersionedActualCommand(entry_id="entry-1", expected_version=3)


def test_approve_actual_defaults_notes_to_empty_string():
    api = _RecordingDesktopApi()
    approve_actual(api, {"entryId": "entry-1", "rowVersion": 2})

    name, command = api.calls[0]
    assert name == "approve_actual"
    assert command == FinancialDecideActualCommand(
        entry_id="entry-1", expected_version=2, notes=""
    )


def test_reject_actual_forwards_notes():
    api = _RecordingDesktopApi()
    reject_actual(api, {"entryId": "entry-1", "rowVersion": 2, "notes": "Wrong cost code."})

    name, command = api.calls[0]
    assert name == "reject_actual"
    assert command.notes == "Wrong cost code."


def test_post_actual_requires_posting_date():
    api = _RecordingDesktopApi()
    with pytest.raises(ValueError, match="Posting date"):
        post_actual(api, {"entryId": "entry-1", "rowVersion": 1})
    assert api.calls == []


def test_post_actual_builds_command_with_posting_date():
    api = _RecordingDesktopApi()
    post_actual(api, {"entryId": "entry-1", "rowVersion": 1, "postingDate": "2026-01-13"})

    name, command = api.calls[0]
    assert name == "post_actual"
    assert command == FinancialPostActualCommand(
        entry_id="entry-1", expected_version=1, posting_date=date(2026, 1, 13)
    )


def test_reverse_actual_requires_reason():
    api = _RecordingDesktopApi()
    with pytest.raises(ValueError, match="reason"):
        reverse_actual(
            api,
            {
                "entryId": "entry-1",
                "rowVersion": 1,
                "commandId": "cmd-1",
                "postingDate": "2026-01-14",
                "reason": "",
            },
        )
    assert api.calls == []


def test_reverse_actual_builds_full_command():
    api = _RecordingDesktopApi()
    reverse_actual(
        api,
        {
            "entryId": "entry-1",
            "rowVersion": 4,
            "commandId": "cmd-1",
            "postingDate": "2026-01-14",
            "reason": "Corrected after audit.",
        },
    )

    name, command = api.calls[0]
    assert name == "reverse_actual"
    assert command == FinancialReverseActualCommand(
        entry_id="entry-1",
        expected_version=4,
        command_id="cmd-1",
        posting_date=date(2026, 1, 14),
        reason="Corrected after audit.",
    )


# ---------------------------------------------------------------------------
# Controller layer — Slot delegation, busy state, error propagation, and
# post-success refresh, using a fake presenter so this stays a controller
# unit test rather than a full desktop-API integration test (the desktop
# API path is already covered end to end in
# test_project_finance_command_cutover.py).
# ---------------------------------------------------------------------------


class _FakeFinancialsWorkspacePresenter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.fail_with: Exception | None = None
        self._desktop_api = None

    def build_workspace_state(self, **_kwargs):
        raise RuntimeError("workspace state is not faked in this test")

    def create_manual_actual(self, payload):
        self._record("create_manual_actual", payload)

    def submit_actual(self, payload):
        self._record("submit_actual", payload)

    def approve_actual(self, payload):
        self._record("approve_actual", payload)

    def reject_actual(self, payload):
        self._record("reject_actual", payload)

    def post_actual(self, payload):
        self._record("post_actual", payload)

    def reverse_actual(self, payload):
        self._record("reverse_actual", payload)

    def _record(self, name: str, payload: dict) -> None:
        self.calls.append((name, dict(payload)))
        if self.fail_with is not None:
            raise self.fail_with


@pytest.fixture
def controller(qapp):
    fake_presenter = _FakeFinancialsWorkspacePresenter()
    workspace_presenter = MagicMock()
    workspace_presenter.build_view_model.side_effect = RuntimeError(
        "workspace view model is not faked in this test"
    )
    ctrl = ProjectManagementFinancialsWorkspaceController(
        workspace_presenter=workspace_presenter,
        financials_workspace_presenter=fake_presenter,
    )
    ctrl._fake_presenter = fake_presenter
    return ctrl


def test_submit_actual_slot_delegates_and_reports_success(controller):
    # Note: the mutation's own result — {"ok", "message"} — is checked here,
    # not controller.feedbackMessage. run_mutation()'s on_success callback
    # (_request_domain_refresh) immediately triggers another refresh() call
    # after every successful mutation, and that refresh clears/overwrites
    # feedbackMessage/errorMessage with whatever that unrelated refresh
    # produces — a pre-existing controller behavior, not something this
    # slot-delegation test should depend on.
    result = controller.submitActual({"entryId": "entry-1", "rowVersion": 1})

    assert result["ok"] is True
    assert result["message"] == "Actual submitted for approval."
    assert controller._fake_presenter.calls == [
        ("submit_actual", {"entryId": "entry-1", "rowVersion": 1})
    ]


def test_approve_actual_slot_reports_success_message(controller):
    result = controller.approveActual({"entryId": "entry-1", "rowVersion": 1})

    assert result["ok"] is True
    assert result["message"] == "Actual approval decision recorded."


def test_reject_actual_slot_reports_success_message(controller):
    result = controller.rejectActual({"entryId": "entry-1", "rowVersion": 1, "notes": "Bad code."})

    assert result["ok"] is True
    assert result["message"] == "Actual returned to draft."


def test_post_actual_slot_reports_success_message(controller):
    result = controller.postActual(
        {"entryId": "entry-1", "rowVersion": 1, "postingDate": "2026-01-13"}
    )

    assert result["ok"] is True
    assert result["message"] == "Actual posted to the ledger."


def test_reverse_actual_slot_reports_success_message(controller):
    result = controller.reverseActual(
        {
            "entryId": "entry-1",
            "rowVersion": 1,
            "commandId": "cmd-1",
            "postingDate": "2026-01-14",
            "reason": "Correction.",
        }
    )

    assert result["ok"] is True
    assert result["message"] == "Reversal posted."


def test_approve_actual_slot_propagates_backend_denial_without_crashing(controller):
    controller._fake_presenter.fail_with = BusinessRuleError(
        "Permission denied for approve project cost entry. Missing 'project_cost.approve'.",
        code="PERMISSION_DENIED",
    )

    result = controller.approveActual({"entryId": "entry-1", "rowVersion": 1})

    assert result["ok"] is False
    assert "project_cost.approve" in result["message"]
    assert controller.errorMessage == result["message"]
    assert controller.feedbackMessage == ""
    assert controller.isBusy is False


def test_forecast_controller_keeps_master_and_detail_query_state_independent(
    controller,
) -> None:
    controller.refresh = MagicMock()
    controller._forecast_version_page = 4
    controller._forecast_line_page = 3

    controller.selectForecastVersion("forecast-2")
    assert controller.selectedForecastId == "forecast-2"
    assert controller._forecast_version_page == 4
    assert controller._forecast_line_page == 1

    controller._forecast_line_page = 3
    controller.setForecastVersionSort("metaText", Qt.AscendingOrder.value)
    assert controller._forecast_version_page == 1
    assert controller._forecast_line_page == 3
    assert controller.forecastVersionSortKey == "metaText"

    controller._forecast_version_page = 4
    controller.setForecastLineSort("supportingText", Qt.DescendingOrder.value)
    assert controller._forecast_version_page == 4
    assert controller._forecast_line_page == 1
    assert controller.forecastLineSortKey == "supportingText"


def test_forecast_controller_filter_and_project_reset_rules(controller) -> None:
    controller.refresh = MagicMock()
    controller._forecast_version_page = 5
    controller._forecast_line_page = 4

    controller.setForecastVersionFilters("alpha", "approved", "manual")
    assert controller._forecast_version_page == 1
    assert controller._forecast_line_page == 4
    assert controller.forecastVersionSearch == "alpha"
    assert controller.forecastVersionStatus == "approved"
    assert controller.forecastGenerationMode == "manual"

    controller.setForecastLineFilters("risk", "risk")
    assert controller._forecast_line_page == 1
    assert controller.forecastLineSearch == "risk"
    assert controller.forecastLineSourceType == "risk"

    controller._set_selected_project_id("project-a")
    controller._set_selected_forecast_id("forecast-a")
    controller._forecast_version_page = 3
    controller._forecast_line_page = 2
    controller.selectProject("project-b")
    assert controller.selectedForecastId == ""
    assert controller._forecast_version_page == 1
    assert controller._forecast_line_page == 1


def test_forecast_refresh_rejects_stale_a_b_c_selection_responses(controller) -> None:
    controller._workspace_loaded = True
    controller._shell_loaded = True
    controller._active_destination = "planning"
    controller._active_subsection = "forecast"
    controller._set_selected_project_id("project-a")
    controller._set_selected_forecast_id("forecast-a")

    state_a = object()
    state_b = object()
    state_c = object()
    call_count = 0

    def build_destination_state(**_kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            controller._set_selected_forecast_id("forecast-b")
            controller.refresh()
            return state_a
        if call_count == 2:
            controller._set_selected_forecast_id("forecast-c")
            controller.refresh()
            return state_b
        return state_c

    controller._financials_workspace_presenter.build_destination_state = MagicMock(
        side_effect=build_destination_state
    )
    controller._apply_destination_state = MagicMock()

    controller.refresh()

    assert call_count == 3
    assert controller.selectedForecastId == "forecast-c"
    controller._apply_destination_state.assert_called_once_with(
        "planning", "forecast", state_c
    )
