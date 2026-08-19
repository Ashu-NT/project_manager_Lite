"""Phase N/N9: the Task Detail Dependencies dialog surfaces the typed,
non-persisting impact-preview backend (Phase K) instead of computing any
schedule math itself. These tests pin the presenter-layer command-handler
functions that translate a QML payload into a desktop-API preview call and
back into a camelCase dict -- the same contract already established by
``assignment_command_handler.preview_assignment``.
"""
from __future__ import annotations

from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.tasks.dependency_command_handler import (
    preview_create_dependency,
    preview_delete_dependency,
    preview_update_dependency,
)


def _fake_impact_dto(**overrides):
    defaults = dict(
        is_valid=True,
        code="DEPENDENCY_VALID",
        summary="Applying this dependency shifts 2 downstream tasks.",
        detail="",
        risk_level="medium",
        affected_task_count=2,
        largest_shift_days=3,
        rows=(
            SimpleNamespace(
                task_id="task-2",
                task_name="Task Two",
                before_start_label="2026-09-09",
                before_finish_label="2026-09-11",
                after_start_label="2026-09-11",
                after_finish_label="2026-09-13",
                start_shift_days=2,
                finish_shift_days=2,
            ),
        ),
        suggestions=("You can apply this dependency with low scheduling risk.",),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_preview_create_dependency_maps_payload_and_serializes_rows():
    captured = []

    def _fake_preview_create_dependency(command):
        captured.append(command)
        return _fake_impact_dto()

    desktop_api = SimpleNamespace(preview_create_dependency=_fake_preview_create_dependency)

    result = preview_create_dependency(
        desktop_api,
        {
            "taskId": "task-1",
            "linkedTaskId": "task-2",
            "relationshipDirection": "PREDECESSOR",
            "dependencyType": "FS",
            "lagDays": "2",
        },
    )

    assert len(captured) == 1
    command = captured[0]
    assert command.task_id == "task-1"
    assert command.linked_task_id == "task-2"
    assert command.relationship_direction == "PREDECESSOR"
    assert command.dependency_type == "FS"
    assert command.lag_days == 2

    assert result["available"] is True
    assert result["isValid"] is True
    assert result["code"] == "DEPENDENCY_VALID"
    assert result["riskLevel"] == "medium"
    assert result["affectedTaskCount"] == 2
    assert result["largestShiftDays"] == 3
    assert result["rows"] == [
        {
            "taskId": "task-2",
            "taskName": "Task Two",
            "beforeStartLabel": "2026-09-09",
            "beforeFinishLabel": "2026-09-11",
            "afterStartLabel": "2026-09-11",
            "afterFinishLabel": "2026-09-13",
            "startShiftDays": 2,
            "finishShiftDays": 2,
        }
    ]
    assert result["suggestions"] == ["You can apply this dependency with low scheduling risk."]


def test_preview_create_dependency_returns_unavailable_without_crashing_when_inputs_incomplete():
    """Mirrors preview_assignment's incomplete-input contract: QML may call
    this before the user has finished filling the dialog. Must never raise."""
    desktop_api = SimpleNamespace(preview_create_dependency=lambda command: None)

    result = preview_create_dependency(desktop_api, {"taskId": "task-1"})

    assert result["available"] is False
    assert result["isValid"] is True
    assert result["rows"] == []


def test_preview_create_dependency_reports_unavailable_when_backend_dto_is_none():
    """desktop_api.preview_create_dependency degrades to None when the
    task service doesn't support diagnostics (graceful-degradation seam) --
    the dialog must show no impact panel, not fabricate one."""
    desktop_api = SimpleNamespace(preview_create_dependency=lambda command: None)

    result = preview_create_dependency(
        desktop_api,
        {
            "taskId": "task-1",
            "linkedTaskId": "task-2",
            "relationshipDirection": "PREDECESSOR",
        },
    )

    assert result["available"] is False


def test_preview_update_dependency_maps_payload():
    captured = []

    def _fake_preview_update_dependency(command):
        captured.append(command)
        return _fake_impact_dto(code="DEPENDENCY_VALID", risk_level="none", rows=(), affected_task_count=0, largest_shift_days=0, suggestions=())

    desktop_api = SimpleNamespace(preview_update_dependency=_fake_preview_update_dependency)

    result = preview_update_dependency(
        desktop_api,
        {"dependencyId": "dep-1", "dependencyType": "ss", "lagDays": "1"},
    )

    assert len(captured) == 1
    command = captured[0]
    assert command.dependency_id == "dep-1"
    assert command.dependency_type == "SS"
    assert command.lag_days == 1
    assert result["available"] is True
    assert result["riskLevel"] == "none"
    assert result["rows"] == []


def test_preview_update_dependency_returns_unavailable_without_dependency_id():
    desktop_api = SimpleNamespace(preview_update_dependency=lambda command: _fake_impact_dto())

    result = preview_update_dependency(desktop_api, {"dependencyType": "FS", "lagDays": "0"})

    assert result["available"] is False


def test_preview_delete_dependency_maps_id_and_reports_downstream_shift():
    captured = []

    def _fake_preview_delete_dependency(dependency_id):
        captured.append(dependency_id)
        return _fake_impact_dto(
            code="DEPENDENCY_VALID",
            risk_level="high",
            affected_task_count=7,
            largest_shift_days=3,
        )

    desktop_api = SimpleNamespace(preview_delete_dependency=_fake_preview_delete_dependency)

    result = preview_delete_dependency(desktop_api, "  dep-1  ")

    assert captured == ["dep-1"]
    assert result["available"] is True
    assert result["affectedTaskCount"] == 7
    assert result["largestShiftDays"] == 3
    assert result["riskLevel"] == "high"


def test_preview_delete_dependency_returns_unavailable_for_blank_id():
    desktop_api = SimpleNamespace(preview_delete_dependency=lambda dependency_id: _fake_impact_dto())

    result = preview_delete_dependency(desktop_api, "   ")

    assert result["available"] is False
