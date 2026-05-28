"""Phase 10 verification: PMCapabilityController exposes correct permission flags."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

_HAS_QT = False
try:
    from PySide6.QtCore import QObject  # noqa: F401
    _HAS_QT = True
except Exception:
    pass

pytestmark = pytest.mark.skipif(not _HAS_QT, reason="PySide6 required")


def _build(*, engine=None, session_fn=None):
    from src.ui_qml.modules.project_management.controllers.common.pm_capability_controller import (
        PMCapabilityController,
    )
    return PMCapabilityController(
        auth_engine=engine,
        user_session_provider=session_fn,
    )


def _engine_allowing(*codes):
    """Return a mock AuthorizationEngine that only allows the specified codes."""
    m = MagicMock()
    m.has_permission.side_effect = lambda session, code: code in codes
    return m


def _engine_denying(*codes):
    """Return a mock AuthorizationEngine that denies the specified codes."""
    m = MagicMock()
    m.has_permission.side_effect = lambda session, code: code not in codes
    return m


# ── Default permissive behavior ───────────────────────────────────────────────

class TestDefaultPermissive:
    def test_all_flags_true_when_no_engine(self):
        ctrl = _build()
        assert ctrl.canApproveBaseline is True
        assert ctrl.canApplyLeveling is True
        assert ctrl.canManageSkills is True
        assert ctrl.canRequestAssignmentOverride is True
        assert ctrl.canImport is True
        assert ctrl.canApprovePmRequest is True

    def test_flags_remain_true_after_refresh_with_no_engine(self):
        ctrl = _build()
        ctrl.refresh()
        assert ctrl.canApproveBaseline is True
        assert ctrl.canImport is True


# ── Permission code routing ───────────────────────────────────────────────────

class TestPermissionCodeRouting:
    def test_can_approve_baseline_maps_to_correct_code(self):
        engine = _engine_allowing("pm.baseline.approve")
        ctrl = _build(engine=engine)
        assert ctrl.canApproveBaseline is True
        assert ctrl.canApplyLeveling is False

    def test_can_apply_leveling_maps_to_correct_code(self):
        engine = _engine_allowing("pm.schedule.apply_leveling")
        ctrl = _build(engine=engine)
        assert ctrl.canApplyLeveling is True
        assert ctrl.canApproveBaseline is False

    def test_can_manage_skills_maps_to_correct_code(self):
        engine = _engine_allowing("pm.resource.manage_skills")
        ctrl = _build(engine=engine)
        assert ctrl.canManageSkills is True
        assert ctrl.canImport is False

    def test_can_request_assignment_override_maps_to_correct_code(self):
        engine = _engine_allowing("pm.assignment.request_override")
        ctrl = _build(engine=engine)
        assert ctrl.canRequestAssignmentOverride is True
        assert ctrl.canApproveBaseline is False

    def test_can_import_maps_to_correct_code(self):
        engine = _engine_allowing("pm.import.execute")
        ctrl = _build(engine=engine)
        assert ctrl.canImport is True
        assert ctrl.canManageSkills is False

    def test_can_approve_pm_request_maps_to_correct_code(self):
        engine = _engine_allowing("pm.request.approve")
        ctrl = _build(engine=engine)
        assert ctrl.canApprovePmRequest is True
        assert ctrl.canImport is False


# ── Denial behavior ───────────────────────────────────────────────────────────

class TestDenialBehavior:
    def test_all_flags_false_when_engine_denies_everything(self):
        engine = _engine_allowing()  # allows nothing
        ctrl = _build(engine=engine)
        assert ctrl.canApproveBaseline is False
        assert ctrl.canApplyLeveling is False
        assert ctrl.canManageSkills is False
        assert ctrl.canRequestAssignmentOverride is False
        assert ctrl.canImport is False
        assert ctrl.canApprovePmRequest is False

    def test_only_denied_flag_is_false(self):
        engine = _engine_denying("pm.import.execute")
        ctrl = _build(engine=engine)
        assert ctrl.canImport is False
        assert ctrl.canApproveBaseline is True
        assert ctrl.canApplyLeveling is True
        assert ctrl.canManageSkills is True


# ── Session provider ─────────────────────────────────────────────────────────

class TestSessionProvider:
    def test_session_provider_called_with_session(self):
        sentinel = object()
        engine = MagicMock()
        engine.has_permission.return_value = True
        ctrl = _build(engine=engine, session_fn=lambda: sentinel)
        # has_permission should have been called with the sentinel session
        calls = engine.has_permission.call_args_list
        assert all(c.args[0] is sentinel for c in calls)

    def test_none_session_provider_passes_none(self):
        engine = MagicMock()
        engine.has_permission.return_value = True
        ctrl = _build(engine=engine, session_fn=None)
        calls = engine.has_permission.call_args_list
        assert all(c.args[0] is None for c in calls)


# ── Refresh ──────────────────────────────────────────────────────────────────

class TestRefresh:
    def test_refresh_recomputes_flags(self):
        engine = MagicMock()
        engine.has_permission.return_value = False
        ctrl = _build(engine=engine)
        assert ctrl.canImport is False

        engine.has_permission.return_value = True
        ctrl.refresh()
        assert ctrl.canImport is True

    def test_engine_exception_falls_back_to_true(self):
        engine = MagicMock()
        engine.has_permission.side_effect = RuntimeError("auth unavailable")
        ctrl = _build(engine=engine)
        assert ctrl.canApproveBaseline is True
        assert ctrl.canImport is True
