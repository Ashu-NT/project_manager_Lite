"""Phase 5 verification: PMTimeController routes entry mutations through
_refresh_entry_cb (scoped) and period mutations through _facade_refresh.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

_HAS_QT = False
try:
    from PySide6.QtCore import QObject  # noqa: F401
    _HAS_QT = True
except Exception:
    pass

pytestmark = pytest.mark.skipif(not _HAS_QT, reason="PySide6 required")

_MUTATION_RUNNER = (
    "src.ui_qml.modules.project_management.controllers.tasks"
    ".pm_time_controller.run_mutation"
)


def _build_controller(*, facade_refresh=None, entry_refresh=None):
    from src.ui_qml.modules.project_management.controllers.tasks.pm_time_controller import (
        PMTimeController,
    )

    ctrl = PMTimeController(
        presenter=MagicMock(),
        facade_refresh=facade_refresh or MagicMock(),
        refresh_time_entries=entry_refresh,
        set_is_busy=MagicMock(),
        set_error_message=MagicMock(),
        set_feedback_message=MagicMock(),
    )
    return ctrl


def _stub_run_mutation():
    """Patch run_mutation so slots complete without needing a Qt event loop."""
    m = MagicMock(return_value={"ok": True, "message": ""})
    return patch(_MUTATION_RUNNER, m), m


# ── Constructor routing ────────────────────────────────────────────────────────

class TestCallbackRouting:
    def test_scoped_refresh_stored_when_provided(self):
        scoped = MagicMock()
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=scoped)
        assert ctrl._refresh_entry_cb is scoped

    def test_facade_refresh_used_as_fallback_when_entry_refresh_none(self):
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=None)
        assert ctrl._refresh_entry_cb is facade

    def test_scoped_and_facade_are_independent_when_both_provided(self):
        scoped = MagicMock()
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=scoped)
        assert ctrl._facade_refresh is facade
        assert ctrl._refresh_entry_cb is scoped
        assert ctrl._facade_refresh is not ctrl._refresh_entry_cb

    def test_facade_always_stored_on_facade_attribute(self):
        scoped = MagicMock()
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=scoped)
        assert ctrl._facade_refresh is facade

    def test_facade_stored_even_when_entry_refresh_absent(self):
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=None)
        assert ctrl._facade_refresh is facade


# ── Entry-level mutations use scoped refresh ───────────────────────────────────

class TestEntryMutationsUseScoped:
    def test_add_entry_passes_scoped_as_on_success(self):
        scoped = MagicMock()
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=scoped)
        patcher, mock_run = _stub_run_mutation()
        with patcher:
            ctrl.addTaskTimeEntry({"taskId": "t-1", "hours": 8})
        _, kw = mock_run.call_args
        assert kw["on_success"] is scoped

    def test_update_entry_passes_scoped_as_on_success(self):
        scoped = MagicMock()
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=scoped)
        patcher, mock_run = _stub_run_mutation()
        with patcher:
            ctrl.updateTaskTimeEntry({"id": "e-1", "hours": 4})
        _, kw = mock_run.call_args
        assert kw["on_success"] is scoped

    def test_delete_entry_passes_scoped_as_on_success(self):
        scoped = MagicMock()
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=scoped)
        patcher, mock_run = _stub_run_mutation()
        with patcher:
            ctrl.deleteTaskTimeEntry("e-99")
        _, kw = mock_run.call_args
        assert kw["on_success"] is scoped

    def test_add_entry_on_success_is_facade_when_no_scoped(self):
        """Fallback: entry refresh not provided → _refresh_entry_cb == facade_refresh."""
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=None)
        patcher, mock_run = _stub_run_mutation()
        with patcher:
            ctrl.addTaskTimeEntry({"taskId": "t-1", "hours": 8})
        _, kw = mock_run.call_args
        assert kw["on_success"] is facade

    def test_entry_mutations_do_not_pass_facade_when_scoped_provided(self):
        scoped = MagicMock()
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=scoped)
        patcher, mock_run = _stub_run_mutation()
        with patcher:
            ctrl.updateTaskTimeEntry({"id": "e-2", "hours": 2})
        _, kw = mock_run.call_args
        assert kw["on_success"] is not facade


# ── Period-level mutations always use facade ───────────────────────────────────

class TestPeriodMutationsUseFacade:
    def test_submit_period_passes_facade_as_on_success(self):
        scoped = MagicMock()
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=scoped)
        patcher, mock_run = _stub_run_mutation()
        with patcher:
            ctrl.submitTaskPeriod({"periodId": "pd-1"})
        _, kw = mock_run.call_args
        assert kw["on_success"] is facade

    def test_lock_period_passes_facade_as_on_success(self):
        scoped = MagicMock()
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=scoped)
        patcher, mock_run = _stub_run_mutation()
        with patcher:
            ctrl.lockTaskPeriod({"periodId": "pd-1"})
        _, kw = mock_run.call_args
        assert kw["on_success"] is facade

    def test_unlock_period_passes_facade_as_on_success(self):
        scoped = MagicMock()
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=scoped)
        patcher, mock_run = _stub_run_mutation()
        with patcher:
            ctrl.unlockTaskPeriod({"periodId": "pd-1"})
        _, kw = mock_run.call_args
        assert kw["on_success"] is facade

    def test_period_mutations_do_not_use_scoped_refresh(self):
        scoped = MagicMock()
        facade = MagicMock()
        ctrl = _build_controller(facade_refresh=facade, entry_refresh=scoped)
        patcher, mock_run = _stub_run_mutation()
        with patcher:
            ctrl.submitTaskPeriod({"periodId": "pd-1"})
        _, kw = mock_run.call_args
        assert kw["on_success"] is not scoped
