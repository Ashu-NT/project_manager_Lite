"""R4.2 Projects redesign: catalog -> inspector -> full detail, plus the
explicit Set/Clear Active Project action -- neither existed before this
phase (confirmed via R4.1 characterization: no inspector step, no active-
project affordance anywhere in Projects). Real QML-engine load, real
created project, no mocks."""

from __future__ import annotations

import os
from datetime import date, timedelta

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QJSValue


def _to_py(value):
    return value.toVariant() if isinstance(value, QJSValue) else value

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.routes import project_management_qml_path
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine


def _ensure_qgui_application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    return QGuiApplication(["pm-r4-2-projects-inspector-test"])


def _load_projects_page(pm_catalog, platform_catalog):
    engine = create_qml_engine()
    engine.setInitialProperties(
        {"pmCatalog": pm_catalog, "platformCatalog": platform_catalog}
    )
    path = project_management_qml_path("workspaces", "projects", "ProjectsWorkspacePage.qml")
    engine.load(str(path))
    assert len(engine.rootObjects()) == 1
    return engine, engine.rootObjects()[0]


def test_selecting_a_row_opens_inspector_without_opening_full_detail(services) -> None:
    today = date.today()
    project = services["project_service"].create_project(
        "R4.2 Inspector Project",
        start_date=today - timedelta(days=10),
        end_date=today + timedelta(days=80),
        financial_currency_code="EUR",
    )

    _ensure_qgui_application()
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()
    engine, root = _load_projects_page(pm_catalog, platform_catalog)

    controller = pm_catalog.projectsWorkspace
    controller.selectProject(project.id)

    inspector_item = root.property("_inspectorItem")
    assert inspector_item is not None
    assert str(inspector_item["id"]) == project.id
    assert str(inspector_item["title"]) == "R4.2 Inspector Project"

    # Select != activate: single selection must not open the full detail
    # page (matches the global project-context rule -- browsing/selecting
    # is not the same as a heavier/committing action).
    assert bool(root.property("_detailOpen")) is False

    sections = _to_py(root.property("_inspectorSections"))
    assert isinstance(sections, list)
    assert len(sections) > 0


def test_inspector_set_and_clear_active_project(services) -> None:
    today = date.today()
    project = services["project_service"].create_project(
        "R4.2 Active Project Toggle",
        start_date=today - timedelta(days=5),
        end_date=today + timedelta(days=60),
        financial_currency_code="EUR",
    )

    _ensure_qgui_application()
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()
    engine, root = _load_projects_page(pm_catalog, platform_catalog)

    controller = pm_catalog.projectsWorkspace
    controller.selectProject(project.id)

    assert bool(root.property("_inspectorIsActiveProject")) is False

    pm_project_context = pm_catalog.pmProjectContext
    pm_project_context.selectProject(project.id)

    assert pm_project_context.activeProjectId == project.id
    assert bool(root.property("_inspectorIsActiveProject")) is True

    pm_project_context.clearProject()

    assert pm_project_context.hasActiveProject is False
    assert bool(root.property("_inspectorIsActiveProject")) is False


def test_row_activation_still_opens_full_detail(services) -> None:
    today = date.today()
    project = services["project_service"].create_project(
        "R4.2 Full Detail Project",
        start_date=today - timedelta(days=3),
        end_date=today + timedelta(days=90),
        financial_currency_code="EUR",
    )

    _ensure_qgui_application()
    registry = build_desktop_api_registry(services)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    platform_catalog = PlatformWorkspaceCatalog()
    engine, root = _load_projects_page(pm_catalog, platform_catalog)

    controller = pm_catalog.projectsWorkspace
    controller.activateProject(project.id)
    root._openDetail(0)

    assert bool(root.property("_detailOpen")) is True
    assert controller.selectedProject["id"] == project.id
