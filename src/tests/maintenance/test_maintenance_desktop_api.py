from __future__ import annotations

from pathlib import Path

from src.api.desktop.runtime import build_desktop_api_registry
from src.core.modules.maintenance.api.desktop import (
    build_maintenance_workspace_desktop_api,
)


EXPECTED_MAINTENANCE_WORKSPACE_KEYS = [
    "dashboard",
    "assets",
    "work_requests",
    "work_orders",
    "preventive",
    "reliability",
    "planner",
]


def test_maintenance_desktop_api_lists_workspace_descriptors() -> None:
    api = build_maintenance_workspace_desktop_api()

    descriptors = api.list_workspaces()

    assert [descriptor.key for descriptor in descriptors] == EXPECTED_MAINTENANCE_WORKSPACE_KEYS
    assert descriptors[1].title == "Assets"
    assert api.get_workspace("maintenance_management.work_orders").title == "Work Orders"
    assert api.get_workspace("maintenance_management.unknown") is None


def test_build_desktop_api_registry_exposes_maintenance_adapters(services) -> None:
    registry = build_desktop_api_registry(services)

    assert registry.maintenance_workspaces.list_workspaces()[0].key == "dashboard"
    assert registry.maintenance_workspaces.get_workspace("maintenance_management.planner").title == "Planner"


def test_maintenance_desktop_api_does_not_import_qml_or_legacy_ui() -> None:
    root = Path("src/core/modules/maintenance/api/desktop")
    combined = "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.py")))

    assert "src.ui_qml" not in combined
    assert "ui.modules.maintenance_management" not in combined
