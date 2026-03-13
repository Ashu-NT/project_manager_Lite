from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.platform.common.exceptions import BusinessRuleError, ValidationError
from tests.ui_runtime_helpers import login_as, register_and_login
from ui.platform.admin.access.tab import AccessTab
from ui.modules.project_management.collaboration.tab import CollaborationTab
from ui.modules.project_management.portfolio.tab import PortfolioTab


def test_auth_service_locks_accounts_and_expires_sessions(services, monkeypatch):
    auth = services["auth_service"]
    user_session = services["user_session"]
    monkeypatch.setenv("PM_AUTH_LOCKOUT_ATTEMPTS", "2")
    monkeypatch.setenv("PM_AUTH_LOCKOUT_MINUTES", "30")

    user = auth.register_user("locked-user", "StrongPass123", role_names=["viewer"])

    with pytest.raises(ValidationError, match="Invalid credentials"):
        auth.authenticate("locked-user", "wrong-pass")
    with pytest.raises(ValidationError, match="Invalid credentials"):
        auth.authenticate("locked-user", "wrong-pass")
    with pytest.raises(ValidationError, match="Account is locked until"):
        auth.authenticate("locked-user", "StrongPass123")

    locked = next(row for row in auth.list_users() if row.id == user.id)
    assert locked.failed_login_attempts == 2
    assert locked.locked_until is not None

    auth.unlock_user_account(user.id)
    unlocked = next(row for row in auth.list_users() if row.id == user.id)
    assert unlocked.failed_login_attempts == 0
    assert unlocked.locked_until is None

    authenticated = auth.authenticate("locked-user", "StrongPass123")
    authenticated.session_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    services["session"].commit()
    user_session.set_principal(auth.build_principal(authenticated))

    assert user_session.is_authenticated() is False
    assert user_session.principal is None


def test_project_memberships_restrict_project_and_task_queries(services):
    auth = services["auth_service"]
    access = services["access_service"]
    project_service = services["project_service"]
    task_service = services["task_service"]

    project_alpha = project_service.create_project("Scoped Alpha")
    project_beta = project_service.create_project("Scoped Beta")
    task_service.create_task(project_alpha.id, "Alpha Task")
    task_service.create_task(project_beta.id, "Beta Task")
    viewer = auth.register_user("scoped-viewer", "StrongPass123", role_names=["viewer"])

    access.assign_project_membership(
        project_id=project_alpha.id,
        user_id=viewer.id,
        scope_role="viewer",
    )

    login_as(services, "scoped-viewer", "StrongPass123")

    visible_projects = project_service.list_projects()
    assert [project.id for project in visible_projects] == [project_alpha.id]
    assert services["user_session"].is_project_restricted() is True
    assert services["user_session"].has_project_permission(project_alpha.id, "task.read") is True
    assert services["user_session"].has_project_permission(project_beta.id, "task.read") is False
    assert [task.name for task in task_service.list_tasks_for_project(project_alpha.id)] == ["Alpha Task"]

    with pytest.raises(BusinessRuleError, match="Missing scoped 'task.read' access"):
        task_service.list_tasks_for_project(project_beta.id)


def test_collaboration_inbox_filters_by_project_scope_and_marks_mentions_read(services):
    auth = services["auth_service"]
    access = services["access_service"]
    project_service = services["project_service"]
    task_service = services["task_service"]
    collaboration = services["collaboration_service"]

    project_alpha = project_service.create_project("Collab Alpha")
    project_beta = project_service.create_project("Collab Beta")
    task_alpha = task_service.create_task(project_alpha.id, "Alpha Task")
    task_beta = task_service.create_task(project_beta.id, "Beta Task")
    viewer = auth.register_user("collab-viewer", "StrongPass123", role_names=["viewer"])
    beta_viewer = auth.register_user("collab-beta-viewer", "StrongPass123", role_names=["viewer"])

    access.assign_project_membership(
        project_id=project_alpha.id,
        user_id=viewer.id,
        scope_role="viewer",
    )
    access.assign_project_membership(
        project_id=project_beta.id,
        user_id=beta_viewer.id,
        scope_role="viewer",
    )
    collaboration.post_comment(task_id=task_alpha.id, body="Please review @collab-viewer")
    collaboration.post_comment(task_id=task_beta.id, body="Do not show @collab-beta-viewer")

    login_as(services, "collab-viewer", "StrongPass123")

    inbox = collaboration.list_inbox()
    assert len(inbox) == 1
    assert inbox[0].project_id == project_alpha.id
    assert collaboration.unread_mentions_count() == 1

    collaboration.mark_task_mentions_read(task_alpha.id)

    refreshed = collaboration.list_inbox()
    assert len(refreshed) == 1
    assert refreshed[0].unread is False
    assert collaboration.unread_mentions_count() == 0


def test_portfolio_scenario_evaluation_rolls_up_budget_and_capacity(services):
    project_service = services["project_service"]
    portfolio = services["portfolio_service"]
    resource_service = services["resource_service"]

    resource_service.create_resource("Portfolio Analyst", hourly_rate=100.0, capacity_percent=50.0)
    project = project_service.create_project("Portfolio Project", planned_budget=500.0)
    intake = portfolio.create_intake_item(
        title="New Initiative",
        sponsor_name="PMO",
        requested_budget=600.0,
        requested_capacity_percent=70.0,
        strategic_score=5,
        value_score=4,
        urgency_score=4,
        risk_score=2,
    )
    scenario = portfolio.create_scenario(
        name="Tight Plan",
        budget_limit=1_000.0,
        capacity_limit_percent=60.0,
        project_ids=[project.id],
        intake_item_ids=[intake.id],
    )

    result = portfolio.evaluate_scenario(scenario.id)

    assert result.selected_projects == 1
    assert result.selected_intake_items == 1
    assert result.total_budget == pytest.approx(1_100.0)
    assert result.total_capacity_percent == pytest.approx(70.0)
    assert result.available_capacity_percent == pytest.approx(50.0)
    assert result.over_budget is True
    assert result.over_capacity is True
    assert "over budget" in result.summary
    assert "over capacity" in result.summary


def test_access_tab_shows_memberships_and_security_runtime(qapp, services):
    auth = services["auth_service"]
    access = services["access_service"]
    project = services["project_service"].create_project("Access UI Project")
    user = auth.register_user("access-ui", "StrongPass123", role_names=["viewer"])
    access.assign_project_membership(project_id=project.id, user_id=user.id, scope_role="viewer")

    tab = AccessTab(
        access_service=access,
        auth_service=auth,
        project_service=services["project_service"],
        user_session=services["user_session"],
    )

    assert tab.project_combo.currentData() == project.id
    assert tab.membership_table.rowCount() == 1
    assert tab.membership_table.item(0, 0).text() == "access-ui"
    assert tab.security_table.rowCount() >= 2
    assert tab.btn_unlock.isEnabled() is True


def test_access_tab_auto_refreshes_for_user_and_membership_events(qapp, services):
    auth = services["auth_service"]
    access = services["access_service"]
    project = services["project_service"].create_project("Access Events Project")
    tab = AccessTab(
        access_service=access,
        auth_service=auth,
        project_service=services["project_service"],
        user_session=services["user_session"],
    )

    assert tab.security_table.rowCount() == 1
    assert tab.membership_table.rowCount() == 0

    user = auth.register_user("access-events", "StrongPass123", role_names=["viewer"])
    qapp.processEvents()
    assert tab.security_table.rowCount() == 2

    access.assign_project_membership(project_id=project.id, user_id=user.id, scope_role="viewer")
    qapp.processEvents()
    assert tab.membership_table.rowCount() == 1


def test_collaboration_tab_auto_refreshes_when_task_comments_change(qapp, services):
    project = services["project_service"].create_project("Collaboration Events Project")
    task = services["task_service"].create_task(project.id, "Comment Sync Task")
    tab = CollaborationTab(collaboration_service=services["collaboration_service"])

    assert tab.inbox_table.rowCount() == 0

    services["task_collaboration_store"].add_comment(
        task_id=task.id,
        author="alice",
        body="Please check this @admin",
        attachments=[],
    )
    qapp.processEvents()

    assert tab.inbox_table.rowCount() == 1
    assert tab.activity_table.rowCount() == 1
    assert tab.inbox_table.item(0, 1).text() == project.name
    assert tab.inbox_table.item(0, 2).text() == task.name


def test_portfolio_tab_auto_refreshes_for_project_and_portfolio_events(qapp, services):
    tab = PortfolioTab(
        portfolio_service=services["portfolio_service"],
        project_service=services["project_service"],
        user_session=services["user_session"],
    )

    assert tab.project_list.count() == 0
    assert tab.intake_table.rowCount() == 0

    services["project_service"].create_project("Portfolio Event Project")
    qapp.processEvents()
    assert tab.project_list.count() == 1

    services["portfolio_service"].create_intake_item(
        title="Portfolio Event Intake",
        sponsor_name="PMO",
    )
    qapp.processEvents()
    assert tab.intake_table.rowCount() == 1


def test_portfolio_tab_disables_manage_actions_for_read_only_user(qapp, services):
    register_and_login(services, username_prefix="planner-portfolio", role_names=("planner",))

    tab = PortfolioTab(
        portfolio_service=services["portfolio_service"],
        project_service=services["project_service"],
        user_session=services["user_session"],
    )

    assert tab.btn_add_intake.isEnabled() is False
    assert tab.btn_save_scenario.isEnabled() is False
    assert "portfolio.manage" in tab.btn_add_intake.toolTip()
    assert "portfolio.manage" in tab.btn_save_scenario.toolTip()
