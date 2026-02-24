from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core.exceptions import NotFoundError, ValidationError


def test_compare_baselines_returns_added_removed_changed_and_cost_delta(services):
    ps = services["project_service"]
    ts = services["task_service"]
    bs = services["baseline_service"]
    cost_s = services["cost_service"]
    rp = services["reporting_service"]

    project = ps.create_project("Baseline Compare", "")
    pid = project.id

    task_a = ts.create_task(pid, "Task A", start_date=date(2024, 1, 1), duration_days=2)
    task_b = ts.create_task(pid, "Task B", start_date=date(2024, 1, 3), duration_days=2)
    cost_s.add_cost_item(project_id=pid, description="A planned", planned_amount=100.0, task_id=task_a.id)
    baseline_1 = bs.create_baseline(pid, "BL1")

    ts.update_task(task_a.id, start_date=date(2024, 1, 2), duration_days=3)
    ts.delete_task(task_b.id)
    task_c = ts.create_task(pid, "Task C", start_date=date(2024, 1, 8), duration_days=1)
    cost_s.add_cost_item(project_id=pid, description="A extra", planned_amount=50.0, task_id=task_a.id)
    baseline_2 = bs.create_baseline(pid, "BL2")

    comparison = rp.compare_baselines(
        project_id=pid,
        baseline_a_id=baseline_1.id,
        baseline_b_id=baseline_2.id,
        include_unchanged=True,
    )

    assert comparison.total_tasks_compared == 3
    assert comparison.changed_tasks == 1
    assert comparison.added_tasks == 1
    assert comparison.removed_tasks == 1
    assert comparison.unchanged_tasks == 0

    rows_by_id = {row.task_id: row for row in comparison.rows}
    assert rows_by_id[task_a.id].change_type == "CHANGED"
    assert rows_by_id[task_a.id].start_shift_days == 1
    assert rows_by_id[task_a.id].planned_cost_delta == pytest.approx(50.0)

    assert rows_by_id[task_b.id].change_type == "REMOVED"
    assert rows_by_id[task_b.id].task_name == "Task B"
    assert rows_by_id[task_b.id].baseline_b_start is None

    assert rows_by_id[task_c.id].change_type == "ADDED"
    assert rows_by_id[task_c.id].baseline_a_start is None


def test_compare_baselines_filters_out_unchanged_rows_when_requested(services):
    ps = services["project_service"]
    ts = services["task_service"]
    bs = services["baseline_service"]
    rp = services["reporting_service"]

    project = ps.create_project("Baseline Compare Filter", "")
    pid = project.id
    ts.create_task(pid, "Task Stable", start_date=date(2024, 2, 5), duration_days=2)

    baseline_1 = bs.create_baseline(pid, "Stable-1")
    baseline_2 = bs.create_baseline(pid, "Stable-2")

    comparison = rp.compare_baselines(
        project_id=pid,
        baseline_a_id=baseline_1.id,
        baseline_b_id=baseline_2.id,
        include_unchanged=False,
    )

    assert comparison.total_tasks_compared == 1
    assert comparison.unchanged_tasks == 1
    assert comparison.rows == []


def test_compare_baselines_validates_input_and_missing_ids(services):
    ps = services["project_service"]
    ts = services["task_service"]
    bs = services["baseline_service"]
    rp = services["reporting_service"]

    project = ps.create_project("Baseline Compare Validation", "")
    pid = project.id
    ts.create_task(pid, "Task 1", start_date=date(2024, 3, 4), duration_days=1)
    baseline = bs.create_baseline(pid, "Only")

    with pytest.raises(ValidationError) as same_exc:
        rp.compare_baselines(pid, baseline.id, baseline.id)
    assert same_exc.value.code == "BASELINE_COMPARE_SAME_BASELINE"

    with pytest.raises(NotFoundError) as missing_exc:
        rp.compare_baselines(pid, baseline.id, "missing-id")
    assert missing_exc.value.code == "BASELINE_B_NOT_FOUND"


def test_report_tab_wires_baseline_comparison_action():
    tab_text = (Path(__file__).resolve().parents[1] / "ui" / "report" / "tab.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    actions_text = (Path(__file__).resolve().parents[1] / "ui" / "report" / "actions.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )

    assert "self.btn_show_baseline_compare = QPushButton" in tab_text
    assert "self.btn_show_baseline_compare.clicked.connect(self.show_baseline_comparison)" in tab_text
    assert "def show_baseline_comparison" in actions_text
    assert "BaselineCompareDialog" in actions_text
