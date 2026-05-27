from __future__ import annotations

from src.api.desktop.platform import PlatformRuntimeDesktopApi
from src.ui_qml.platform.view_models import (
    PlatformMetricViewModel,
    PlatformWorkspaceOverviewViewModel,
    PlatformWorkspaceRowViewModel,
    PlatformWorkspaceSectionViewModel,
)


class PlatformSettingsWorkspacePresenter:
    def __init__(self, *, runtime_api: PlatformRuntimeDesktopApi | None = None) -> None:
        self._runtime_api = runtime_api

    def build_overview(self) -> PlatformWorkspaceOverviewViewModel:
        runtime_result = self._runtime_api.get_runtime_context() if self._runtime_api is not None else None
        modules_result = self._runtime_api.list_modules() if self._runtime_api is not None else None
        organizations_result = self._runtime_api.list_organizations(active_only=None) if self._runtime_api is not None else None

        if runtime_result is not None and (not runtime_result.ok or runtime_result.data is None):
            message = runtime_result.error.message if runtime_result.error is not None else "Unknown platform API error"
            return PlatformWorkspaceOverviewViewModel(
                title="Settings",
                subtitle=message,
                status_label="Error",
            )

        if runtime_result is None or runtime_result.data is None:
            return PlatformWorkspaceOverviewViewModel(
                title="Settings",
                subtitle="Platform runtime API is not connected in this QML preview.",
                status_label="Preview",
                metrics=(
                    PlatformMetricViewModel("Licensed modules", "0", "API not connected"),
                    PlatformMetricViewModel("Organizations", "0", "API not connected"),
                ),
            )

        runtime_context = runtime_result.data
        modules = self._tuple_data(modules_result)
        organizations = self._tuple_data(organizations_result)

        return PlatformWorkspaceOverviewViewModel(
            title="Settings",
            subtitle="Runtime settings, tenancy, and module state prepared for the QML shell.",
            status_label="Connected",
            metrics=(
                PlatformMetricViewModel("Licensed modules", str(len(runtime_context.licensed_modules)), "Currently licensed"),
                PlatformMetricViewModel("Enabled modules", str(len(runtime_context.enabled_modules)), "Runtime active"),
                PlatformMetricViewModel("Planned modules", str(len(runtime_context.planned_modules)), "Not yet enabled"),
                PlatformMetricViewModel("Organizations", str(len(organizations)), "Install profiles"),
            ),
            sections=(
                PlatformWorkspaceSectionViewModel(
                    title="Organization Profiles",
                    rows=tuple(
                        PlatformWorkspaceRowViewModel(
                            org.display_name,
                            org.organization_code,
                            f"{org.timezone_name} | {org.base_currency}",
                        )
                        for org in organizations[:5]
                    ),
                    empty_state="No organizations are configured yet.",
                ),
                PlatformWorkspaceSectionViewModel(
                    title="Module Catalog",
                    rows=tuple(
                        PlatformWorkspaceRowViewModel(
                            module.label,
                            module.stage.title(),
                            module.description,
                        )
                        for module in modules[:5]
                    ),
                    empty_state="No module metadata is available yet.",
                ),
                PlatformWorkspaceSectionViewModel(
                    title="Platform Capabilities",
                    rows=tuple(
                        PlatformWorkspaceRowViewModel(
                            capability.label,
                            "Always on" if capability.always_on else capability.code,
                            capability.description,
                        )
                        for capability in runtime_context.platform_capabilities[:5]
                    ),
                    empty_state="No platform capabilities were returned for this context.",
                ),
            ),
        )

    @staticmethod
    def _tuple_data(result: object | None) -> tuple[object, ...]:
        if result is None or not getattr(result, "ok", False) or getattr(result, "data", None) is None:
            return ()
        return tuple(result.data)


__all__ = ["PlatformSettingsWorkspacePresenter"]
