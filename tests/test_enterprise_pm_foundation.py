from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

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


def test_collaboration_notifications_filter_project_scope_for_mentions_and_timesheet_workflow(services):
    auth = services["auth_service"]
    access = services["access_service"]
    project_service = services["project_service"]
    task_service = services["task_service"]
    resource_service = services["resource_service"]
    timesheet_service = services["timesheet_service"]
    collaboration = services["collaboration_service"]

    project_alpha = project_service.create_project("Notifications Alpha")
    project_beta = project_service.create_project("Notifications Beta")
    task_alpha = task_service.create_task(project_alpha.id, "Alpha Delivery Task")
    task_beta = task_service.create_task(project_beta.id, "Beta Delivery Task")
    viewer = auth.register_user("notify-viewer", "StrongPass123", role_names=["viewer"])

    access.assign_project_membership(
        project_id=project_alpha.id,
        user_id=viewer.id,
        scope_role="viewer",
    )
    collaboration.post_comment(task_id=task_alpha.id, body="Please review @notify-viewer")

    resource = resource_service.create_resource("Shared Contributor", hourly_rate=95.0)
    assignment_alpha = task_service.assign_resource(task_alpha.id, resource.id, 50.0)
    assignment_beta = task_service.assign_resource(task_beta.id, resource.id, 50.0)
    timesheet_service.add_time_entry(
        assignment_alpha.id,
        entry_date=date(2026, 6, 2),
        hours=3.0,
        note="Alpha execution",
    )
    timesheet_service.add_time_entry(
        assignment_beta.id,
        entry_date=date(2026, 6, 3),
        hours=2.5,
        note="Beta execution",
    )
    timesheet_service.submit_timesheet_period(
        resource.id,
        period_start=date(2026, 6, 1),
        note="Ready for review",
    )

    login_as(services, "notify-viewer", "StrongPass123")

    notifications = collaboration.list_notifications(limit=20)

    mention = next(item for item in notifications if item.notification_type == "mention")
    timesheet_notice = next(item for item in notifications if item.notification_type == "timesheet")

    assert mention.project_id == project_alpha.id
    assert mention.project_name == project_alpha.name
    assert timesheet_notice.project_name == project_alpha.name
    assert project_beta.name not in timesheet_notice.project_name
    assert "Timesheet submitted" in timesheet_notice.headline


def test_collaboration_service_tracks_active_task_presence(services):
    project = services["project_service"].create_project("Presence Project")
    task = services["task_service"].create_task(project.id, "Presence Task")
    collaboration = services["collaboration_service"]

    assert collaboration.list_task_presence(task.id) == []

    collaboration.touch_task_presence(task.id, activity="editing")

    active = collaboration.list_task_presence(task.id)
    assert len(active) == 1
    assert active[0].task_id == task.id
    assert active[0].task_name == task.name
    assert active[0].project_id == project.id
    assert active[0].project_name == project.name
    assert active[0].username == "admin"
    assert active[0].activity == "editing"
    assert active[0].is_self is True

    collaboration.clear_task_presence(task.id)
    assert collaboration.list_task_presence(task.id) == []


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


def test_portfolio_scenario_comparison_highlights_delta_and_selection_changes(services):
    project_service = services["project_service"]
    portfolio = services["portfolio_service"]
    resource_service = services["resource_service"]

    resource_service.create_resource("Portfolio Capacity", hourly_rate=95.0, capacity_percent=100.0)
    project_alpha = project_service.create_project("Portfolio Alpha", planned_budget=400.0)
    project_beta = project_service.create_project("Portfolio Beta", planned_budget=700.0)
    intake_keep = portfolio.create_intake_item(
        title="Legacy Intake",
        sponsor_name="PMO",
        requested_budget=200.0,
        requested_capacity_percent=30.0,
        strategic_score=4,
        value_score=3,
        urgency_score=3,
        risk_score=2,
    )
    intake_expand = portfolio.create_intake_item(
        title="Expansion Intake",
        sponsor_name="PMO",
        requested_budget=150.0,
        requested_capacity_percent=10.0,
        strategic_score=5,
        value_score=4,
        urgency_score=4,
        risk_score=1,
    )
    baseline = portfolio.create_scenario(
        name="Baseline Scenario",
        budget_limit=900.0,
        capacity_limit_percent=60.0,
        project_ids=[project_alpha.id],
        intake_item_ids=[intake_keep.id],
    )
    candidate = portfolio.create_scenario(
        name="Expansion Scenario",
        budget_limit=1_400.0,
        capacity_limit_percent=90.0,
        project_ids=[project_alpha.id, project_beta.id],
        intake_item_ids=[intake_expand.id],
    )

    comparison = portfolio.compare_scenarios(baseline.id, candidate.id)

    assert comparison.base_scenario_name == "Baseline Scenario"
    assert comparison.candidate_scenario_name == "Expansion Scenario"
    assert comparison.budget_delta == pytest.approx(650.0)
    assert comparison.capacity_delta_percent == pytest.approx(-20.0)
    assert comparison.selected_projects_delta == 1
    assert comparison.selected_intake_items_delta == 0
    assert comparison.added_project_names == ["Portfolio Beta"]
    assert comparison.added_intake_titles == ["Expansion Intake"]
    assert comparison.removed_intake_titles == ["Legacy Intake"]
    assert "Expansion Scenario vs Baseline Scenario" in comparison.summary


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


def test_access_tab_switches_to_platform_only_state_when_pm_module_disabled(qapp, services):
    project = services["project_service"].create_project("Access Disabled Project")
    tab = AccessTab(
        access_service=services["access_service"],
        auth_service=services["auth_service"],
        project_service=services["project_service"],
        user_session=services["user_session"],
    )

    assert tab.project_combo.count() == 1
    assert tab.btn_assign.isEnabled() is True

    services["module_catalog_service"].set_module_state("project_management", enabled=False)
    qapp.processEvents()

    assert tab.project_combo.count() == 0
    assert tab.membership_table.rowCount() == 0
    assert tab.btn_assign.isEnabled() is False
    assert tab.btn_remove.isEnabled() is False
    assert "disabled" in tab.membership_hint.text().lower()


def test_collaboration_tab_auto_refreshes_when_task_comments_change(qapp, services):
    project = services["project_service"].create_project("Collaboration Events Project")
    task = services["task_service"].create_task(project.id, "Comment Sync Task")
    tab = CollaborationTab(collaboration_service=services["collaboration_service"])

    assert tab.sections_tabs.count() == 4
    assert tab.sections_tabs.tabText(0) == "Notifications (0)"
    assert tab.sections_tabs.tabText(1) == "Mentions (0)"
    assert tab.sections_tabs.tabText(2) == "Recent Activity (0)"
    assert tab.sections_tabs.tabText(3) == "Active Now (0)"
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
    assert tab.sections_tabs.tabText(1) == "Mentions (1)"
    assert tab.sections_tabs.tabText(2) == "Recent Activity (1)"
    assert tab.inbox_table.item(0, 1).text() == project.name
    assert tab.inbox_table.item(0, 2).text() == task.name


def test_collaboration_tab_shows_active_presence_rows(qapp, services):
    project = services["project_service"].create_project("Presence Events Project")
    task = services["task_service"].create_task(project.id, "Presence Sync Task")
    tab = CollaborationTab(collaboration_service=services["collaboration_service"])

    assert tab.active_table.rowCount() == 0

    services["collaboration_service"].touch_task_presence(task.id, activity="reviewing")
    qapp.processEvents()

    assert tab.active_table.rowCount() == 1
    assert tab.active_label.text() == "Active now: 1"
    assert tab.sections_tabs.tabText(3) == "Active Now (1)"
    assert tab.active_table.item(0, 1).text() == project.name
    assert tab.active_table.item(0, 2).text() == task.name
    assert tab.active_table.item(0, 4).text() == "Reviewing"


def test_collaboration_tab_refreshes_when_timesheet_period_notifications_change(qapp, services):
    project = services["project_service"].create_project("Collaboration Timesheet Events Project")
    task = services["task_service"].create_task(project.id, "Timesheet Sync Task")
    resource = services["resource_service"].create_resource("Collaboration Worker", hourly_rate=110.0)
    assignment = services["task_service"].assign_resource(task.id, resource.id, 100.0)
    tab = CollaborationTab(collaboration_service=services["collaboration_service"])

    assert tab.notifications_table.rowCount() == 0

    services["timesheet_service"].add_time_entry(
        assignment.id,
        entry_date=date(2026, 6, 4),
        hours=4.0,
        note="Execution work",
    )
    qapp.processEvents()
    assert tab.notifications_table.rowCount() == 0

    services["timesheet_service"].submit_timesheet_period(
        resource.id,
        period_start=date(2026, 6, 1),
        note="Ready for approval",
    )
    qapp.processEvents()

    assert tab.notifications_table.rowCount() == 1
    assert tab.notification_label.text() == "Notifications: 1"
    assert tab.notifications_table.item(0, 1).text() == "Timesheet"
    assert tab.notifications_table.item(0, 2).text() == project.name
    assert "Timesheet submitted" in tab.notifications_table.item(0, 4).text()


def test_portfolio_tab_auto_refreshes_for_project_and_portfolio_events(qapp, services):
    tab = PortfolioTab(
        portfolio_service=services["portfolio_service"],
        project_service=services["project_service"],
        user_session=services["user_session"],
    )

    assert tab.scenario_tabs.count() == 2
    assert tab.scenario_tabs.tabText(0) == "Saved Scenarios"
    assert tab.scenario_tabs.tabText(1) == "Compare"
    assert tab.scenario_options_label.text() == "Scenario options: 0 project(s), 0 intake item(s)."
    assert tab.intake_table.rowCount() == 0

    services["project_service"].create_project("Portfolio Event Project")
    qapp.processEvents()
    assert tab.scenario_options_label.text() == "Scenario options: 1 project(s), 0 intake item(s)."

    services["portfolio_service"].create_intake_item(
        title="Portfolio Event Intake",
        sponsor_name="PMO",
    )
    qapp.processEvents()
    assert tab.scenario_options_label.text() == "Scenario options: 1 project(s), 1 intake item(s)."
    assert tab.intake_table.rowCount() == 1


def test_portfolio_tab_compares_saved_scenarios_side_by_side(qapp, services):
    project_alpha = services["project_service"].create_project("UI Portfolio Alpha", planned_budget=350.0)
    project_beta = services["project_service"].create_project("UI Portfolio Beta", planned_budget=450.0)
    intake_alpha = services["portfolio_service"].create_intake_item(
        title="UI Intake Alpha",
        sponsor_name="PMO",
        requested_budget=100.0,
        requested_capacity_percent=20.0,
    )
    intake_beta = services["portfolio_service"].create_intake_item(
        title="UI Intake Beta",
        sponsor_name="PMO",
        requested_budget=180.0,
        requested_capacity_percent=35.0,
    )
    baseline = services["portfolio_service"].create_scenario(
        name="UI Baseline",
        budget_limit=600.0,
        capacity_limit_percent=50.0,
        project_ids=[project_alpha.id],
        intake_item_ids=[intake_alpha.id],
    )
    candidate = services["portfolio_service"].create_scenario(
        name="UI Candidate",
        budget_limit=1_200.0,
        capacity_limit_percent=90.0,
        project_ids=[project_alpha.id, project_beta.id],
        intake_item_ids=[intake_beta.id],
    )

    tab = PortfolioTab(
        portfolio_service=services["portfolio_service"],
        project_service=services["project_service"],
        user_session=services["user_session"],
    )
    qapp.processEvents()

    for idx in range(tab.base_compare_scenario.count()):
        if tab.base_compare_scenario.itemData(idx) == baseline.id:
            tab.base_compare_scenario.setCurrentIndex(idx)
            break
    qapp.processEvents()

    for idx in range(tab.compare_scenario.count()):
        if tab.compare_scenario.itemData(idx) == candidate.id:
            tab.compare_scenario.setCurrentIndex(idx)
            break
    tab._compare_selected_scenario()

    assert tab.comparison_table.rowCount() == 6
    assert tab.comparison_table.item(0, 1).text() == "1"
    assert tab.comparison_table.item(0, 2).text() == "2"
    assert tab.comparison_table.item(2, 3).text() == "+530.00"
    assert "UI Candidate vs UI Baseline" in tab.comparison_summary.text()
    assert "UI Portfolio Beta" in tab.comparison_summary.text()


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
