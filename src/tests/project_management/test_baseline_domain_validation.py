from __future__ import annotations

from datetime import date, datetime

import pytest

from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineStatus,
    BaselineTask,
    BaselineVarianceRecord,
    ProjectBaseline,
)
from src.core.platform.common.exceptions import ValidationError


def test_project_baseline_dto_normalizes_and_validates_lifecycle_metadata():
    baseline = ProjectBaseline.create("  proj-1  ", "   ")

    assert baseline.project_id == "proj-1"
    assert baseline.name == "Baseline"
    assert baseline.status == BaselineStatus.DRAFT
    assert baseline.version == 1
    assert baseline.can_submit is True
    assert baseline.can_approve is False
    assert baseline.can_reject is False

    baseline.submit("  alex  ", "  Ready for review.  ")
    assert baseline.status == BaselineStatus.SUBMITTED
    assert baseline.submitted_by == "alex"
    assert baseline.submitted_at == date.today()
    assert baseline.notes == "Ready for review."
    assert baseline.can_submit is False
    assert baseline.can_approve is True
    assert baseline.can_reject is True

    baseline.approve("  maria  ", "  Approved for execution.  ")
    assert baseline.status == BaselineStatus.APPROVED
    assert baseline.approved_by == "maria"
    assert baseline.approved_at == date.today()
    assert baseline.notes == "Approved for execution."
    assert baseline.can_submit is False
    assert baseline.can_approve is False
    assert baseline.can_reject is False

    baseline.supersede()
    assert baseline.status == BaselineStatus.SUPERSEDED
    assert baseline.can_submit is False
    assert baseline.can_approve is False
    assert baseline.can_reject is False


def test_project_baseline_rejected_state_exposes_no_lifecycle_actions():
    baseline = ProjectBaseline.create("proj-1", "Rejected")
    baseline.submit("alex")
    baseline.reject("Needs revision")

    assert baseline.status == BaselineStatus.REJECTED
    assert baseline.can_submit is False
    assert baseline.can_approve is False
    assert baseline.can_reject is False


def test_project_baseline_dto_rejects_invalid_status_and_transitions():
    with pytest.raises(ValidationError) as exc_project:
        ProjectBaseline.create(" ", "Valid")
    assert exc_project.value.code == "BASELINE_PROJECT_REQUIRED"

    with pytest.raises(ValidationError) as exc_status:
        ProjectBaseline(
            id="baseline-1",
            project_id="proj-1",
            name="Weekly Freeze",
            created_at=datetime(2026, 7, 1, 8, 0, 0),
            status="bad-status",
        )
    assert exc_status.value.code == "BASELINE_STATUS_INVALID"

    with pytest.raises(ValidationError) as exc_metadata:
        ProjectBaseline(
            id="baseline-2",
            project_id="proj-1",
            name="Submitted",
            created_at=date(2026, 7, 1),
            status=BaselineStatus.SUBMITTED,
        )
    assert exc_metadata.value.code == "BASELINE_SUBMISSION_METADATA_REQUIRED"

    baseline = ProjectBaseline.create("proj-1", "Freeze 1")
    with pytest.raises(ValidationError) as exc_transition:
        baseline.approve("alex")
    assert exc_transition.value.code == "BASELINE_APPROVE_STATUS_INVALID"


def test_baseline_task_and_variance_dtos_normalize_and_validate_local_fields():
    baseline_task = BaselineTask.create(
        baseline_id="  baseline-1  ",
        task_id="  task-1  ",
        task_name="  Task A  ",
        baseline_start=datetime(2026, 7, 1, 9, 0, 0),
        baseline_finish=date(2026, 7, 3),
        baseline_duration_days="2",
        baseline_planned_cost="150.5",
    )

    assert baseline_task.baseline_id == "baseline-1"
    assert baseline_task.task_id == "task-1"
    assert baseline_task.task_name == "Task A"
    assert baseline_task.baseline_start == date(2026, 7, 1)
    assert baseline_task.baseline_finish == date(2026, 7, 3)
    assert baseline_task.baseline_duration_days == 2
    assert baseline_task.baseline_planned_cost == pytest.approx(150.5)

    variance = BaselineVarianceRecord.create(
        project_id="  proj-1  ",
        new_baseline_id="  baseline-2  ",
        superseded_baseline_id="  baseline-1  ",
        task_id="  task-1  ",
        task_name="  Task A  ",
        start_variance_days="2",
        finish_variance_days="-1",
        cost_variance="15.25",
    )

    assert variance.project_id == "proj-1"
    assert variance.new_baseline_id == "baseline-2"
    assert variance.superseded_baseline_id == "baseline-1"
    assert variance.task_id == "task-1"
    assert variance.task_name == "Task A"
    assert variance.start_variance_days == 2
    assert variance.finish_variance_days == -1
    assert variance.cost_variance == pytest.approx(15.25)

    with pytest.raises(ValidationError) as exc_duration:
        BaselineTask.create(
            baseline_id="baseline-1",
            task_id="task-1",
            task_name="Task A",
            baseline_start=date(2026, 7, 1),
            baseline_finish=date(2026, 7, 2),
            baseline_duration_days=-1,
            baseline_planned_cost=10.0,
        )
    assert exc_duration.value.code == "BASELINE_TASK_DURATION_INVALID"

    with pytest.raises(ValidationError) as exc_range:
        BaselineTask.create(
            baseline_id="baseline-1",
            task_id="task-1",
            task_name="Task A",
            baseline_start=date(2026, 7, 3),
            baseline_finish=date(2026, 7, 1),
            baseline_duration_days=2,
            baseline_planned_cost=10.0,
        )
    assert exc_range.value.code == "BASELINE_TASK_DATE_RANGE_INVALID"


def test_baseline_service_uses_domain_normalization_for_create_and_reject_flow(services):
    project_service = services["project_service"]
    task_service = services["task_service"]
    baseline_service = services["baseline_service"]

    project = project_service.create_project("Baseline DTO Service Proof")
    task_service.create_task(project.id, "First Task", start_date=date(2026, 7, 1), duration_days=2)

    created = baseline_service.create_baseline(
        project.id, "  Weekly Freeze  ", rate_as_of=date.today()
    )
    assert created.name == "Weekly Freeze"

    submitted = baseline_service.submit_baseline(
        created.id,
        submitted_by="  alex  ",
        notes="  Ready for approval.  ",
    )
    assert submitted.submitted_by == "alex"
    assert submitted.notes == "Ready for approval."

    rejected = baseline_service.reject_baseline(created.id, notes="  Need one more review.  ")
    assert rejected.status == BaselineStatus.REJECTED
    assert rejected.notes == "Need one more review."
