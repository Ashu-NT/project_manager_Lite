"""Regression: Site Detail's "Open Project Management" action (an optional
external tile in Overview's Related Actions -- Site Detail deliberately has
no dedicated Projects tab; see AdminSiteDetailPage.qml's `_sections` note)
must actually switch the shell into the Project Management module, not
silently fall back to Platform's own Overview surface.

`PlatformWorkspacePage.qml`'s internal destination router
(`_directSurfaceDestinations`/`_surfaceFor()`) has no "project_management"
entry -- Project Management is a separate top-level module, not a
Platform-internal destination. The original wiring called
`navigateToDestination("project_management")`, which fell through that
router straight to "overview". The fix threads the shell's own
`ShellContext` down to `SitesWorkspacePage.qml` and calls
`shellModel.selectRoute("project_management.workspace")` instead -- the
same cross-module abstraction Project Management's own dashboard cards
already use in the opposite direction. This test drives the same
`handleDetailAction("open_project_management")` entry point the Related
Actions tile calls, loading the real app shell (not just Platform in
isolation) so the fix is proven against the actual route registry, not a
stub."""

from __future__ import annotations

import os
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, qInstallMessageHandler
from PySide6.QtQuick import QQuickItem

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)
from src.ui_qml.modules.project_management.navigation import PM_CANONICAL_ROUTE_ID
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.context import build_shell_context
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml
from src.ui_qml.shell.qml_registry import build_qml_route_registry


def _settle(app, *, seconds: float = 2.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)


def test_open_project_management_cta_switches_shell_route_not_overview(qapp, services) -> None:
    site_service = services["site_service"]
    site = site_service.create_site(site_code="PMNAV-1", name="PM Nav Site")

    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    try:
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
        platform_catalog.selectDestination("sites")
        _settle(qapp, seconds=3.0)

        sites_page = root.findChild(QQuickItem, "sitesWorkspacePage")
        assert sites_page is not None

        sites_page.setProperty("selectedRowId", site.id)
        sites_page.setProperty("detailOpen", True)
        _settle(qapp, seconds=2.0)

        sites_page.handleDetailAction("open_project_management")
        _settle(qapp, seconds=1.0)

        assert shell_context.currentRouteId == PM_CANONICAL_ROUTE_ID, (
            f"expected the shell to switch into Project Management "
            f"({PM_CANONICAL_ROUTE_ID!r}), got {shell_context.currentRouteId!r} -- "
            "the CTA fell back to Platform's own Overview surface instead "
            "of a real module switch"
        )

        relevant = [
            m for m in messages
            if any(marker in m for marker in ("ReferenceError", "TypeError", "is not defined", "Cannot read prop"))
        ]
        assert relevant == [], relevant
    finally:
        qInstallMessageHandler(previous_handler)
