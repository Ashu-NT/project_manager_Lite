from src.api.desktop.platform.models import (
    DesktopApiResult,
    ModuleDto,
    OrganizationDto,
    PlatformRuntimeContextDto,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.platform.presenters import PlatformRuntimePresenter


class _FakePlatformRuntimeApi:
    def get_runtime_context(self):
        module = ModuleDto(
            code="project_management",
            label="Project Management",
            description="Projects",
            default_enabled=True,
            stage="active",
            primary_capabilities=("delivery",),
        )
        return DesktopApiResult(
            ok=True,
            data=PlatformRuntimeContextDto(
                context_label="Enterprise Runtime",
                shell_summary="2 modules enabled",
                active_organization=OrganizationDto(
                    id="org-1",
                    organization_code="ORG",
                    display_name="TechAsh",
                    timezone_name="UTC",
                    base_currency="EUR",
                    is_active=True,
                    version=1,
                ),
                platform_capabilities=(),
                entitlements=(),
                enabled_modules=(module,),
                licensed_modules=(module,),
                available_modules=(module,),
                planned_modules=(),
            ),
        )


def test_platform_runtime_presenter_uses_desktop_api_context() -> None:
    presenter = PlatformRuntimePresenter(_FakePlatformRuntimeApi())

    overview = presenter.build_overview()

    assert overview.title == "Enterprise Runtime"
    assert overview.subtitle == "TechAsh | 2 modules enabled"
    assert overview.status_label == "Connected"
    assert [(metric.label, metric.value) for metric in overview.metrics] == [
        ("Active organization", "TechAsh"),
        ("Enabled modules", "1"),
        ("Licensed modules", "1"),
        ("Available modules", "1"),
    ]


def test_platform_runtime_presenter_has_preview_state_without_api() -> None:
    presenter = PlatformRuntimePresenter()

    overview = presenter.build_overview()

    assert overview.status_label == "Preview"
    assert overview.metrics[0].supporting_text == "API not connected"


def test_platform_workspace_catalog_exposes_qml_safe_maps() -> None:
    catalog = PlatformWorkspaceCatalog(_FakePlatformRuntimeApi())

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
