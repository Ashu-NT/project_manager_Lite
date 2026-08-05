from __future__ import annotations

from types import SimpleNamespace

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.platform.presenters import PlatformRuntimePresenter
from src.tests.platform._platform_test_helpers import FakePlatformRuntimeApi


def test_platform_runtime_presenter_uses_desktop_api_context() -> None:
    presenter = PlatformRuntimePresenter(FakePlatformRuntimeApi())

    overview = presenter.build_overview()

    assert overview.title == "Enterprise Runtime"
    assert overview.subtitle == "TechAsh | 2 modules licensed"
    assert overview.status_label == "Connected"
    assert [(metric.label, metric.value) for metric in overview.metrics] == [
        ("Active organization", "TechAsh"),
        ("Enabled modules", "1"),
        ("Licensed modules", "2"),
        ("Available modules", "3"),
    ]


def test_platform_runtime_presenter_has_preview_state_without_api() -> None:
    presenter = PlatformRuntimePresenter()

    overview = presenter.build_overview()

    assert overview.status_label == "Preview"
    assert overview.metrics[0].supporting_text == "API not connected"


def test_platform_workspace_catalog_falls_back_to_direct_runtime_api() -> None:
    catalog = PlatformWorkspaceCatalog(
        FakePlatformRuntimeApi(),
        desktop_api_registry=SimpleNamespace(),
    )

    overview = catalog.runtimeOverview()

    assert overview["statusLabel"] == "Connected"
    assert overview["metrics"][0]["value"] == "TechAsh"


def test_platform_workspace_catalog_exposes_qml_safe_maps() -> None:
    catalog = PlatformWorkspaceCatalog(FakePlatformRuntimeApi())

    workspace = catalog.workspace("platform.admin")
    overview = catalog.runtimeOverview()

    assert workspace == {
        "routeId": "platform.admin",
        "title": "Admin Console",
        "summary": "Platform / Administration",
    }
    assert overview["statusLabel"] == "Connected"
    assert overview["metrics"][0] == {
        "label": "Active organization",
        "value": "TechAsh",
        "supportingText": "Current platform context",
    }


def test_platform_workspace_catalog_returns_module_flags_off_without_active_organization(
    services,
) -> None:
    services["user_session"].set_active_organization_id(None)
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    assert catalog.isModuleEnabled("project_management") is False
    assert catalog.hasCapability("inventory.stock.read") is False
    assert catalog.canUseIntegration(
        "project_management",
        "inventory_procurement",
        "material_demand",
    ) is False
    snapshot = catalog.capabilitySnapshot()
    assert snapshot["isPlatformEnabled"] is True
    assert snapshot["isProjectManagementEnabled"] is False
