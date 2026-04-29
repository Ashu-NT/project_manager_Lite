from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QSizePolicy

from src.src.core.modules.project_management.domain.enums import CostType
from tests.ui_runtime_helpers import make_settings_store
from ui.modules.project_management.project.tab import ProjectTab
from ui.modules.project_management.resource.tab import ResourceTab
from ui.modules.project_management.task.tab import TaskTab


def test_project_tab_filters_work_at_runtime(qapp, services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    reporting = services["reporting_service"]
    importer = services["data_import_service"]

    ps.create_project("Alpha Internal", description="Data migration")
    ps.create_project("Beta External", description="External rollout")

    tab = ProjectTab(
        project_service=ps,
        task_service=ts,
        reporting_service=reporting,
        project_resource_service=prs,
        resource_service=rs,
        data_import_service=importer,
        user_session=services["user_session"],
    )

    assert tab.project_search_filter.placeholderText() == "Name, client, description..."
    assert tab.btn_clear_project_filters.text() == "Clear Filters"
    assert tab.project_scope_badge.text() == "All Statuses"
    assert tab.project_count_badge.text() == "2 visible"
    assert tab.project_access_badge.text() == "Manage Enabled"
    assert tab.model.rowCount() == 2

    tab.project_search_filter.setText("internal")
    assert tab.model.rowCount() == 1
    assert tab.project_count_badge.text() == "1 visible"
    assert tab.model.data(tab.model.index(0, 0)) == "Alpha Internal"


def test_resource_tab_filters_work_at_runtime(qapp, services):
    rs = services["resource_service"]
    rs.create_resource("Alpha Engineer", role="Developer", hourly_rate=100.0, is_active=True)
    rs.create_resource(
        "Beta Vendor",
        role="Vendor",
        hourly_rate=80.0,
        is_active=False,
        cost_type=CostType.MATERIAL,
    )

    tab = ResourceTab(resource_service=rs, user_session=services["user_session"])

    assert tab.resource_search_filter.placeholderText() == "Name, role, category..."
    assert tab.btn_clear_resource_filters.text() == "Clear Filters"
    assert tab.resource_scope_badge.text() == "All Resources"
    assert tab.resource_count_badge.text() == "2 visible"
    assert tab.resource_access_badge.text() == "Manage Enabled"
    assert tab.resource_header_card.sizePolicy().verticalPolicy() == QSizePolicy.Fixed
    assert tab.resource_controls_card.sizePolicy().verticalPolicy() == QSizePolicy.Fixed
    assert tab.layout().stretch(2) == 1
    assert tab.model.rowCount() == 2

    tab.resource_active_filter.setCurrentIndex(tab.resource_active_filter.findData("inactive"))
    assert tab.model.rowCount() == 1
    assert tab.resource_scope_badge.text() == "Inactive"
    assert tab.resource_count_badge.text() == "1 visible"
    assert tab.model.data(tab.model.index(0, 0)) == "Beta Vendor"

    tab.resource_search_filter.setText("vendor")
    assert tab.model.rowCount() == 1


def test_task_tab_filters_work_at_runtime(qapp, services, repo_workspace):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    settings_store = make_settings_store(repo_workspace, prefix="task-filters")

    project = ps.create_project("Task Filter Project")
    ts.create_task(
        project.id,
        "High Priority Task",
        description="Critical path item",
        start_date=date(2026, 4, 1),
        duration_days=2,
        priority=90,
    )
    ts.create_task(
        project.id,
        "Low Priority Task",
        description="Backlog item",
        start_date=date(2026, 4, 2),
        duration_days=2,
        priority=10,
    )

    tab = TaskTab(
        project_service=ps,
        task_service=ts,
        resource_service=rs,
        project_resource_service=prs,
        collaboration_store=services["task_collaboration_store"],
        settings_store=settings_store,
        user_session=services["user_session"],
    )

    assert "advanced:" in tab.task_search_filter.placeholderText()
    assert tab.task_view_combo.count() >= 1
    assert tab.model.rowCount() == 2

    tab.task_search_filter.setText("priority>=70")
    assert tab.model.rowCount() == 1
    assert tab.model.data(tab.model.index(0, 0)) == "High Priority Task"

    tab._mentions_refresh_timer.stop()


