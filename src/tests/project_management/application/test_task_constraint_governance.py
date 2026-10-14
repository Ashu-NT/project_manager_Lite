"""Task scheduling-constraint mutation: governance parity with dependency mutations, optimistic
concurrency, apply-time TOCTOU revalidation, and the non-working-date calendar policy."""
from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.domain.enums import ConstraintType
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    ValidationError,
)


def _login(services, username: str, password: str):
    user_session = services["user_session"]
    user = services["authentication"].authenticate(username, password)
    user_session.set_principal(services["principal_builder"].build(user))


def _login_eligible_reviewer(services):
    _login(services, "admin", "ChangeMe123!")
    services["user_registration"].register_user(
        "constraint-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "constraint-reviewer", "StrongPass123")


def _make_task(services, *, start_date=date(2026, 9, 1), duration_days=3):
    project = services['project_create'].create_project("Constraint Governance", "")
    task = services['task_lifecycle_commands'].create_task(project.id, "Constrained Task", "", start_date=start_date, duration_days=duration_days)
    return project, task


class TestImmediateApply:
    def test_ungoverned_update_applies_immediately_and_recalculates_schedule(self, services):
        project, task = _make_task(services)

        updated = services['task_constraint_commands'].update_task_scheduling_constraint(
            task.id,
            constraint_type=ConstraintType.MUST_START_ON,
            constraint_date=date(2026, 9, 18),
            expected_version=task.version,
        )

        assert updated.constraint_type is ConstraintType.MUST_START_ON
        assert updated.constraint_date == date(2026, 9, 18)
        assert updated.start_date == date(2026, 9, 18)

    def test_schedule_failure_rolls_back_constraint_write(self, services, monkeypatch):
        _, task = _make_task(services)

        def fail_schedule(*args, **kwargs):
            raise RuntimeError("schedule recalculation failed")

        monkeypatch.setattr(
            services['task_constraint_commands']._schedule_synchronizer,
            "sync_project_schedule",
            fail_schedule,
        )
        with pytest.raises(RuntimeError, match="schedule recalculation failed"):
            services['task_constraint_commands'].update_task_scheduling_constraint(
                task.id,
                constraint_type=ConstraintType.MUST_START_ON,
                constraint_date=date(2026, 9, 18),
                expected_version=task.version,
            )

        unchanged = services['task_detail_query'].get_task(task.id)
        assert unchanged.constraint_type is None
        assert unchanged.constraint_date is None

    def test_clearing_a_constraint_back_to_asap_applies_immediately(self, services):
        project, task = _make_task(services)
        services['task_constraint_commands'].update_task_scheduling_constraint(
            task.id,
            constraint_type=ConstraintType.MUST_START_ON,
            constraint_date=date(2026, 9, 18),
            expected_version=task.version,
        )
        constrained = services['task_detail_query'].get_task(task.id)

        cleared = services['task_constraint_commands'].update_task_scheduling_constraint(
            task.id,
            constraint_type=None,
            constraint_date=None,
            expected_version=constrained.version,
        )

        assert cleared.constraint_type is None
        assert cleared.constraint_date is None


class TestNonWorkingDatePolicy:
    def test_non_working_constraint_date_is_rejected_not_silently_snapped(self, services):
        project, task = _make_task(services)

        with pytest.raises(ValidationError) as exc_info:
            services['task_constraint_commands'].update_task_scheduling_constraint(
                task.id,
                constraint_type=ConstraintType.MUST_START_ON,
                # A Saturday.
                constraint_date=date(2026, 9, 19),
                expected_version=task.version,
            )
        assert exc_info.value.code == "CONSTRAINT_DATE_NON_WORKING"
        # Nothing was mutated.
        assert services['task_detail_query'].get_task(task.id).constraint_type is None

    def test_working_day_constraint_date_is_accepted(self, services):
        project, task = _make_task(services)

        updated = services['task_constraint_commands'].update_task_scheduling_constraint(
            task.id,
            constraint_type=ConstraintType.MUST_START_ON,
            # A Friday.
            constraint_date=date(2026, 9, 18),
            expected_version=task.version,
        )
        assert updated.constraint_type is ConstraintType.MUST_START_ON


class TestOptimisticConcurrency:
    def test_stale_expected_version_is_rejected(self, services):
        project, task = _make_task(services)
        services['task_constraint_commands'].update_task_scheduling_constraint(
            task.id,
            constraint_type=ConstraintType.START_NO_EARLIER_THAN,
            constraint_date=date(2026, 9, 18),
            expected_version=task.version,
        )

        with pytest.raises(ConcurrencyError):
            services['task_constraint_commands'].update_task_scheduling_constraint(
                task.id,
                constraint_type=ConstraintType.MUST_START_ON,
                constraint_date=date(2026, 9, 4),
                expected_version=task.version,  # stale -- version already advanced
            )


class TestGovernanceParity:
    def test_update_requires_approval_when_governed(self, services, monkeypatch):
        monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
        monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "task.constraint.update")
        _login(services, "admin", "ChangeMe123!")

        approvals = services["approval_commands"]
        project, task = _make_task(services)

        services["user_registration"].register_user("planner-constraint-governed", "StrongPass123", role_names=["planner"])
        _login(services, "planner-constraint-governed", "StrongPass123")

        with pytest.raises(BusinessRuleError, match="Approval required"):
            services['task_constraint_commands'].update_task_scheduling_constraint(
                task.id,
                constraint_type=ConstraintType.MUST_START_ON,
                constraint_date=date(2026, 9, 18),
                expected_version=task.version,
            )

        # Not applied yet.
        assert services['task_detail_query'].get_task(task.id).constraint_type is None

        req = services["approval_queries"].list_pending(project_id=project.id)[0]
        assert req.request_type == "task.constraint.update"
        assert req.payload["constraint_type"] == "must_start_on"
        assert req.payload["constraint_date"] == "2026-09-18"
        assert req.payload["expected_version"] == task.version

        _login_eligible_reviewer(services)
        approvals.approve_and_apply(req.id)

        assert services['task_detail_query'].get_task(task.id).constraint_type is ConstraintType.MUST_START_ON

    def test_admin_session_bypasses_governance(self, services, monkeypatch):
        monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
        monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "task.constraint.update")
        _login(services, "admin", "ChangeMe123!")
        project, task = _make_task(services)

        updated = services['task_constraint_commands'].update_task_scheduling_constraint(
            task.id,
            constraint_type=ConstraintType.MUST_START_ON,
            constraint_date=date(2026, 9, 18),
            expected_version=task.version,
        )
        assert updated.constraint_type is ConstraintType.MUST_START_ON

    def test_approval_apply_revalidates_version_at_apply_time(self, services, monkeypatch):
        """TOCTOU fix mirrored from dependency governance: if the task
        changed after the request was filed, applying the stale request
        must fail rather than silently overwrite whatever happened in
        between."""
        monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
        monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "task.constraint.update")
        _login(services, "admin", "ChangeMe123!")

        approvals = services["approval_commands"]
        project, task = _make_task(services)

        services["user_registration"].register_user("planner-constraint-toctou", "StrongPass123", role_names=["planner"])
        _login(services, "planner-constraint-toctou", "StrongPass123")

        with pytest.raises(BusinessRuleError, match="Approval required"):
            services['task_constraint_commands'].update_task_scheduling_constraint(
                task.id,
                constraint_type=ConstraintType.MUST_START_ON,
                constraint_date=date(2026, 9, 18),
                expected_version=task.version,
            )
        req = services["approval_queries"].list_pending(project_id=project.id)[0]

        # The task changes while the request is pending: an admin edits
        # it directly, bumping its version.
        _login(services, "admin", "ChangeMe123!")
        services['task_lifecycle_commands'].update_task(task.id, name="Renamed While Pending", expected_version=task.version)
        assert services['task_detail_query'].get_task(task.id).version == 2

        _login_eligible_reviewer(services)
        with pytest.raises(ConcurrencyError):
            approvals.approve_and_apply(req.id)

        # The admin's direct edit must survive -- the stale pending
        # request must not silently overwrite it.
        assert services['task_detail_query'].get_task(task.id).name == "Renamed While Pending"
        assert services['task_detail_query'].get_task(task.id).constraint_type is None
