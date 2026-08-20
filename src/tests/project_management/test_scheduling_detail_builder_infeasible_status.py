"""R4.4 Planning IA implementation, step 1 -- detail_builder.py's Overview
status label must use the same Infeasible > Critical > (raw status)
precedence every other criticality-reporting surface in the Scheduling
workspace already uses. Previously it checked only is_critical, silently
dropping infeasibility for the per-activity Detail Overview header.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.scheduling.detail_builder import (
    build_detail_view_model,
)


def _activity(**overrides):
    base = dict(
        id="t1",
        project_id="p1",
        name="Task One",
        description="",
        wbs_code="1.1",
        start_date=date(2026, 1, 5),
        finish_date=date(2026, 1, 7),
        latest_start=date(2026, 1, 5),
        latest_finish=date(2026, 1, 7),
        duration_days=2,
        remaining_duration_days=2,
        total_float_days=0,
        percent_complete=0.0,
        status_label="In Progress",
        is_critical=False,
        is_infeasible=False,
        constraint_type_label="ASAP",
        constraint_date=None,
        deadline=None,
        actual_start=None,
        actual_end=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _build(activity):
    return build_detail_view_model(
        selected_activity=activity,
        calendar_label="Standard",
        dependency_rows=[],
        resource_load=[],
        baseline_rows=[],
    )


def test_infeasible_activity_reports_infeasible_even_when_not_critical():
    activity = _activity(is_infeasible=True, is_critical=False, status_label="Not Started")
    vm = _build(activity)
    assert vm.status_label == "Infeasible"


def test_critical_activity_reports_critical():
    activity = _activity(is_infeasible=False, is_critical=True, status_label="In Progress")
    vm = _build(activity)
    assert vm.status_label == "Critical"


def test_infeasible_and_critical_reports_infeasible_first():
    activity = _activity(is_infeasible=True, is_critical=True)
    vm = _build(activity)
    assert vm.status_label == "Infeasible"


def test_neither_infeasible_nor_critical_falls_back_to_the_raw_status_label():
    activity = _activity(is_infeasible=False, is_critical=False, status_label="In Progress")
    vm = _build(activity)
    assert vm.status_label == "In Progress"
