"""Governance parity for ApplyResourceLevelingPlanCommand, mirroring
TaskSchedulingConstraintHandler's governed/ungoverned shape
(test_task_constraint_governance.py): approval-gated apply, admin
bypass, and TOCTOU-safe revalidation at apply time using the schedule
fingerprint instead of a single task's version.
"""
from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.application.resources.dto.commands.catalog import (
    ResourceCreateCommand,
)
from src.core.modules.project_management.application.scheduling.leveling.resource_leveling_planner import (
    ResourceLevelingPlanner,
)
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks
from src.core.platform.application.approval.dto.commands.decisions import (
    ApprovalDecisionCommand,
)
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError


def _login(services, username: str, password: str):
    user_session = services["user_session"]
    user = services["authentication"].authenticate(username, password)
    user_session.set_principal(services["principal_builder"].build(user))


def _login_eligible_reviewer(services):
    _login(services, "admin", "ChangeMe123!")
    services["user_registration"].register_user(
        "leveling-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "leveling-reviewer", "StrongPass123")


def _snapshot(task_lookup, dependency_query, project_id):
    tasks = select_leaf_tasks(task_lookup.list_tasks_for_project(project_id))
    tasks_by_id = {t.id: t for t in tasks}
    assignments = task_lookup.list_assignments_for_tasks([t.id for t in tasks])
    deps = dependency_query.list_dependencies_for_project(project_id)
    return tasks_by_id, assignments, deps


def _build_overload_proposal(services, name: str):
    ts = services['task_lookup_query']
    calendar = services["work_calendar_engine"]

    project = services['project_create'].create_project(ProjectCreateCommand(name=name, description=""))
    task_b = services['task_lifecycle_commands'].create_task(project.id, "Task B", start_date=date(2026, 9, 7), duration_days=3)
    task_c = services['task_lifecycle_commands'].create_task(project.id, "Task C", start_date=date(2026, 9, 7), duration_days=3)
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="Governance Dev", role="Developer", hourly_rate=100.0))
    services['task_assignment_commands'].assign_resource(task_b.id, resource.id, allocation_percent=70.0)
    services['task_assignment_commands'].assign_resource(task_c.id, resource.id, allocation_percent=60.0)

    tasks_by_id, assignments, deps = _snapshot(ts, services['task_dependency_query'], project.id)
    planner = ResourceLevelingPlanner(calendar)
    proposal = planner.build_proposal(
        project_id=project.id,
        tasks_by_id=tasks_by_id,
        deps=deps,
        assignments=assignments,
        resource_name_by_id={resource.id: resource.name},
    )
    return project, task_b, task_c, proposal


class TestGovernanceParity:
    def test_apply_requires_approval_when_governed(self, services, monkeypatch):
        monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
        monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "scheduling.leveling.apply")
        _login(services, "admin", "ChangeMe123!")

        approvals = services["approval_commands"]
        project, task_b, task_c, proposal = _build_overload_proposal(services, "Leveling Governance Apply")
        assert len(proposal.moves) >= 1
        moved_task_id = proposal.moves[0].task_id
        expected_start = proposal.moves[0].new_start

        services["user_registration"].register_user("planner-leveling-governed", "StrongPass123", role_names=["planner"])
        _login(services, "planner-leveling-governed", "StrongPass123")

        with pytest.raises(BusinessRuleError, match="Approval required"):
            services['task_leveling_commands'].apply_resource_leveling_plan(project.id, proposal)

        # Not applied yet.
        assert services['task_detail_query'].get_task(moved_task_id).resource_leveling_not_before is None

        req = services["approval_queries"].list_pending(project_id=project.id)[0]
        assert req.request_type == "scheduling.leveling.apply"
        assert req.payload["schedule_fingerprint"] == proposal.schedule_fingerprint
        assert {m["task_id"] for m in req.payload["moves"]} == {m.task_id for m in proposal.moves}

        _login_eligible_reviewer(services)
        approvals.approve_and_apply(ApprovalDecisionCommand(request_id=req.id))

        assert services['task_detail_query'].get_task(moved_task_id).resource_leveling_not_before == expected_start
        assert services['task_detail_query'].get_task(moved_task_id).start_date == expected_start

    def test_admin_session_bypasses_governance(self, services, monkeypatch):
        monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
        monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "scheduling.leveling.apply")
        _login(services, "admin", "ChangeMe123!")
        project, task_b, task_c, proposal = _build_overload_proposal(services, "Leveling Governance Admin Bypass")
        assert len(proposal.moves) >= 1
        moved_task_id = proposal.moves[0].task_id

        updated = services['task_leveling_commands'].apply_resource_leveling_plan(project.id, proposal)

        assert any(t.id == moved_task_id for t in updated)
        assert services['task_detail_query'].get_task(moved_task_id).resource_leveling_not_before is not None

    def test_approval_apply_revalidates_fingerprint_at_apply_time(self, services, monkeypatch):
        """TOCTOU fix mirrored from constraint governance: if the
        schedule drifted while the request was pending, applying the
        stale request must fail rather than silently overwrite whatever
        happened in between."""
        monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
        monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "scheduling.leveling.apply")
        _login(services, "admin", "ChangeMe123!")

        approvals = services["approval_commands"]
        project, task_b, task_c, proposal = _build_overload_proposal(services, "Leveling Governance TOCTOU")
        assert len(proposal.moves) >= 1
        moved_task_id = proposal.moves[0].task_id

        services["user_registration"].register_user("planner-leveling-toctou", "StrongPass123", role_names=["planner"])
        _login(services, "planner-leveling-toctou", "StrongPass123")

        with pytest.raises(BusinessRuleError, match="Approval required"):
            services['task_leveling_commands'].apply_resource_leveling_plan(project.id, proposal)
        req = services["approval_queries"].list_pending(project_id=project.id)[0]

        # The schedule drifts while the request is pending: an admin
        # edits an involved task directly, bumping its version and
        # invalidating the fingerprint embedded in the pending request.
        _login(services, "admin", "ChangeMe123!")
        services['task_lifecycle_commands'].update_task(task_c.id, name="Renamed While Pending")

        _login_eligible_reviewer(services)
        with pytest.raises(ConcurrencyError):
            approvals.approve_and_apply(ApprovalDecisionCommand(request_id=req.id))

        # The admin's direct edit must survive -- the stale pending
        # request must not silently overwrite it.
        assert services['task_detail_query'].get_task(task_c.id).name == "Renamed While Pending"
        assert services['task_detail_query'].get_task(moved_task_id).resource_leveling_not_before is None
