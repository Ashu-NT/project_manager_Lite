"""Department closeout visual QA: scene-graph offscreen capture of the
Departments master-data-specialization page (list + Inspector + Detail, all
tabs, sparse and fully-populated records, inherited vs. overridden calendar)
at multiple breakpoints and themes -- the same technique already used for
Organization/Site (see test_visual_qa_sites.py)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtQuick import QQuickItem

from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.time_management.calendar.models.enterprise_calendar import (
    DeptCalendarAssignCommand,
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


def _seed_departments(services, *, count: int, prefix: str) -> None:
    department_service = services["department_service"]
    for i in range(count):
        department_service.create_department(department_code=f"{prefix}{i:03d}", name=f"{prefix} Department {i:03d}")


def _seed_mixed_lifecycle_departments(services, *, prefix: str) -> None:
    department_service = services["department_service"]
    active = department_service.create_department(department_code=f"{prefix}-ACT", name=f"{prefix} Active Department")
    inactive = department_service.create_department(department_code=f"{prefix}-INA", name=f"{prefix} Inactive Department")
    department_service.deactivate_department(inactive.id)
    return active


def _seed_sparse_department(services, *, code: str, name: str) -> str:
    """A department with no site, no parent, no HOD, no employees, no
    calendar override -- exercises every blank-value convention and empty
    state."""
    department = services["department_service"].create_department(department_code=code, name=name)
    return department.id


def _seed_full_department(services, *, code: str, name: str) -> tuple[str, str]:
    """A department with a real site, parent department, HOD, employee,
    cost center, notes, and its own calendar override -- exercises
    populated Overview cards, real Key Statistics counts, and the
    "Department override" calendar state."""
    site_service = services["site_service"]
    department_service = services["department_service"]
    employee_service = services["employee_service"]

    site = site_service.create_site(site_code=f"{code}-SITE", name="VQA Department Site")
    parent = department_service.create_department(department_code=f"{code}-PARENT", name="VQA Parent Department")
    department = department_service.create_department(
        department_code=code,
        name=name,
        description="Full VQA department",
        site_id=site.id,
        parent_department_id=parent.id,
        department_type="Operations",
        cost_center_code="CC-VQA-01",
        notes="Operational notes for visual QA.",
    )
    employee = employee_service.create_employee(
        employee_code=f"{code}-EMP-1", full_name="VQA Head Employee", site_id=site.id, department_id=department.id
    )
    department_service.update_department(
        department.id, head_of_department_employee_id=employee.id, expected_version=department.version
    )

    registry = build_desktop_api_registry(services)
    calendars_result = registry.platform_enterprise_calendar.list_calendars()
    assert calendars_result.ok and calendars_result.data, "expected the seeded default calendar"
    calendar_id = calendars_result.data[0].id
    assign_result = registry.platform_enterprise_calendar.assign_department_calendar(
        DeptCalendarAssignCommand(department_id=department.id, calendar_id=calendar_id)
    )
    assert assign_result.ok, assign_result.error

    return department.id, calendar_id


@pytest.mark.parametrize("theme_mode", ["light", "dark"])
def test_capture_departments_list_screenshots(qapp, services, theme_mode) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    try:
        _seed_departments(services, count=30, prefix="VQADEPT")
        _seed_mixed_lifecycle_departments(services, prefix="VQALIFE")

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
        platform_catalog.selectDestination("departments")
        _settle(qapp)

        for size_name, (w, h) in SIZES.items():
            root.resize(w, h)
            _settle(qapp)
            item = root.findChild(QQuickItem, "mainWindow")
            assert item is not None
            saved = _grab(qapp, item, OUT_DIR / f"departments_page1_{theme_mode}_{size_name}.png")
            assert saved

        # Mixed-status rows -- Active/Inactive StatusChip tones side by side.
        platform_catalog.adminWorkspace.setDepartmentSearchText("VQALIFE")
        _settle(qapp)
        root.resize(1600, 1000)
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"departments_mixedstatus_{theme_mode}_1600x1000.png")
        assert saved

        # Inspector open on the mixed-status set (Actions ▾ hierarchy).
        departments_page = root.findChild(QQuickItem, "departmentsWorkspacePage")
        assert departments_page is not None
        catalog = platform_catalog.adminWorkspace.departments
        active_row = next(row for row in catalog["items"] if "Active Department" in row["title"])
        departments_page.setProperty("selectedRowId", active_row["id"])
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"departments_inspector_active_{theme_mode}_1600x1000.png")
        assert saved

        inactive_row = next(row for row in catalog["items"] if "Inactive Department" in row["title"])
        departments_page.setProperty("selectedRowId", inactive_row["id"])
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"departments_inspector_inactive_{theme_mode}_1600x1000.png")
        assert saved

        platform_catalog.adminWorkspace.setDepartmentSearchText("")

        # Search with no matches -> "no results" empty state.
        platform_catalog.adminWorkspace.setDepartmentSearchText("DOES-NOT-EXIST-ANYWHERE")
        _settle(qapp)
        item = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, item, OUT_DIR / f"departments_noresults_{theme_mode}_1600x1000.png")
        assert saved
        platform_catalog.adminWorkspace.setDepartmentSearchText("")

        relevant = [m for m in messages if any(marker in m for marker in _RELEVANT_ERROR_MARKERS)]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)


def _open_department_detail(services, api_registry):
    """One fresh shell/engine per capture -- deliberately never reuses one
    Loader-backed detail page across two different rows in the same engine
    (see the Site closeout investigation note on this same technique in
    test_visual_qa_sites.py)."""
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
    platform_catalog.selectDestination("departments")
    # Return every object whose C++ side must outlive this function -- letting
    # `engine`/`shell_context`/the catalogs fall out of scope here gets them
    # garbage-collected (and their QQuickWindow deleted) before the caller
    # can use `root`.
    return root, platform_catalog, engine, shell_context, pm_catalog


def _tabs_for(detail_page) -> dict[int, str]:
    """Section index -> name, read from the real _sections array rather than
    hardcoded -- Department Detail's final section set (Overview, Employees,
    Calendar, Activity) is otherwise fixed, but reading it live keeps this
    test honest against AdminDepartmentDetailPage.qml's actual `_sections`
    property rather than a copy that can drift. Users/Projects/Documents/
    Audit are deliberately not tabs here (see Related Actions instead)."""
    raw = detail_page.property("_sections")
    sections = raw.toVariant() if hasattr(raw, "toVariant") else (raw or [])
    return {i: str(s.get("label", "")).lower() for i, s in enumerate(sections)}


def test_capture_department_detail_sparse_screenshots(qapp, services) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    try:
        sparse_id = _seed_sparse_department(services, code="VQASPARSE", name="VQA Sparse Department")
        api_registry = build_desktop_api_registry(services)
        root, _platform_catalog, _engine, _shell_context, _pm_catalog = _open_department_detail(services, api_registry)
        _settle(qapp, seconds=4.0)

        departments_page = root.findChild(QQuickItem, "departmentsWorkspacePage")
        assert departments_page is not None
        departments_page.setProperty("selectedRowId", sparse_id)
        departments_page.setProperty("detailOpen", True)
        _settle(qapp, seconds=3.0)
        detail_page = root.findChild(QQuickItem, "adminDepartmentDetailPage")
        assert detail_page is not None
        assert detail_page.property("_departmentId") == sparse_id

        # Regression guard: Key Statistics/tab-count must be THIS
        # department's own count (filteredTotal), never the whole-
        # organization total (totalCount).
        assert detail_page.property("_employeeCount") == 0

        for index, name in _tabs_for(detail_page).items():
            detail_page.setProperty("activeSectionIndex", index)
            _settle(qapp)
            mainWindow = root.findChild(QQuickItem, "mainWindow")
            saved = _grab(qapp, mainWindow, OUT_DIR / f"department_detail_sparse_{name}_light_1600x1000.png")
            assert saved

        relevant = [m for m in messages if any(marker in m for marker in _RELEVANT_ERROR_MARKERS)]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)


def test_capture_department_detail_full_screenshots(qapp, services) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    try:
        full_id, _calendar_id = _seed_full_department(services, code="VQAFULL", name="VQA Full Department")
        api_registry = build_desktop_api_registry(services)
        root, _platform_catalog, _engine, _shell_context, _pm_catalog = _open_department_detail(services, api_registry)
        _settle(qapp, seconds=4.0)

        departments_page = root.findChild(QQuickItem, "departmentsWorkspacePage")
        assert departments_page is not None
        departments_page.setProperty("selectedRowId", full_id)
        departments_page.setProperty("detailOpen", True)
        _settle(qapp, seconds=3.0)
        detail_page = root.findChild(QQuickItem, "adminDepartmentDetailPage")
        assert detail_page is not None
        assert detail_page.property("_departmentId") == full_id
        assert detail_page.property("_employeeCount") == 1

        for index, name in _tabs_for(detail_page).items():
            detail_page.setProperty("activeSectionIndex", index)
            _settle(qapp)
            mainWindow = root.findChild(QQuickItem, "mainWindow")
            saved = _grab(qapp, mainWindow, OUT_DIR / f"department_detail_full_{name}_light_1600x1000.png")
            assert saved

        # Narrow-width Overview (responsive stacking check).
        detail_page.setProperty("activeSectionIndex", 0)
        root.resize(1000, 800)
        _settle(qapp)
        mainWindow = root.findChild(QQuickItem, "mainWindow")
        saved = _grab(qapp, mainWindow, OUT_DIR / "department_detail_full_overview_light_narrow1000.png")
        assert saved

        relevant = [m for m in messages if any(marker in m for marker in _RELEVANT_ERROR_MARKERS)]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)


def test_capture_department_detail_calendar_inherited_vs_override(qapp, services) -> None:
    """The Calendar tab's Effective Calendar card in both resolver states:
    "Inherited from Organization" (sparse department, no site, no override)
    and "Department override" (full department, explicit override) --
    exercises AdminCalendarAssignmentSection's 3-way source label alongside
    Site's own binary one."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    try:
        sparse_id = _seed_sparse_department(services, code="VQACAL1", name="VQA Calendar Inherited Department")
        full_id, _calendar_id = _seed_full_department(services, code="VQACAL2", name="VQA Calendar Override Department")
        api_registry = build_desktop_api_registry(services)

        for department_id, label in ((sparse_id, "inherited"), (full_id, "override")):
            root, _platform_catalog, _engine, _shell_context, _pm_catalog = _open_department_detail(services, api_registry)
            _settle(qapp, seconds=4.0)

            departments_page = root.findChild(QQuickItem, "departmentsWorkspacePage")
            assert departments_page is not None
            departments_page.setProperty("selectedRowId", department_id)
            departments_page.setProperty("detailOpen", True)
            _settle(qapp, seconds=3.0)
            detail_page = root.findChild(QQuickItem, "adminDepartmentDetailPage")
            assert detail_page is not None
            tabs = _tabs_for(detail_page)
            calendar_index = next(i for i, name in tabs.items() if name == "calendar")
            detail_page.setProperty("activeSectionIndex", calendar_index)
            _settle(qapp)
            mainWindow = root.findChild(QQuickItem, "mainWindow")
            saved = _grab(qapp, mainWindow, OUT_DIR / f"department_detail_calendar_{label}_light_1600x1000.png")
            assert saved

        relevant = [m for m in messages if any(marker in m for marker in _RELEVANT_ERROR_MARKERS)]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)
