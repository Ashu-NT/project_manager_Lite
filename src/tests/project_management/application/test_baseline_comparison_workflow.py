from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineStatus,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError


def test_compare_baselines_returns_added_removed_changed_and_cost_delta(services):
    services['baseline_query']
    project = services['project_create'].create_project("Baseline Compare", "")
    pid = project.id

    task_a = services['task_lifecycle_commands'].create_task(pid, "Task A", start_date=date(2024, 1, 1), duration_days=2)
    task_b = services['task_lifecycle_commands'].create_task(pid, "Task B", start_date=date(2024, 1, 3), duration_days=2)
    baseline_1 = services['baseline_commands'].create_baseline(pid, "BL1", rate_as_of=date.today())

    services['task_lifecycle_commands'].update_task(task_a.id, start_date=date(2024, 1, 2), duration_days=3)
    services['task_deletion_commands'].delete_task(task_b.id)
    task_c = services['task_lifecycle_commands'].create_task(pid, "Task C", start_date=date(2024, 1, 8), duration_days=1)
    baseline_2 = services['baseline_commands'].create_baseline(pid, "BL2", rate_as_of=date.today())

    comparison = services["baseline_compare_report"].compare_baselines(
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
    assert rows_by_id[task_a.id].planned_cost_delta == pytest.approx(0.0)

    assert rows_by_id[task_b.id].change_type == "REMOVED"
    assert rows_by_id[task_b.id].task_name == "Task B"
    assert rows_by_id[task_b.id].baseline_b_start is None

    assert rows_by_id[task_c.id].change_type == "ADDED"
    assert rows_by_id[task_c.id].baseline_a_start is None


def test_compare_baselines_filters_out_unchanged_rows_when_requested(services):
    services['baseline_query']
    project = services['project_create'].create_project("Baseline Compare Filter", "")
    pid = project.id
    services['task_lifecycle_commands'].create_task(pid, "Task Stable", start_date=date(2024, 2, 5), duration_days=2)

    baseline_1 = services['baseline_commands'].create_baseline(pid, "Stable-1", rate_as_of=date.today())
    baseline_2 = services['baseline_commands'].create_baseline(pid, "Stable-2", rate_as_of=date.today())

    comparison = services["baseline_compare_report"].compare_baselines(
        project_id=pid,
        baseline_a_id=baseline_1.id,
        baseline_b_id=baseline_2.id,
        include_unchanged=False,
    )

    assert comparison.total_tasks_compared == 1
    assert comparison.unchanged_tasks == 1
    assert comparison.rows == []


def test_compare_baselines_validates_input_and_missing_ids(services):
    services['baseline_query']
    project = services['project_create'].create_project("Baseline Compare Validation", "")
    pid = project.id
    services['task_lifecycle_commands'].create_task(pid, "Task 1", start_date=date(2024, 3, 4), duration_days=1)
    baseline = services['baseline_commands'].create_baseline(pid, "Only", rate_as_of=date.today())

    with pytest.raises(ValidationError) as same_exc:
        services["baseline_compare_report"].compare_baselines(pid, baseline.id, baseline.id)
    assert same_exc.value.code == "BASELINE_COMPARE_SAME_BASELINE"

    with pytest.raises(NotFoundError) as missing_exc:
        services["baseline_compare_report"].compare_baselines(pid, baseline.id, "missing-id")
    assert missing_exc.value.code == "BASELINE_B_NOT_FOUND"


def test_baseline_approval_tracks_current_approved_and_variance_records(services):
    services['baseline_query']

    project = services['project_create'].create_project("Baseline Governance", "")
    pid = project.id
    task = services['task_lifecycle_commands'].create_task(pid, "Critical Task", start_date=date(2024, 4, 1), duration_days=2)

    baseline_1 = services['baseline_commands'].create_baseline(pid, "BL1", rate_as_of=date.today())
    services['baseline_commands'].submit_baseline(baseline_1.id, submitted_by="alex")
    approved_1 = services['baseline_commands'].approve_baseline(baseline_1.id, approved_by="alex")

    assert approved_1.status == BaselineStatus.APPROVED
    assert services['baseline_query'].get_approved_baseline(pid).id == baseline_1.id
    assert services['baseline_query'].list_variance_records(baseline_1.id) == []

    services['task_lifecycle_commands'].update_task(task.id, start_date=date(2024, 4, 3), duration_days=4)

    baseline_2 = services['baseline_commands'].create_baseline(pid, "BL2", rate_as_of=date.today())
    services['baseline_commands'].submit_baseline(baseline_2.id, submitted_by="alex")
    approved_2 = services['baseline_commands'].approve_baseline(baseline_2.id, approved_by="alex")

    baselines = {row.id: row for row in services['baseline_query'].list_baselines(pid)}
    variance_rows = services['baseline_query'].list_variance_records(baseline_2.id)

    assert approved_2.status == BaselineStatus.APPROVED
    assert services['baseline_query'].get_approved_baseline(pid).id == baseline_2.id
    assert baselines[baseline_1.id].status == BaselineStatus.SUPERSEDED
    assert len(variance_rows) == 1
    assert variance_rows[0].task_id == task.id
    assert variance_rows[0].start_variance_days == 2
    assert variance_rows[0].finish_variance_days > 0
    assert variance_rows[0].cost_variance == pytest.approx(0.0)

