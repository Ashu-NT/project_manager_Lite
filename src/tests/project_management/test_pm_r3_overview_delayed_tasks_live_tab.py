"""R3 -- Overview Scalable Queries: proves the Delayed Tasks operational tab
is genuinely server-paginated end-to-end through the real Dashboard route
QML load and controller, not just at the desktop-API layer."""

from __future__ import annotations

import os
from datetime import date, timedelta

from PySide6.QtGui import QGuiApplication

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-r3-overview-delayed-tasks-test"])


def _seed_project_with_overdue_tasks(services, count: int):
    today = date.today()
    project = services["project_service"].create_project(
        "Overview Live Tab Project",
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=60),
        financial_currency_code="EUR",
    )
    rows = [
        TaskORM(
            id=f"live-task-{index:04d}",
            project_id=project.id,
            wbs_code=f"live-task-{index:04d}",
            sort_order=index,
            name=f"Live Overdue Task {index:04d}",
            status=TaskStatus.IN_PROGRESS,
            end_date=today - timedelta(days=5),
            deadline=today - timedelta(days=5),
            version=1,
        )
        for index in range(count)
    ]
    services["session"].add_all(rows)
    services["session"].flush()
    return project


def test_delayed_tasks_tab_is_server_paginated_through_real_controller(services) -> None:
    project = _seed_project_with_overdue_tasks(services, 15)
    _ensure_qgui_application()
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()
    routes = {route.route_id: route for route in build_project_management_routes()}

    engine = create_qml_engine()
    engine.setInitialProperties({"pmCatalog": pm_catalog, "platformCatalog": platform_catalog})
    engine.load(str(routes["project_management.dashboard"].qml_path))
    assert len(engine.rootObjects()) == 1

    controller = pm_catalog.dashboardWorkspace
    controller.selectProject(project.id)
    controller.selectOperationalTab("delayed_tasks")

    assert controller.operationalTotalCount == 15
    assert controller.operationalTable["totalCount"] == 15

    controller.setOperationalPageSize(5)
    assert controller.operationalTotalCount == 15
    assert len(controller.operationalTable["rows"]) == 5

    controller.setOperationalPage(3)
    assert controller.operationalPage == 3
    assert len(controller.operationalTable["rows"]) == 5

    controller.setOperationalSearchText("Live Overdue Task 0001")
    assert controller.operationalTotalCount == 1
