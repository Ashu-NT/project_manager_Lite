"""Phase G/H regressions: optimistic concurrency, update-governance parity,
update atomicity, exclude_dependency_id validation, and the approval-apply
TOCTOU fix. See
docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
§8/§16/Phase G/Phase H for the audit findings these close.
"""
from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.domain.enums import DependencyType
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError


def _login(services, username: str, password: str):
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _make_two_tasks(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Dependency Concurrency", "")
    a = ts.create_task(project.id, "Task A", "", start_date=date(2023, 11, 6), duration_days=2)
    b = ts.create_task(project.id, "Task B", "", duration_days=2)
    return project, a, b


class TestOptimisticConcurrency:
    def test_concurrent_update_raises_instead_of_last_write_wins(self, services):
        """Two callers read the same dependency, then both try to update it.
        The second must get a stale-write error, not silently overwrite the
        first caller's change."""
        ts = services["task_service"]
        _project, a, b = _make_two_tasks(services)
        dep = ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        # Both "callers" start from the same version.
        ts.update_dependency(dep.id, lag_days=1)

        # A second caller, still holding the pre-update version, tries to
        # write on top of it.
        with pytest.raises(ConcurrencyError):
            ts._dependency_repo.update(
                __import__("dataclasses").replace(dep, lag_days=5)
            )

    def test_concurrent_double_delete_does_not_report_false_success(self, services):
        ts = services["task_service"]
        _project, a, b = _make_two_tasks(services)
        dep = ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        ts.remove_dependency(dep.id)

        # A second caller that read the dependency before the first delete
        # tries to delete it again with the same (now stale/nonexistent) id.
        with pytest.raises(NotFoundError):
            ts.remove_dependency(dep.id)


class TestUpdateGovernanceParity:
    def test_update_requires_approval_when_governed(self, services, monkeypatch):
        monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
        monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "dependency.update")
        _login(services, "admin", "ChangeMe123!")

        auth = services["auth_service"]
        approvals = services["approval_service"]
        ts = services["task_service"]
        project, a, b = _make_two_tasks(services)
        dep = ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        auth.register_user("planner-dep-update", "StrongPass123", role_names=["planner"])
        _login(services, "planner-dep-update", "StrongPass123")

        with pytest.raises(BusinessRuleError, match="Approval required"):
            ts.update_dependency(dep.id, lag_days=3)

        # Not applied yet.
        assert ts.get_dependency(dep.id).lag_days == 0

        req = approvals.list_pending(project_id=project.id)[0]
        assert req.request_type == "dependency.update"

        _login(services, "admin", "ChangeMe123!")
        approvals.approve_and_apply(req.id)

        assert ts.get_dependency(dep.id).lag_days == 3

    def test_update_applies_immediately_when_not_governed(self, services):
        """Default (ungoverned) behavior is unchanged."""
        ts = services["task_service"]
        _project, a, b = _make_two_tasks(services)
        dep = ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
        ts.update_dependency(dep.id, lag_days=2)
        assert ts.get_dependency(dep.id).lag_days == 2


class TestUpdateValidation:
    def test_update_does_not_trip_duplicate_against_itself(self, services):
        """Re-saving an existing edge's own lag/type must not be rejected
        as a duplicate of itself (the old code worked around this by
        blindly whitelisting DEPENDENCY_DUPLICATE, which also made the
        cycle check unreachable on this path)."""
        ts = services["task_service"]
        _project, a, b = _make_two_tasks(services)
        dep = ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
        updated = ts.update_dependency(dep.id, dependency_type=DependencyType.START_TO_START, lag_days=1)
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
        ts = services["task_service"]
        project, a, b = _make_two_tasks(services)
        c = ts.create_task(project.id, "Task C", "", duration_days=1)
        existing = ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
        unrelated = ts.add_dependency(a.id, c.id, DependencyType.FINISH_TO_START, lag_days=0)

        diagnostic = ts.get_dependency_diagnostics(
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
        diagnostic_self_excluded = ts.get_dependency_diagnostics(
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

        auth = services["auth_service"]
        approvals = services["approval_service"]
        ts = services["task_service"]
        project, a, b = _make_two_tasks(services)

        auth.register_user("planner-dep-toctou", "StrongPass123", role_names=["planner"])
        _login(services, "planner-dep-toctou", "StrongPass123")

        # b is still a leaf task at REQUEST time, so this passes validation
        # and creates a pending approval request.
        with pytest.raises(BusinessRuleError, match="Approval required"):
            ts.add_dependency(a.id, b.id)

        req = approvals.list_pending(project_id=project.id)[0]

        # The graph changes while the request is pending: b gains a child,
        # becoming a summary task. A request that was valid when submitted
        # is now invalid.
        _login(services, "admin", "ChangeMe123!")
        ts.create_task(project.id, "Task B Child", "", duration_days=1, parent_task_id=b.id)

        with pytest.raises(BusinessRuleError):
            approvals.approve_and_apply(req.id)

        assert ts.list_dependencies_for_task(b.id) == []
