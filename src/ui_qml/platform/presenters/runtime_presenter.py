from __future__ import annotations

from src.api.desktop.platform import PlatformRuntimeDesktopApi
from src.ui_qml.platform.view_models.runtime import (
    PlatformMetricViewModel,
    PlatformRuntimeOverviewViewModel,
)


class PlatformRuntimePresenter:
    def __init__(self, desktop_api: PlatformRuntimeDesktopApi | None = None) -> None:
        self._desktop_api = desktop_api

    def build_overview(self) -> PlatformRuntimeOverviewViewModel:
        if self._desktop_api is None:
            return PlatformRuntimeOverviewViewModel(
                title="Platform",
                subtitle="Platform desktop API is not connected in this QML preview.",
                status_label="Preview",
                metrics=(
                    PlatformMetricViewModel("Organizations", "0", "API not connected"),
                    PlatformMetricViewModel("Enabled modules", "0", "API not connected"),
                    PlatformMetricViewModel("Licensed modules", "0", "API not connected"),
                    PlatformMetricViewModel("Available modules", "0", "API not connected"),
                ),
            )

        result = self._desktop_api.get_runtime_context()
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unknown platform API error"
            return PlatformRuntimeOverviewViewModel(
                title="Platform",
                subtitle=message,
                status_label="Error",
                metrics=(),
            )

        context = result.data
        active_org = context.active_organization
        subtitle = context.shell_summary
        if active_org is not None:
            subtitle = f"{active_org.display_name} | {context.shell_summary}"

        return PlatformRuntimeOverviewViewModel(
            title=context.context_label,
            subtitle=subtitle,
            status_label="Connected",
            metrics=(
                PlatformMetricViewModel(
                    "Active organization",
                    active_org.display_name if active_org is not None else "None",
                    "Current platform context",
                ),
                PlatformMetricViewModel(
                    "Enabled modules",
                    str(len(context.enabled_modules)),
                    "Runtime-enabled module set",
                ),
                PlatformMetricViewModel(
                    "Licensed modules",
                    str(len(context.licensed_modules)),
                    "Licensed module set",
                ),
                PlatformMetricViewModel(
                    "Available modules",
                    str(len(context.available_modules)),
                    "Visible in this desktop runtime",
                ),
            ),
        )


__all__ = ["PlatformRuntimePresenter"]
