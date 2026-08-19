"""PRE-R4.4 -- WIRE CPM INFEASIBILITY STATE TO DESKTOP/QML: the
Scheduling workspace's project-wide diagnostics/overview/table surfaces
must read the backend-owned SchedulingTaskDto.is_infeasible flag
directly, never re-derive it from ``total_float_days < 0`` (the exact
heuristic these two presenter functions used before this pass).
"""
from __future__ import annotations

from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.scheduling.diagnostics_builder import (
    build_diagnostics_collection,
)
from src.ui_qml.modules.project_management.presenters.scheduling.overview_builder import (
    build_overview,
)
from src.ui_qml.modules.project_management.presenters.scheduling.formatters import (
    activity_criticality_label,
)
from src.ui_qml.modules.project_management.presenters.scheduling.record_mappers import (
    to_schedule_record,
)


def _item(**overrides):
    base = dict(
        id="task-1",
        total_float_days=0,
        is_critical=False,
        is_infeasible=False,
        late_by_days=None,
        deadline=None,
        percent_complete=0.0,
        remaining_duration_days=0,
        duration_days=1,
        wbs_code="A",
        name="Task",
        start_date=None,
        finish_date=None,
        status_label="Planned",
        latest_start=None,
        latest_finish=None,
        actual_start=None,
        actual_end=None,
        description="",
        constraint_type="",
        constraint_type_label="As Soon As Possible (ASAP)",
        constraint_date=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestDiagnosticsInfeasibleRow:
    def test_infeasible_flag_drives_the_row_not_negative_float_alone(self):
        """A backend-flagged infeasible item counts even though this
        fake's total_float_days happens to be 0 -- proving the row is
        NOT re-deriving from total_float_days < 0."""
        items = [_item(total_float_days=0, is_infeasible=True)]
        collection = build_diagnostics_collection(
            schedule_items=items, filtered_schedule=items, dependency_rows=[], resource_load=[]
        )
        row = next(r for r in collection.items if r.id == "infeasible")

        assert row.subtitle == "1"
        assert row.status_label == "Danger"

    def test_negative_float_without_the_flag_does_not_count(self):
        """The inverse: a negative total_float_days with is_infeasible
        NOT set must not count either -- confirms the row reads the
        flag, not the number."""
        items = [_item(total_float_days=-3, is_infeasible=False)]
        collection = build_diagnostics_collection(
            schedule_items=items, filtered_schedule=items, dependency_rows=[], resource_load=[]
        )
        row = next(r for r in collection.items if r.id == "infeasible")

        assert row.subtitle == "0"
        assert row.status_label == "Stable"

    def test_no_infeasible_activities_reports_stable(self):
        items = [_item(is_infeasible=False)]
        collection = build_diagnostics_collection(
            schedule_items=items, filtered_schedule=items, dependency_rows=[], resource_load=[]
        )
        row = next(r for r in collection.items if r.id == "infeasible")

        assert row.subtitle == "0"
        assert row.status_label == "Stable"


class TestOverviewInfeasibleMetric:
    def test_infeasible_metric_counts_the_flag(self):
        items = [_item(is_infeasible=True), _item(id="task-2", is_infeasible=False)]
        overview = build_overview(
            resolved_project_id="project-1",
            schedule_items=items,
            filtered_schedule=items,
            critical_items=[],
            delayed_items=[],
            dependency_rows=[],
            baseline_rows=[],
            calendar_snapshot=SimpleNamespace(hours_per_day=8.0, holidays=[]),
            resource_load=[],
        )
        metric = next(m for m in overview.metrics if m.label == "Infeasible")

        assert metric.value == "1"


class TestActivityCriticalityLabel:
    def test_infeasible_takes_precedence_over_critical(self):
        item = _item(is_infeasible=True, is_critical=True)
        assert activity_criticality_label(item) == "Infeasible"

    def test_critical_without_infeasible_reports_critical(self):
        item = _item(is_infeasible=False, is_critical=True)
        assert activity_criticality_label(item) == "Critical"

    def test_neither_reports_normal(self):
        item = _item(is_infeasible=False, is_critical=False)
        assert activity_criticality_label(item) == "Normal"


class TestScheduleRecordCriticalLabel:
    def test_infeasible_item_reports_infeasible_critical_label(self):
        item = _item(is_infeasible=True, is_critical=True)
        record = to_schedule_record(item, row_index=0, calendar_label="Default")

        assert record.state["criticalLabel"] == "Infeasible"
