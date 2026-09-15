"""Phase J1 visual QA: scene-graph offscreen capture of Platform Overview at
multiple breakpoints and themes. Not a correctness assertion suite -- renders
PNGs to a scratch directory for manual visual inspection, and asserts only
that rendering itself completes without error."""

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


@pytest.mark.parametrize("theme_mode", ["light", "dark"])
def test_capture_platform_overview_screenshots(qapp, services, theme_mode) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))

    try:
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

        for size_name, (w, h) in SIZES.items():
            root.resize(w, h)
            _settle(qapp)

            item = root.findChild(QQuickItem, "mainWindow")
            assert item is not None

            saved = _grab(qapp, item, OUT_DIR / f"platform_overview_j1_{theme_mode}_{size_name}.png")
            assert saved, f"platform_overview_j1_{theme_mode}_{size_name} failed to save"

        relevant = [
            m for m in messages
            if "ReferenceError" in m or "TypeError" in m or "unknown icon name" in m
            or "is not defined" in m or "Cannot read prop" in m
        ]
        assert not relevant, "\n".join(relevant)
    finally:
        qInstallMessageHandler(previous_handler)
