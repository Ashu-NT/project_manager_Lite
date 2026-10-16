"""Task dependency optimistic concurrency, update-governance parity, update atomicity,
`exclude_dependency_id` validation, and the approval-apply TOCTOU fix."""
from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.platform.application.approval.dto.commands.decisions import (
    ApprovalDecisionCommand,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
)


def _login(services, username: str, password: str):
    user_session = services["user_session"]
    user = services["authentication"].authenticate(username, password)
    user_session.set_principal(services["principal_builder"].build(user))


def _login_eligible_reviewer(services):
    _login(services, "admin", "ChangeMe123!")
    services["user_registration"].register_user(
        "dependency-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "dependency-reviewer", "StrongPass123")


def _make_two_tasks(services):
    project = services['project_create'].create_project(ProjectCreateCommand(name="Dependency Concurrency", description=""))
    a = services['task_lifecycle_commands'].create_task(project.id, "Task A", "", start_date=date(2023, 11, 6), duration_days=2)
    b = services['task_lifecycle_commands'].create_task(project.id, "Task B", "", duration_days=2)
    return project, a, b


class TestOptimisticConcurrency:
    def test_concurrent_update_raises_instead_of_last_write_wins(self, services):
        """Two callers read the same dependency, then both try to update it.
        The second must get a stale-write error, not silently overwrite the
        first caller's change."""
        dependency_commands = services['task_dependency_commands']
        _project, a, b = _make_two_tasks(services)
        dep = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        # Both "callers" start from the same version.
        services['task_dependency_commands'].update_dependency(dep.id, lag_days=1)

        # A second caller, still holding the pre-update version, tries to
        # write on top of it.
        with pytest.raises(ConcurrencyError):
            dependency_commands._dependency_repo.update(
                __import__("dataclasses").replace(dep, lag_days=5)
            )

    def test_concurrent_double_delete_does_not_report_false_success(self, services):
        _project, a, b = _make_two_tasks(services)
        dep = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        services['task_dependency_commands'].remove_dependency(dep.id)

        # A second caller that read the dependency before the first delete
        # tries to delete it again with the same (now stale/nonexistent) id.
        with pytest.raises(NotFoundError):
            services['task_dependency_commands'].remove_dependency(dep.id)


class TestUpdateOptimisticConcurrency:
    """`update_dependency` must detect when the dependency changed underneath the caller between
    read and write -- a stale client payload must never silently overwrite a newer version."""

    def test_update_with_stale_expected_version_raises_instead_of_overwriting(self, services):
        _project, a, b = _make_two_tasks(services)
        dep = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
        stale_version = services['task_dependency_query'].get_dependency(dep.id).version

        # Someone else updates it first, bumping the version.
        services['task_dependency_commands'].update_dependency(dep.id, lag_days=1)

        # The original caller, still holding the pre-update version, tries
        # to save on top of it.
        with pytest.raises(ConcurrencyError):
            services['task_dependency_commands'].update_dependency(dep.id, lag_days=9, expected_version=stale_version)

        # The first writer's change must survive -- no silent overwrite.
        assert services['task_dependency_query'].get_dependency(dep.id).lag_days == 1

    def test_update_with_matching_expected_version_succeeds(self, services):
        _project, a, b = _make_two_tasks(services)
        dep = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
        current_version = services['task_dependency_query'].get_dependency(dep.id).version

        services['task_dependency_commands'].update_dependency(dep.id, lag_days=4, expected_version=current_version)

        assert services['task_dependency_query'].get_dependency(dep.id).lag_days == 4

    def test_update_without_expected_version_is_unchecked(self, services):
        """Callers that don't supply a version (e.g. internal callers)
        keep the pre-existing unchecked behavior -- only the QML edit
        dialog opts into the check by supplying its loaded version."""
        _project, a, b = _make_two_tasks(services)
        dep = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        services['task_dependency_commands'].update_dependency(dep.id, lag_days=1)
        services['task_dependency_commands'].update_dependency(dep.id, lag_days=2)

        assert services['task_dependency_query'].get_dependency(dep.id).lag_days == 2

    def test_governed_update_apply_rechecks_expected_version_captured_at_request_time(self, services, monkeypatch):
        """The requester's expected_version (captured when THEY opened the
        dialog) must be re-checked at approval-apply time, which can be
        much later -- if the dependency changed in the meantime, applying
        the stale request must fail rather than silently overwrite."""
        monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
        monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "dependency.update")
        _login(services, "admin", "ChangeMe123!")

        approvals = services["approval_commands"]
        project, a, b = _make_two_tasks(services)
        dep = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        services["user_registration"].register_user("planner-dep-update-toctou", "StrongPass123", role_names=["planner"])
        _login(services, "planner-dep-update-toctou", "StrongPass123")

        with pytest.raises(BusinessRuleError, match="Approval required"):
            services['task_dependency_commands'].update_dependency(dep.id, lag_days=3)

        req = services["approval_queries"].list_pending(project_id=project.id)[0]
        assert req.payload["expected_version"] == 1

        # The graph changes while the request is pending: an admin edits
        # the same dependency directly, bumping its version.
        _login(services, "admin", "ChangeMe123!")
        services['task_dependency_commands'].update_dependency(dep.id, lag_days=7)
        assert services['task_dependency_query'].get_dependency(dep.id).version == 2

        _login_eligible_reviewer(services)
        with pytest.raises(ConcurrencyError):
            approvals.approve_and_apply(ApprovalDecisionCommand(request_id=req.id))

        # The admin's direct edit must survive -- the stale pending
        # request must not silently overwrite it.
        assert services['task_dependency_query'].get_dependency(dep.id).lag_days == 7


class TestUpdateGovernanceParity:
    def test_update_requires_approval_when_governed(self, services, monkeypatch):
        monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
        monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "dependency.update")
        _login(services, "admin", "ChangeMe123!")

        approvals = services["approval_commands"]
        project, a, b = _make_two_tasks(services)
        dep = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        services["user_registration"].register_user("planner-dep-update", "StrongPass123", role_names=["planner"])
        _login(services, "planner-dep-update", "StrongPass123")

        with pytest.raises(BusinessRuleError, match="Approval required"):
            services['task_dependency_commands'].update_dependency(dep.id, lag_days=3)

        # Not applied yet.
        assert services['task_dependency_query'].get_dependency(dep.id).lag_days == 0

        req = services["approval_queries"].list_pending(project_id=project.id)[0]
        assert req.request_type == "dependency.update"

        _login_eligible_reviewer(services)
        approvals.approve_and_apply(ApprovalDecisionCommand(request_id=req.id))

        assert services['task_dependency_query'].get_dependency(dep.id).lag_days == 3

    def test_update_applies_immediately_when_not_governed(self, services):
        """Default (ungoverned) behavior is unchanged."""
        _project, a, b = _make_two_tasks(services)
        dep = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
        services['task_dependency_commands'].update_dependency(dep.id, lag_days=2)
        assert services['task_dependency_query'].get_dependency(dep.id).lag_days == 2


class TestUpdateValidation:
    def test_update_does_not_trip_duplicate_against_itself(self, services):
        """Re-saving an existing edge's own lag/type must not be rejected
        as a duplicate of itself (the old code worked around this by
        blindly whitelisting DEPENDENCY_DUPLICATE, which also made the
        cycle check unreachable on this path)."""
        _project, a, b = _make_two_tasks(services)
        dep = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
        updated = services['task_dependency_commands'].update_dependency(dep.id, dependency_type=DependencyType.START_TO_START, lag_days=1)
        assert updated.dependency_type == DependencyType.START_TO_START
        assert updated.lag_days == 1

    def test_exclude_dependency_id_excludes_only_the_named_edge(self, services):
        """exclude_dependency_id must exclude ONLY the specified edge from
        the duplicate scan, not duplicate-checking altogether -- update
        itself can never legitimately trigger DEPENDENCY_DUPLICATE against
        a different edge (endpoints can't change via update, and
        uniqueness is scoped to the (predecessor, successor) pair), so this
        exercises the diagnostics primitive directly at its actual
        boundary: a real duplicate pair, with exclude_dependency_id pointed
        at an unrelated third edge, must still be rejected."""
        project, a, b = _make_two_tasks(services)
        c = services['task_lifecycle_commands'].create_task(project.id, "Task C", "", duration_days=1)
        existing = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
        unrelated = services['task_dependency_commands'].add_dependency(a.id, c.id, DependencyType.FINISH_TO_START, lag_days=0)

        diagnostic = services["task_dependency_diagnostics"].get_dependency_diagnostics(
            predecessor_id=a.id,
            successor_id=b.id,
            dependency_type=DependencyType.START_TO_START,
            lag_days=0,
            include_impact=False,
            exclude_dependency_id=unrelated.id,
        )
        assert diagnostic.is_valid is False
        assert diagnostic.code == "DEPENDENCY_DUPLICATE"

        # Excluding the edge's OWN id is what makes updating it possible.
        diagnostic_self_excluded = services["task_dependency_diagnostics"].get_dependency_diagnostics(
            predecessor_id=a.id,
            successor_id=b.id,
            dependency_type=DependencyType.START_TO_START,
            lag_days=0,
            include_impact=False,
            exclude_dependency_id=existing.id,
        )
        assert diagnostic_self_excluded.is_valid is True


class TestApprovalApplyToctou:
    def test_add_approval_apply_revalidates_and_rejects_a_now_invalid_request(self, services, monkeypatch):
        """The audit's TOCTOU scenario: a dependency.add request is valid
        when submitted, but the graph changes before an approver applies
        it, making it invalid (here: the successor became a summary/parent
        task in the meantime). Apply-time re-validation must catch this
        rather than blindly persisting the original request."""
        monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
        monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "dependency.add")
        _login(services, "admin", "ChangeMe123!")

        approvals = services["approval_commands"]
        project, a, b = _make_two_tasks(services)

        services["user_registration"].register_user("planner-dep-toctou", "StrongPass123", role_names=["planner"])
        _login(services, "planner-dep-toctou", "StrongPass123")

        # b is still a leaf task at REQUEST time, so this passes validation
        # and creates a pending approval request.
        with pytest.raises(BusinessRuleError, match="Approval required"):
            services['task_dependency_commands'].add_dependency(a.id, b.id)

        req = services["approval_queries"].list_pending(project_id=project.id)[0]

        # The graph changes while the request is pending: b gains a child,
        # becoming a summary task. A request that was valid when submitted
        # is now invalid.
        _login(services, "admin", "ChangeMe123!")
        services['task_lifecycle_commands'].create_task(project.id, "Task B Child", "", duration_days=1, parent_task_id=b.id)

        with pytest.raises(BusinessRuleError):
            approvals.approve_and_apply(ApprovalDecisionCommand(request_id=req.id))

        assert services['task_dependency_query'].list_dependencies_for_task(b.id) == []
