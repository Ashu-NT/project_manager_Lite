"""Unit tests for ProjectBaseline lifecycle — pure domain, no DB."""
from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineStatus,
    BaselineTask,
    BaselineVarianceRecord,
    ProjectBaseline,
)


class TestProjectBaselineCreate:
    def test_creates_with_draft_status(self):
        b = ProjectBaseline.create("p1", "Baseline 1")
        assert b.status == BaselineStatus.DRAFT
        assert b.version == 1
        assert b.approved_by is None
        assert b.submitted_by is None

    def test_strips_whitespace_from_name(self):
        b = ProjectBaseline.create("p1", "  My Plan  ")
        assert b.name == "My Plan"

    def test_uses_default_name_when_blank(self):
        b = ProjectBaseline.create("p1", "   ")
        assert b.name == "Baseline"


class TestBaselineSubmit:
    def test_draft_to_submitted(self):
        b = ProjectBaseline.create("p1", "B1")
        b.submit("user_1", notes="Ready for review")
        assert b.status == BaselineStatus.SUBMITTED
        assert b.submitted_by == "user_1"
        assert b.notes == "Ready for review"

    def test_cannot_submit_already_submitted(self):
        b = ProjectBaseline.create("p1", "B1")
        b.submit("user_1")
        with pytest.raises(ValueError, match="Cannot submit"):
            b.submit("user_2")

    def test_cannot_submit_approved(self):
        b = ProjectBaseline.create("p1", "B1")
        b.submit("user_1")
        b.approve("approver_1")
        with pytest.raises(ValueError, match="Cannot submit"):
            b.submit("user_2")


class TestBaselineApprove:
    def test_submitted_to_approved(self):
        b = ProjectBaseline.create("p1", "B1")
        b.submit("user_1")
        b.approve("approver_1", notes="Looks good")
        assert b.status == BaselineStatus.APPROVED
        assert b.approved_by == "approver_1"
        assert b.approved_at == date.today()
        assert b.notes == "Looks good"

    def test_cannot_approve_draft(self):
        b = ProjectBaseline.create("p1", "B1")
        with pytest.raises(ValueError, match="Cannot approve"):
            b.approve("approver_1")


class TestBaselineReject:
    def test_submitted_to_rejected(self):
        b = ProjectBaseline.create("p1", "B1")
        b.submit("user_1")
        b.reject(notes="Needs revision")
        assert b.status == BaselineStatus.REJECTED

    def test_cannot_reject_draft(self):
        b = ProjectBaseline.create("p1", "B1")
        with pytest.raises(ValueError, match="Cannot reject"):
            b.reject()


class TestBaselineSupersede:
    def test_approved_to_superseded(self):
        b = ProjectBaseline.create("p1", "B1")
        b.submit("user_1")
        b.approve("approver_1")
        b.supersede()
        assert b.status == BaselineStatus.SUPERSEDED

    def test_cannot_supersede_draft(self):
        b = ProjectBaseline.create("p1", "B1")
        with pytest.raises(ValueError, match="Cannot supersede"):
            b.supersede()


class TestBaselineVarianceRecord:
    def test_create_variance_record(self):
        r = BaselineVarianceRecord.create(
            project_id="p1",
            new_baseline_id="b2",
            superseded_baseline_id="b1",
            task_id="t1",
            task_name="Design Phase",
            start_variance_days=3,
            finish_variance_days=5,
            cost_variance=1500.0,
        )
        assert r.start_variance_days == 3
        assert r.finish_variance_days == 5
        assert r.cost_variance == 1500.0
        assert r.created_at == date.today()


class TestBaselineTask:
    def test_create_clamps_negative_duration(self):
        bt = BaselineTask.create(
            baseline_id="b1",
            task_id="t1",
            task_name="Task",
            baseline_start=None,
            baseline_finish=None,
            baseline_duration_days=-5,
            baseline_planned_cost=1000.0,
        )
        assert bt.baseline_duration_days == 0

    def test_create_clamps_negative_cost(self):
        bt = BaselineTask.create(
            baseline_id="b1",
            task_id="t1",
            task_name="Task",
            baseline_start=None,
            baseline_finish=None,
            baseline_duration_days=5,
            baseline_planned_cost=-200.0,
        )
        assert bt.baseline_planned_cost == 0.0
