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


def _item(**overrides):
    base = dict(
        task_id="task-1",
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


class TestDiagnosticsConstraintsRow:
    """R4.4 Planning IA dedup (migration step 6): the diagnostics collection
    no longer carries a per-row infeasible/critical/delayed/overloads count --
    those are the Overview KPI strip's job (see TestOverviewInfeasibleMetric
    below). It keeps only the "constraints" (deadline-breach) row, which the
    KPI strip does not report.
    """

    def test_constraints_row_counts_deadline_breaches(self):
        items = [_item(deadline="2026-01-01", late_by_days=2)]
        collection = build_diagnostics_collection(
            schedule_items=items, filtered_schedule=items, dependency_rows=[], resource_load=[]
        )
        row = next(r for r in collection.items if r.id == "constraints")

        assert row.subtitle == "1"
        assert row.status_label == "Danger"

    def test_no_deadline_breaches_reports_stable(self):
        items = [_item(deadline=None, late_by_days=None)]
        collection = build_diagnostics_collection(
            schedule_items=items, filtered_schedule=items, dependency_rows=[], resource_load=[]
        )
        row = next(r for r in collection.items if r.id == "constraints")

        assert row.subtitle == "0"
        assert row.status_label == "Stable"


class TestOverviewInfeasibleMetric:
    def test_infeasible_metric_counts_the_flag(self):
        items = [
            _item(is_infeasible=True),
            _item(task_id="task-2", is_infeasible=False),
        ]
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
