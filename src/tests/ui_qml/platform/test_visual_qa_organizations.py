"""Phase J visual QA: scene-graph offscreen capture of the Organizations
master-data reference page (few-records state as seeded by the shared test
fixture, and a larger seeded dataset exercising the second page / fixed
pagination footer) at multiple breakpoints and themes."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
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
        r"C:\Users\ashu\AppData\Local\Temp\claude\C--Users-ashu-Desktop-PersonalProjects-project-manager-Lite\56b4eb6f-df78-4d92-8f14-a6dc0a538ab0\scratchpad\visual_qa",
    )
)

SIZES = {
    "1600x1000": (1600, 1000),
    "1366x768": (1366, 768),
    "narrow1000": (1000, 800),
}


def _settle(app, *, seconds: float = 2.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)


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


def _seed_organizations(services, *, count: int, prefix: str) -> None:
    organization_service = services["organization_service"]
    for i in range(count):
        organization_service.create_organization(
            organization_code=f"{prefix}{i:03d}", display_name=f"{prefix} Org {i:03d}"
        )


def _seed_mixed_lifecycle_organizations(services, *, prefix: str) -> None:
    """One of each status -- for a screenshot that actually shows the
    Active/Inactive/Archived StatusChip tones side by side, and for the
    status-filtered captures below."""
    organization_service = services["organization_service"]
    active = organization_service.create_organization(organization_code=f"{prefix}-ACT", display_name=f"{prefix} Active Org")
    inactive = organization_service.create_organization(organization_code=f"{prefix}-INA", display_name=f"{prefix} Inactive Org")
    archived = organization_service.create_organization(organization_code=f"{prefix}-ARC", display_name=f"{prefix} Archived Org")
    organization_service.deactivate_organization(inactive.id)
    organization_service.archive_organization(archived.id)


@pytest.mark.parametrize("theme_mode", ["light", "dark"])
def test_capture_organizations_screenshots(qapp, services, theme_mode) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    try:
        _seed_organizations(services, count=30, prefix="VQAORG")
        _seed_mixed_lifecycle_organizations(services, prefix="VQALIFE")

        registry = build_qml_route_registry()
        shell_context = build_shell_context(build_main_window_navigation(registry))
        if theme_mode == "dark":
            shell_context.setThemeMode("dark")

        api_registry = build_desktop_api_registry(services)
        platform_catalog = PlatformWorkspaceCatalog(desktop_api_registry=api_registry)
        pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=api_registry)

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
        shell_context.selectRoute("platform.workspace")
        platform_catalog.selectDestination("organizations")

        for size_name, (w, h) in SIZES.items():
            root.resize(w, h)
            _settle(qapp)

            item = root.findChild(QQuickItem, "mainWindow")
            assert item is not None

            saved = _grab(qapp, item, OUT_DIR / f"organizations_page1_{theme_mode}_{size_name}.png")
            assert saved

        # Page 2 (30 seeded + any pre-existing -> definitely a second page
        # at the default page size of 25).
        platform_catalog.adminWorkspace.setOrganizationPage(2)
        _settle(qapp)
        root.resize(1600, 1000)
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"organizations_page2_{theme_mode}_1600x1000.png")
        assert saved

        # Search with no matches -> "no results" empty state.
        platform_catalog.adminWorkspace.setOrganizationSearchText("DOES-NOT-EXIST-ANYWHERE")
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"organizations_noresults_{theme_mode}_1600x1000.png")
        assert saved
        platform_catalog.adminWorkspace.setOrganizationSearchText("")

        # Mixed-status rows -- Active/Inactive/Archived StatusChip tones
        # side by side (search narrowed to the seeded lifecycle trio so
        # they land on the same page regardless of page size/sort).
        platform_catalog.adminWorkspace.setOrganizationSearchText("VQALIFE")
        platform_catalog.adminWorkspace.setOrganizationPage(1)
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"organizations_mixedstatus_{theme_mode}_1600x1000.png")
        assert saved

        # Status filter applied server-side (Archived only).
        platform_catalog.adminWorkspace.setOrganizationStatusFilter("archived")
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"organizations_filtered_archived_{theme_mode}_1600x1000.png")
        assert saved
        platform_catalog.adminWorkspace.setOrganizationStatusFilter("")
        platform_catalog.adminWorkspace.setOrganizationSearchText("")

        relevant = [
            m for m in messages
            if "ReferenceError" in m or "TypeError" in m or "unknown icon name" in m
            or "is not defined" in m or "Cannot read prop" in m
        ]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)

# NOTE (Sites vertical slice): a pixel-level screenshot of the Organization
# Detail Sites tab specifically was attempted here and removed --
# grabToImage() requires a QQuickWindow-backed root, which a standalone
# AdminOrganizationDetailPage.qml load (no shell window ancestor) does not
# have. The existing capture above only works because it grabs a named
# child ("mainWindow") from within the full shell scene. Reaching the Sites
# tab that way needs real shell navigation (open Organizations -> select a
# row -> open detail -> switch tab), which is planned for the combined
# visual QA pass once Departments/Employees/Documents also exist (see the
# Phase K report). The Sites tab is instead verified end-to-end, including
# zero console errors, by test_organization_detail_sites_tab.py.


def _seed_full_organization(services, *, code: str, name: str) -> str:
    """One organization with a real row in each of the four Phase K tabs,
    plus a mixed-lifecycle status so the redesigned grouped Inspector shows
    real Key Statistics counts, not just "0" for everything."""
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    org = organization_service.create_organization(
        organization_code=code,
        display_name=name,
        timezone_name="UTC",
        base_currency="USD",
        legal_name=f"{name} Legal Entity",
        registration_number="REG-VQA-001",
        city="Lagos",
        country_code="NG",
    )
    tenant_context_service.set_active_organization(org.id)
    services["site_service"].create_site(site_code="VQA-SITE-1", name="VQA Site One", city="Lagos", country="Nigeria")
    services["department_service"].create_department(department_code="VQA-DEPT-1", name="VQA Department One")
    services["employee_service"].create_employee(employee_code="VQA-EMP-1", full_name="VQA Employee One")
    services["document_service"].create_document(
        document_code="VQA-DOC-1", title="VQA Document One", storage_uri="C:/docs/vqa.pdf"
    )
    return org.id


def test_capture_organization_detail_combined_screenshots(qapp, services) -> None:
    """Combined visual QA (Phase K step 7): the redesigned grouped Inspector
    plus all four entity tabs (Sites/Departments/Employees/Documents),
    captured from within the real shell -- the only way grabToImage() can
    work, since it needs a QQuickWindow-backed root (see the note above)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    try:
        org_id = _seed_full_organization(services, code="VQACOMBINED", name="VQA Combined Org")

        registry = build_qml_route_registry()
        shell_context = build_shell_context(build_main_window_navigation(registry))

        api_registry = build_desktop_api_registry(services)
        platform_catalog = PlatformWorkspaceCatalog(desktop_api_registry=api_registry)
        pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=api_registry)

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
        root.resize(1600, 1000)
        shell_context.selectRoute("platform.workspace")
        platform_catalog.selectDestination("organizations")
        _settle(qapp, seconds=4.0)

        organizations_page = root.findChild(QQuickItem, "organizationsWorkspacePage")
        assert organizations_page is not None
        organizations_page.setProperty("selectedRowId", org_id)
        _settle(qapp)

        # 1. The redesigned grouped Inspector (Identity/Lifecycle/Location/
        # Key Statistics/Business Context), compact width, Open Details +
        # Edit/Actions hierarchy -- shown while NOT in the nested detail.
        mainWindow = root.findChild(QQuickItem, "mainWindow")
        assert mainWindow is not None
        assert _grab(qapp, mainWindow, OUT_DIR / "organization_inspector_grouped_light_1600x1000.png")

        organizations_page.setProperty("detailOpen", True)
        _settle(qapp)
        detail_page = root.findChild(QQuickItem, "adminOrganizationDetailPage")
        assert detail_page is not None

        tabs = {
            0: "overview",
            1: "sites",
            2: "departments",
            3: "employees",
            4: "documents",
        }
        for index, name in tabs.items():
            detail_page.setProperty("activeSectionIndex", index)
            _settle(qapp)
            mainWindow = root.findChild(QQuickItem, "mainWindow")
            saved = _grab(qapp, mainWindow, OUT_DIR / f"organization_detail_{name}_light_1600x1000.png")
            assert saved

        relevant = [
            m for m in messages
            if "ReferenceError" in m or "TypeError" in m or "unknown icon name" in m
            or "is not defined" in m or "Cannot read prop" in m
        ]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)
