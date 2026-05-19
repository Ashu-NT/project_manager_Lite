from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.modules.project_management.domain.enums import DependencyType
from tests.ui_runtime_helpers import login_as


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
    auth_session_repo = getattr(auth, "_auth_session_repo", None)
    assert auth_session_repo is not None
    assert authenticated.active_session_id is not None
    auth_session = auth_session_repo.get(authenticated.active_session_id)
    assert auth_session is not None
    auth_session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    auth_session.updated_at = datetime.now(timezone.utc)
    auth_session_repo.update(auth_session)
    services["session"].commit()
    user_session.set_principal(auth.build_principal(authenticated, session_id=auth_session.id))

    assert user_session.is_authenticated() is False
    assert user_session.principal is None


def test_security_admin_can_revoke_live_user_sessions(services):
    auth = services["auth_service"]
    auth.register_user("revoked-user", "StrongPass123", role_names=["viewer"])

    stale_session = UserSessionContext(principal_validator=auth.validate_session_principal)
    stale_session.set_principal(auth.build_principal(auth.authenticate("revoked-user", "StrongPass123")))

    auth.revoke_user_sessions(
        next(row for row in auth.list_users() if row.username == "revoked-user").id,
        note="Offboarding test",
    )

    assert stale_session.is_authenticated() is False
    assert stale_session.principal is None


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


def test_portfolio_scoring_templates_drive_new_intake_scores(services):
    portfolio = services["portfolio_service"]

    default_template = portfolio.get_active_scoring_template()
    assert default_template.name == "Balanced PMO"

    template = portfolio.create_scoring_template(
        name="Value First",
        summary="Pushes business value above urgency.",
        strategic_weight=1,
        value_weight=5,
        urgency_weight=1,
        risk_weight=0,
        activate=True,
    )

    active_template = portfolio.get_active_scoring_template()
    assert active_template.id == template.id
    assert active_template.is_active is True

    intake = portfolio.create_intake_item(
        title="Template Driven Intake",
        sponsor_name="PMO",
        strategic_score=2,
        value_score=5,
        urgency_score=1,
        risk_score=4,
    )

    assert intake.scoring_template_id == template.id
    assert intake.scoring_template_name == "Value First"
    assert intake.composite_score == 28


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


def test_portfolio_executive_views_roll_up_heatmap_and_recent_pm_actions(services):
    project_service = services["project_service"]
    portfolio = services["portfolio_service"]
    resource_service = services["resource_service"]
    task_service = services["task_service"]
    timesheet_service = services["timesheet_service"]

    project = project_service.create_project("Executive Pressure Project", planned_budget=200.0)
    resource = resource_service.create_resource("Executive Analyst", hourly_rate=100.0, capacity_percent=80.0)
    task = task_service.create_task(
        project.id,
        "Late Executive Task",
        start_date=date(2026, 6, 1),
        duration_days=2,
    )
    assignment = task_service.assign_resource(task.id, resource.id, 100.0)
    timesheet_service.add_time_entry(
        assignment.id,
        entry_date=date(2026, 6, 2),
        hours=6.0,
        note="Delivery work",
    )
    timesheet_service.submit_timesheet_period(
        resource.id,
        period_start=date(2026, 6, 1),
        note="Executive review",
    )

    heatmap = portfolio.list_portfolio_heatmap()
    recent_actions = portfolio.list_recent_pm_actions(limit=10)

    assert len(heatmap) == 1
    assert heatmap[0].project_name == "Executive Pressure Project"
    assert heatmap[0].pressure_label in {"Watch", "Hot"}
    assert heatmap[0].peak_utilization_percent >= 100.0

    assert any("Timesheet Period Submit" == item.action_label for item in recent_actions)
    assert any(item.project_name == "Executive Pressure Project" for item in recent_actions)


def test_portfolio_project_dependencies_track_cross_project_links(services):
    project_service = services["project_service"]
    portfolio = services["portfolio_service"]

    predecessor = project_service.create_project("Dependency Program Alpha")
    successor = project_service.create_project("Dependency Program Beta")

    dependency = portfolio.create_project_dependency(
        predecessor_project_id=predecessor.id,
        successor_project_id=successor.id,
        dependency_type=DependencyType.FINISH_TO_START,
        summary="Beta depends on Alpha handover.",
    )

    rows = portfolio.list_project_dependencies()

    assert len(rows) == 1
    assert rows[0].dependency_id == dependency.id
    assert rows[0].predecessor_project_name == "Dependency Program Alpha"
    assert rows[0].successor_project_name == "Dependency Program Beta"
    assert rows[0].dependency_type == DependencyType.FINISH_TO_START
    assert rows[0].summary == "Beta depends on Alpha handover."
    assert rows[0].pressure_label in {"Stable", "Watch", "Hot", "Needs Schedule"}

    portfolio.remove_project_dependency(dependency.id)
    assert portfolio.list_project_dependencies() == []
