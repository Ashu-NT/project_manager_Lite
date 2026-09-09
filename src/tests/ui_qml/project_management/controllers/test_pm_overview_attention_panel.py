"""Overview visual redesign: the "Attention Required" panel replaces the
cost chart in the delivery-trend pairing (wireframe section 6.1) with a
compact digest of already-real, already-bounded data (Delayed Tasks / High
Risks / Pending Approvals) -- no new backend query, no fabricated content."""

from __future__ import annotations

import os
from datetime import date, timedelta

from PySide6.QtGui import QGuiApplication

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_operational_table_mixin import (
    DashboardOperationalTableMixin,
)
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-overview-attention-test"])


class _Harness(DashboardOperationalTableMixin):
    def __init__(self, raw_operational_tables):
        self._raw_operational_tables = raw_operational_tables


def test_build_attention_items_combines_top_rows_from_each_category() -> None:
    harness = _Harness(
        [
            {
                "id": "delayed_tasks",
                "rows": [
                    {"id": "t1", "taskName": "Finish deck", "owner": "Alex", "statusLabel": "Late", "routeId": "project_management.tasks", "state": {}},
                    {"id": "t2", "taskName": "Pour footing", "owner": "Sam", "statusLabel": "Late", "routeId": "project_management.tasks", "state": {}},
                    {"id": "t3", "taskName": "Third task -- excluded by the top-2 cap", "owner": "Kim", "statusLabel": "Late", "routeId": "", "state": {}},
                ],
            },
            {
                "id": "high_risks",
                "rows": [
                    {"id": "r1", "title": "Permit delay", "owner": "Jo", "severityLabel": "Critical", "statusLabel": "Open", "routeId": "project_management.register", "state": {}},
                ],
            },
            {
                "id": "pending_approvals",
                "rows": [
                    {"id": "a1", "request": "Change order #4", "requestedBy": "Pat", "statusLabel": "Pending", "routeId": "platform.control", "state": {}},
                ],
            },
        ]
    )

    items = harness._build_attention_items()

    assert [item["id"] for item in items] == ["t1", "t2", "r1", "a1"]
    assert items[0]["category"] == "Delayed"
    assert items[0]["title"] == "Finish deck"
    assert items[2]["category"] == "Risk"
    assert items[2]["title"] == "Permit delay"
    assert items[3]["category"] == "Approval"
    assert items[3]["title"] == "Change order #4"


def test_build_attention_items_skips_missing_categories() -> None:
    harness = _Harness([{"id": "high_risks", "rows": [{"id": "r1", "title": "Only risk", "owner": "", "statusLabel": "Open", "routeId": "", "state": {}}]}])

    items = harness._build_attention_items()

    assert len(items) == 1
    assert items[0]["category"] == "Risk"


def test_dashboard_route_exposes_attention_items_property(services) -> None:
    today = date.today()
    project = services["project_service"].create_project(
        "Attention Panel Project",
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=30),
        financial_currency_code="EUR",
    )
    services["session"].add(
        TaskORM(
            id="attention-task-1",
            project_id=project.id,
            wbs_code="attention-task-1",
            sort_order=0,
            name="Overdue attention task",
            status=TaskStatus.IN_PROGRESS,
            end_date=today - timedelta(days=3),
            deadline=today - timedelta(days=3),
            version=1,
        )
    )
    services["session"].flush()

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

    assert isinstance(controller.attentionItems, list)
