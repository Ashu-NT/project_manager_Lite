from __future__ import annotations

from src.api.desktop.runtime import build_desktop_api_registry
from src.core.modules.maintenance.api.desktop import (
    build_maintenance_workspace_desktop_api,
)
from pathlib import Path


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
    assert registry.maintenance_assets.list_lifecycle_statuses()[0].value == "DRAFT"
    assert registry.maintenance_dashboard.build_snapshot().overview.title == "Maintenance Dashboard"
    assert registry.maintenance_planner.build_snapshot().overview.title == "Planner"
    assert registry.maintenance_preventive.list_plan_types()[0].value == "PREVENTIVE"
    assert registry.maintenance_reliability.build_snapshot().overview.title == "Reliability"
    assert registry.maintenance_work_requests.list_statuses()[0].value == "NEW"
    assert registry.maintenance_work_orders.list_statuses()[0].value == "DRAFT"


def test_maintenance_desktop_api_does_not_import_qml_or_legacy_ui() -> None:
    root = Path("src/core/modules/maintenance/api/desktop")
    combined = "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.py")))

    assert "src.ui_qml" not in combined
    assert "ui.modules.maintenance_management" not in combined
