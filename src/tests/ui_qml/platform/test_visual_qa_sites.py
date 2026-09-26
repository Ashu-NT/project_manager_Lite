"""Site closeout visual QA: scene-graph offscreen capture of the Sites
master-data reference page (list + Inspector + Detail, all tabs, sparse and
fully-populated records, inherited vs. overridden calendar) at multiple
breakpoints and themes -- the same technique already used for Organization
(see test_visual_qa_organizations.py)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtQuick import QQuickItem

from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.time_management.calendar.models.enterprise_calendar import (
    SiteCalendarAssignCommand,
)
from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)
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
    "1600x1000": (1600, 1000),
    "1366x768": (1366, 768),
    "narrow1000": (1000, 800),
}

_RELEVANT_ERROR_MARKERS = (
    "ReferenceError",
    "TypeError",
    "unknown icon name",
    "is not defined",
    "Cannot read prop",
    "Cannot assign to non-existent property",
    "unavailable",
)


def _settle(app, *, seconds: float = 2.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)


def _grab(app, item, path: Path) -> bool:
    grab_result = item.grabToImage()
    state: dict[str, object] = {}

    def _on_ready():
        state["done"] = grab_result.saveToFile(str(path))

    grab_result.ready.connect(_on_ready)
    deadline = time.time() + 10
    while "done" not in state and time.time() < deadline:
        app.processEvents()
    return bool(state.get("done", False))


def _seed_sites(services, *, count: int, prefix: str) -> None:
    site_service = services["site_service"]
    for i in range(count):
        site_service.create_site(site_code=f"{prefix}{i:03d}", name=f"{prefix} Site {i:03d}")


def _seed_mixed_lifecycle_sites(services, *, prefix: str) -> None:
    site_service = services["site_service"]
    active = site_service.create_site(site_code=f"{prefix}-ACT", name=f"{prefix} Active Site")
    inactive = site_service.create_site(site_code=f"{prefix}-INA", name=f"{prefix} Inactive Site")
    archived = site_service.create_site(site_code=f"{prefix}-ARC", name=f"{prefix} Archived Site")
    site_service.deactivate_site(inactive.id)
    site_service.deactivate_site(archived.id)
    site_service.archive_site(archived.id)


def _seed_sparse_site(services, *, code: str, name: str) -> str:
    """A site with no address, no departments, no employees, no calendar
    override -- exercises every blank-value convention and empty state."""
    site = services["site_service"].create_site(site_code=code, name=name)
    return site.id


def _seed_full_site(services, *, code: str, name: str) -> tuple[str, str]:
    """A site with real address fields, a department, an employee, and its
    own calendar override -- exercises populated Overview cards, real Key
    Statistics counts, and the "Site override" calendar state."""
    site_service = services["site_service"]
    site = site_service.create_site(
        site_code=code,
        name=name,
        description="Full VQA site",
        city="Douala",
        country="Cameroon",
        region="Littoral",
        address_line_1="12 Rue de la Paix",
        address_line_2="Building B",
        postal_code="00237",
        timezone_name="Africa/Douala",
        currency_code="XAF",
        site_type="Plant",
    )
    services["department_service"].create_department(
        department_code=f"{code}-DEPT-1", name="VQA Department One", site_id=site.id
    )
    services["employee_service"].create_employee(
        employee_code=f"{code}-EMP-1", full_name="VQA Employee One", site_id=site.id
    )

    registry = build_desktop_api_registry(services)
    calendars_result = registry.platform_enterprise_calendar.list_calendars()
    assert calendars_result.ok and calendars_result.data, "expected the seeded default calendar"
    calendar_id = calendars_result.data[0].id
    assign_result = registry.platform_enterprise_calendar.assign_site_calendar(
        SiteCalendarAssignCommand(site_id=site.id, calendar_id=calendar_id)
    )
    assert assign_result.ok, assign_result.error

    return site.id, calendar_id


@pytest.mark.parametrize("theme_mode", ["light", "dark"])
def test_capture_sites_list_screenshots(qapp, services, theme_mode) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    try:
        _seed_sites(services, count=30, prefix="VQASITE")
        _seed_mixed_lifecycle_sites(services, prefix="VQALIFE")

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
        platform_catalog.selectDestination("sites")
        _settle(qapp)

        for size_name, (w, h) in SIZES.items():
            root.resize(w, h)
            _settle(qapp)
            item = root.findChild(QQuickItem, "mainWindow")
            assert item is not None
            saved = _grab(qapp, item, OUT_DIR / f"sites_page1_{theme_mode}_{size_name}.png")
            assert saved

        # Mixed-status rows -- Active/Inactive/Archived StatusChip tones
        # side by side.
        platform_catalog.adminWorkspace.setSiteSearchText("VQALIFE")
        _settle(qapp)
        root.resize(1600, 1000)
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"sites_mixedstatus_{theme_mode}_1600x1000.png")
        assert saved

        # Inspector open on the mixed-status set (Actions ▾ hierarchy).
        sites_page = root.findChild(QQuickItem, "sitesWorkspacePage")
        assert sites_page is not None
        catalog = platform_catalog.adminWorkspace.sites
        active_row = next(row for row in catalog["items"] if "Active Site" in row["title"])
        sites_page.setProperty("selectedRowId", active_row["id"])
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"sites_inspector_active_{theme_mode}_1600x1000.png")
        assert saved

        archived_row = next(row for row in catalog["items"] if "Archived Site" in row["title"])
        sites_page.setProperty("selectedRowId", archived_row["id"])
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"sites_inspector_archived_{theme_mode}_1600x1000.png")
        assert saved

        platform_catalog.adminWorkspace.setSiteSearchText("")

        # Search with no matches -> "no results" empty state.
        platform_catalog.adminWorkspace.setSiteSearchText("DOES-NOT-EXIST-ANYWHERE")
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"sites_noresults_{theme_mode}_1600x1000.png")
        assert saved
        platform_catalog.adminWorkspace.setSiteSearchText("")

        relevant = [m for m in messages if any(marker in m for marker in _RELEVANT_ERROR_MARKERS)]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)


def _open_site_detail(services, api_registry, *, site_id: str):
    """One fresh shell/engine per capture -- deliberately never reuses one
    Loader-backed detail page across two different rows in the same engine.
    Toggling active(false)->active(true) on a different row races the
    Loader's async item teardown/recreation under this harness's manually-
    pumped event loop (confirmed to affect the already-accepted Organization
    Detail equally, not something specific to Site -- see the Site closeout
    investigation), so each row gets its own engine instead."""
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
    root.resize(1600, 1000)
    shell_context.selectRoute("platform.workspace")
    platform_catalog.selectDestination("sites")
    # Return every object whose C++ side must outlive this function --
    # letting `engine`/`shell_context`/the catalogs fall out of scope here
    # gets them garbage-collected (and their QQuickWindow deleted) before
    # the caller can use `root`.
    return root, platform_catalog, engine, shell_context, pm_catalog


def _tabs_for(detail_page) -> dict[int, str]:
    """Section index -> name, read from the real _sections array rather
    than hardcoded -- Projects is only inserted (at index 3, shifting
    Calendar/Documents/Activity by one) when project_management is
    enabled, so a fixed index map silently mislabels captures depending on
    which modules are on."""
    raw = detail_page.property("_sections")
    sections = raw.toVariant() if hasattr(raw, "toVariant") else (raw or [])
    return {i: str(s.get("label", "")).lower() for i, s in enumerate(sections)}


def test_capture_site_detail_sparse_screenshots(qapp, services) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    try:
        sparse_id = _seed_sparse_site(services, code="VQASPARSE", name="VQA Sparse Site")
        api_registry = build_desktop_api_registry(services)
        root, _platform_catalog, _engine, _shell_context, _pm_catalog = _open_site_detail(services, api_registry, site_id=sparse_id)
        _settle(qapp, seconds=4.0)

        sites_page = root.findChild(QQuickItem, "sitesWorkspacePage")
        assert sites_page is not None
        sites_page.setProperty("selectedRowId", sparse_id)
        sites_page.setProperty("detailOpen", True)
        _settle(qapp, seconds=3.0)
        detail_page = root.findChild(QQuickItem, "adminSiteDetailPage")
        assert detail_page is not None
        assert detail_page.property("_siteId") == sparse_id

        # Regression guard: Key Statistics/tab-count must be THIS site's own
        # count (filteredTotal), never the whole-organization total
        # (totalCount) -- a sparse site sitting in the same organization as
        # another, fully-populated site must show zero, not leak the other
        # site's department/employee counts into its own Overview.
        assert detail_page.property("_departmentCount") == 0
        assert detail_page.property("_employeeCount") == 0

        for index, name in _tabs_for(detail_page).items():
            detail_page.setProperty("activeSectionIndex", index)
            _settle(qapp)
            mainWindow = root.findChild(QQuickItem, "mainWindow")
            saved = _grab(qapp, mainWindow, OUT_DIR / f"site_detail_sparse_{name}_light_1600x1000.png")
            assert saved

        relevant = [m for m in messages if any(marker in m for marker in _RELEVANT_ERROR_MARKERS)]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)


def test_capture_site_detail_full_screenshots(qapp, services) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    try:
        full_id, _calendar_id = _seed_full_site(services, code="VQAFULL", name="VQA Full Site")
        api_registry = build_desktop_api_registry(services)
        root, _platform_catalog, _engine, _shell_context, _pm_catalog = _open_site_detail(services, api_registry, site_id=full_id)
        _settle(qapp, seconds=4.0)

        sites_page = root.findChild(QQuickItem, "sitesWorkspacePage")
        assert sites_page is not None
        sites_page.setProperty("selectedRowId", full_id)
        sites_page.setProperty("detailOpen", True)
        _settle(qapp, seconds=3.0)
        detail_page = root.findChild(QQuickItem, "adminSiteDetailPage")
        assert detail_page is not None
        assert detail_page.property("_siteId") == full_id
        assert detail_page.property("_departmentCount") == 1
        assert detail_page.property("_employeeCount") == 1

        for index, name in _tabs_for(detail_page).items():
            detail_page.setProperty("activeSectionIndex", index)
            _settle(qapp)
            mainWindow = root.findChild(QQuickItem, "mainWindow")
            saved = _grab(qapp, mainWindow, OUT_DIR / f"site_detail_full_{name}_light_1600x1000.png")
            assert saved

        # Narrow-width Overview (responsive stacking check).
        detail_page.setProperty("activeSectionIndex", 0)
        root.resize(1000, 800)
        _settle(qapp)
        mainWindow = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, mainWindow, OUT_DIR / "site_detail_full_overview_light_narrow1000.png")
        assert saved

        relevant = [m for m in messages if any(marker in m for marker in _RELEVANT_ERROR_MARKERS)]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)
