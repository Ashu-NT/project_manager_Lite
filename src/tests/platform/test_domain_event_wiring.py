from datetime import date

import pytest

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.shared.events.domain_events import domain_events
def _login_as(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def test_project_create_emits_typed_domain_event_and_view_invalidation(services):
    """P43: `project_changed` is deleted -- `create_project` now records a typed `ProjectCreated`
    DomainEvent, delivered as a `project_list` ViewInvalidation hint."""
    from src.core.modules.project_management.application.projects.event_handlers.view_invalidation import (
        PROJECT_CATEGORY,
        PROJECT_LIST_SCOPE_CODE,
    )

    ps = services["project_service"]

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    hints: list = []
    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )

    project = ps.create_project("Event Project", "")

    project_hints = [h for h in hints if h.category == PROJECT_CATEGORY]
    assert len(project_hints) == 1
    assert project_hints[0].scope_code == PROJECT_LIST_SCOPE_CODE
    assert project_hints[0].entity_id == project.id


def test_project_update_emits_typed_domain_event_and_view_invalidation(services):
    """P43: `project_changed` is deleted -- `update_project` now records a typed
    `ProjectProfileUpdated` DomainEvent, delivered as both `project_list` and `project_detail`
    ViewInvalidation hints."""
    from src.core.modules.project_management.application.projects.event_handlers.view_invalidation import (
        PROJECT_CATEGORY,
        PROJECT_DETAIL_SCOPE_CODE,
        PROJECT_LIST_SCOPE_CODE,
    )

    ps = services["project_service"]
    project = ps.create_project("Event Update Project", "")

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    hints: list = []
    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )

    ps.update_project(project.id, name="Event Update Project V2")

    project_hints = [h for h in hints if h.category == PROJECT_CATEGORY]
    scope_codes = {h.scope_code for h in project_hints}
    assert scope_codes == {PROJECT_LIST_SCOPE_CODE, PROJECT_DETAIL_SCOPE_CODE}
    assert all(h.entity_id == project.id for h in project_hints)


def test_task_create_dependency_assignment_emit_tasks_changed(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Event Task Ops", "")
    t1 = ts.create_task(project.id, "Task A", start_date=date(2024, 1, 1), duration_days=2)
    t2 = ts.create_task(project.id, "Task B", start_date=date(2024, 1, 3), duration_days=2)
    resource = rs.create_resource("Event Dev", "Developer", hourly_rate=100.0)
    seen: list[str] = []

    def _on_tasks_changed(project_id: str) -> None:
        seen.append(project_id)

    domain_events.tasks_changed.connect(_on_tasks_changed)
    try:
        t3 = ts.create_task(project.id, "Task C", start_date=date(2024, 1, 6), duration_days=1)
        ts.add_dependency(t1.id, t2.id, DependencyType.FINISH_TO_START, lag_days=0)
        ts.assign_resource(t3.id, resource.id, allocation_percent=50.0)
    finally:
        domain_events.tasks_changed.disconnect(_on_tasks_changed)

    assert seen.count(project.id) >= 3


def test_task_update_emits_tasks_changed(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Event Task Update", "")
    task = ts.create_task(project.id, "Task A", start_date=date(2024, 1, 1), duration_days=2)
    seen: list[str] = []

    def _on_tasks_changed(project_id: str) -> None:
        seen.append(project_id)

    domain_events.tasks_changed.connect(_on_tasks_changed)
    try:
        ts.update_task(task.id, name="Task A Updated")
    finally:
        domain_events.tasks_changed.disconnect(_on_tasks_changed)

    assert seen == [project.id]



def test_approve_baseline_request_emits_project_baseline_view_invalidation(services, monkeypatch):
    """P23: `baseline_changed` is retired -- an approved `baseline.create` request now produces
    a typed `ProjectBaselineCreated` DomainEvent, delivered as a `project_baseline`
    ViewInvalidation hint scoped to the requesting project."""
    from src.core.modules.project_management.application.scheduling.baselines.event_handlers.view_invalidation import (
        BASELINE_CATEGORY,
        BASELINE_PROJECT_SCOPE_CODE,
    )

    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "baseline.create")
    auth = services["auth_service"]
    auth.register_user("planner-baseline", "StrongPass123", role_names=["planner"])
    _login_as(services, "admin", "ChangeMe123!")

    ps = services["project_service"]
    ts = services["task_service"]
    approvals = services["approval_service"]
    baseline = services["baseline_service"]
    project = ps.create_project("Approval baseline events")
    ts.create_task(project.id, "Task A", start_date=date(2024, 1, 1), duration_days=1)
    _login_as(services, "planner-baseline", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="Approval required"):
        baseline.create_baseline(project.id, "Gate 1", rate_as_of=date.today())
    request_id = approvals.list_pending(project_id=project.id)[0].id

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    hints: list = []
    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )

    _login_as(services, "admin", "ChangeMe123!")
    approvals.approve_and_apply(request_id, note="Approved")

    baseline_hints = [h for h in hints if h.category == BASELINE_CATEGORY]
    assert len(baseline_hints) == 1
    assert baseline_hints[0].scope_code == BASELINE_PROJECT_SCOPE_CODE
    assert baseline_hints[0].scope.entity_id == project.id

