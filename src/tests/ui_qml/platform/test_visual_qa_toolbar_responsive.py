"""Runtime visual verification for the shared TableToolbar responsive fix,
against the real Organization/Site Employees (and Site Departments) tabs --
not just the isolated shared-component probe in
test_table_toolbar_responsive.py. A synthetic probe missed a real regression
here once already (the toolbar's row-reparenting only ran once, at initial
load, so a later resize repositioned controls using the new row's math while
they were still attached to the old row -- correct x values, wrong parent,
invisible in an x-only bounds check but visible immediately as an overlapping
render): scene-graph offscreen capture plus direct geometry assertions on the
real detail pages catch that class of bug that a bounds-only check does not."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtQuick import QQuickItem

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.context import build_shell_context
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml
from src.ui_qml.shell.qml_registry import build_qml_route_registry

OUT_DIR = Path(
    os.environ.get(
        "VISUAL_QA_OUT_DIR",
        r"C:\Users\ashu\AppData\Local\Temp\claude\C--Users-ashu-Desktop-PersonalProjects-project-manager-Lite\780b7419-8bb7-4db7-93f0-f562a53886ee\scratchpad\visual_qa",
    )
)

SIZES = {
    "wide": (1600, 1000),
    "constrained": (1000, 800),
    # Detail pages lose a large, fixed amount of width to the platform
    # sidebar + SectionNavigationRail before the toolbar ever sees it (see
    # TableToolbar.qml's responsive-breakpoint comment). Below roughly this
    # window width, the rail's own narrow-width behavior (a separately
    # tracked, pre-existing issue) starts to dominate what content width
    # the toolbar receives, which is not what this test is verifying.
    "narrow": (900, 700),
}

_RELEVANT_ERROR_MARKERS = ("TypeError", "ReferenceError", "Binding loop", "Cannot read prop")


def _settle(app, seconds: float = 1.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)


def _grab(app, item, path: Path) -> bool:
    grab_result = item.grabToImage()
    state = {}

    def _on_ready():
        state["done"] = grab_result.saveToFile(str(path))

    grab_result.ready.connect(_on_ready)
    deadline = time.time() + 10
    while "done" not in state and time.time() < deadline:
        app.processEvents()
    return state.get("done", False)


def _new_shell(api_registry):
    registry = build_qml_route_registry()
    shell_context = build_shell_context(build_main_window_navigation(registry))
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=api_registry)
    platform_catalog = PlatformWorkspaceCatalog(desktop_api_registry=api_registry)

    engine = create_qml_engine()
    shell_route = registry.get("shell.app")
    load_qml(
        engine,
        shell_route.qml_path,
        initial_properties={
            "shellModel": shell_context,
            "platformCatalog": platform_catalog,
            "pmCatalog": pm_catalog,
        },
    )
    root = engine.rootObjects()[0]
    return root, platform_catalog, engine, shell_context, pm_catalog


def _find_active_toolbar(detail_page):
    """Multiple TableToolbar instances coexist (LazySectionLoader
    keepLoaded) -- scope the search to the currently-visible one."""
    for candidate in detail_page.findChildren(QQuickItem, "toolbarTopRow"):
        if candidate.isVisible():
            return candidate.parentItem().parentItem()
    return None


# Command/table controls (row 2) must never clip -- that is the bug this
# fix targets. Query controls (row 1: search + caller-supplied
# filterContent) are checked leniently: filter content is opaque/caller-
# owned with no shared shrink API, so several wide filters plus a very
# narrow window can still run slightly past the row's own edge -- a
# distinct, lower-severity concern than actions vanishing.
_COMMAND_CONTROLS = (
    "toolbarCustomizeButton", "toolbarViewsButton", "toolbarRefreshButton",
    "toolbarImportButton", "toolbarExportButton", "toolbarOverflowButton",
    "toolbarCreateButton",
)
_QUERY_CONTROLS = ("toolbarSearchField", "toolbarFilterSlot", "toolbarFilterButton")


def _assert_controls_reachable(toolbar_root, label):
    """Every action a caller wired up must be reachable: visible and, for
    command/table controls, fully within the toolbar's own bounds.
    Positions are checked in the toolbar's own coordinate space
    (mapToItem), which also catches a control still parented to the wrong
    row after a tier switch even though its x looks fine in isolation."""
    width = toolbar_root.width()
    checked = 0
    for name in _COMMAND_CONTROLS:
        item = toolbar_root.findChild(QQuickItem, name)
        if item is None or not item.property("visible"):
            continue
        checked += 1
        top_left = item.mapToItem(toolbar_root, 0, 0)
        bottom_right = item.mapToItem(toolbar_root, item.width(), item.height())
        assert top_left.x() >= -0.5, f"{label}: {name} starts left of toolbar (x={top_left.x()})"
        assert bottom_right.x() <= width + 0.5, (
            f"{label}: {name} right edge ({bottom_right.x()}) exceeds toolbar width ({width})"
        )
        assert item.width() > 0 and item.height() > 0, f"{label}: {name} has zero size"

    for name in _QUERY_CONTROLS:
        item = toolbar_root.findChild(QQuickItem, name)
        if item is None or not item.property("visible"):
            continue
        checked += 1
        top_left = item.mapToItem(toolbar_root, 0, 0)
        assert top_left.x() >= -0.5, f"{label}: {name} starts left of toolbar (x={top_left.x()})"
        assert item.width() > 0 and item.height() > 0, f"{label}: {name} has zero size"

    assert checked > 0, f"{label}: no toolbar controls found"

    # The primary create action, if present, must never be the one folded
    # into overflow -- it stays directly visible at every tier.
    create = toolbar_root.findChild(QQuickItem, "toolbarCreateButton")
    if create is not None and toolbar_root.property("showCreate"):
        assert create.property("visible") is True, f"{label}: primary create action is not visible"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_organization_employees_toolbar_responsive(qapp, services, theme) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    try:
        organization_service = services["organization_service"]
        org = organization_service.create_organization(
            organization_code=f"VQATB-ORG-{theme}", display_name="VQA Toolbar Org", timezone_name="UTC", base_currency="USD"
        )
        services["tenant_context_service"].set_active_organization(org.id)
        department = services["department_service"].create_department(
            department_code=f"VQATB-OD1-{theme}", name="VQA Toolbar Org Dept"
        )
        services["employee_service"].create_employee(
            employee_code="VQATB-OE1", full_name="VQA Toolbar Org Employee", department_id=department.id
        )

        api_registry = build_desktop_api_registry(services)
        root, platform_catalog, engine, shell_context, pm_catalog = _new_shell(api_registry)
        if theme == "dark":
            shell_context.setThemeMode("dark")
        root.resize(1600, 1000)
        shell_context.selectRoute("platform.workspace")
        platform_catalog.selectDestination("organizations")
        _settle(qapp, 2.0)

        orgs_page = None
        for _ in range(20):
            orgs_page = root.findChild(QQuickItem, "organizationsWorkspacePage")
            if orgs_page is not None:
                break
            _settle(qapp, 0.5)
        orgs_page.setProperty("selectedRowId", org.id)
        orgs_page.setProperty("detailOpen", True)
        _settle(qapp, 2.0)

        detail_page = root.findChild(QQuickItem, "adminOrganizationDetailPage")
        sections = detail_page.property("_sections")
        sections = sections.toVariant() if hasattr(sections, "toVariant") else sections
        employees_index = next(i for i, s in enumerate(sections) if s["label"] == "Employees")
        detail_page.setProperty("activeSectionIndex", employees_index)
        _settle(qapp, 1.0)

        for size_name, (w, h) in SIZES.items():
            root.resize(w, h)
            _settle(qapp, 1.0)
            toolbar_root = _find_active_toolbar(detail_page)
            assert toolbar_root is not None, f"org employees {size_name}: toolbar not found"
            _assert_controls_reachable(toolbar_root, f"org employees {size_name}")
            item = root.findChild(QQuickItem, "mainWindow")
            saved = _grab(qapp, item, OUT_DIR / f"toolbar_org_employees_{theme}_{size_name}.png")
            assert saved

        relevant = [m for m in messages if any(marker in m for marker in _RELEVANT_ERROR_MARKERS)]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_site_employees_and_departments_toolbar_responsive(qapp, services, theme) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    try:
        site_service = services["site_service"]
        site = site_service.create_site(site_code=f"VQATB-SITE-{theme}", name="VQA Toolbar Site")
        department = services["department_service"].create_department(
            department_code=f"VQATB-D1-{theme}", name="VQA Toolbar Dept", site_id=site.id
        )
        services["employee_service"].create_employee(
            employee_code="VQATB-E1", full_name="VQA Toolbar Site Employee", site_id=site.id, department_id=department.id
        )

        api_registry = build_desktop_api_registry(services)
        root, platform_catalog, engine, shell_context, pm_catalog = _new_shell(api_registry)
        if theme == "dark":
            shell_context.setThemeMode("dark")
        root.resize(1600, 1000)
        shell_context.selectRoute("platform.workspace")
        platform_catalog.selectDestination("sites")
        _settle(qapp, 2.0)

        sites_page = None
        for _ in range(20):
            sites_page = root.findChild(QQuickItem, "sitesWorkspacePage")
            if sites_page is not None:
                break
            _settle(qapp, 0.5)
        sites_page.setProperty("selectedRowId", site.id)
        sites_page.setProperty("detailOpen", True)
        _settle(qapp, 2.0)

        detail_page = root.findChild(QQuickItem, "adminSiteDetailPage")
        sections = detail_page.property("_sections")
        sections = sections.toVariant() if hasattr(sections, "toVariant") else sections
        employees_index = next(i for i, s in enumerate(sections) if s["label"] == "Employees")
        departments_index = next(i for i, s in enumerate(sections) if s["label"] == "Departments")

        detail_page.setProperty("activeSectionIndex", employees_index)
        _settle(qapp, 1.0)
        for size_name, (w, h) in SIZES.items():
            root.resize(w, h)
            _settle(qapp, 1.0)
            toolbar_root = _find_active_toolbar(detail_page)
            assert toolbar_root is not None, f"site employees {size_name}: toolbar not found"
            _assert_controls_reachable(toolbar_root, f"site employees {size_name}")
            item = root.findChild(QQuickItem, "mainWindow")
            saved = _grab(qapp, item, OUT_DIR / f"toolbar_site_employees_{theme}_{size_name}.png")
            assert saved

        detail_page.setProperty("activeSectionIndex", departments_index)
        root.resize(*SIZES["constrained"])
        _settle(qapp, 1.0)
        toolbar_root = _find_active_toolbar(detail_page)
        assert toolbar_root is not None, "site departments constrained: toolbar not found"
        _assert_controls_reachable(toolbar_root, "site departments constrained")
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"toolbar_site_departments_{theme}_constrained.png")
        assert saved

        relevant = [m for m in messages if any(marker in m for marker in _RELEVANT_ERROR_MARKERS)]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)
