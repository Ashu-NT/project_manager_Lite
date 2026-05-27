from __future__ import annotations

from datetime import datetime
from typing import Any

from src.api.desktop.platform import (
    PlatformSupportDesktopApi,
    SupportSettingsUpdateCommand,
)
from src.api.desktop.platform.models import DesktopApiResult
from src.ui_qml.platform.presenters.support import (
    bool_value,
    option_item,
    preview_error_result,
    string_value,
    title_case_code,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


class PlatformSupportWorkspacePresenter:
    def __init__(self, *, support_api: PlatformSupportDesktopApi | None = None) -> None:
        self._support_api = support_api

    def new_incident_id(self) -> str:
        if self._support_api is None:
            return "preview-incident"
        return self._support_api.new_incident_id()

    def build_settings_state(self) -> dict[str, object]:
        if self._support_api is None:
            return self._preview_settings_state()
        result = self._support_api.load_settings()
        if not result.ok or result.data is None:
            return self._preview_settings_state()
        dto = result.data
        return {
            "updateChannel": dto.update_channel,
            "updateAutoCheck": dto.update_auto_check,
            "updateManifestSource": dto.update_manifest_source,
            "themeMode": dto.theme_mode,
            "governanceMode": dto.governance_mode,
            "appVersion": dto.app_version,
            "supportEmail": dto.support_email,
            "channelOptions": self._channel_options(),
        }

    def build_paths_state(self) -> dict[str, object]:
        if self._support_api is None:
            return {
                "dataDirectoryPath": "",
                "dataDirectoryUrl": "",
                "logsDirectoryPath": "",
                "logsDirectoryUrl": "",
                "incidentsDirectoryPath": "",
                "incidentsDirectoryUrl": "",
                "eventsFilePath": "",
                "eventsFileUrl": "",
            }
        result = self._support_api.get_paths()
        if not result.ok or result.data is None:
            return {
                "dataDirectoryPath": "",
                "dataDirectoryUrl": "",
                "logsDirectoryPath": "",
                "logsDirectoryUrl": "",
                "incidentsDirectoryPath": "",
                "incidentsDirectoryUrl": "",
                "eventsFilePath": "",
                "eventsFileUrl": "",
            }
        dto = result.data
        return {
            "dataDirectoryPath": dto.data_directory_path,
            "dataDirectoryUrl": dto.data_directory_url,
            "logsDirectoryPath": dto.logs_directory_path,
            "logsDirectoryUrl": dto.logs_directory_url,
            "incidentsDirectoryPath": dto.incidents_directory_path,
            "incidentsDirectoryUrl": dto.incidents_directory_url,
            "eventsFilePath": dto.events_file_path,
            "eventsFileUrl": dto.events_file_url,
        }

    def build_activity_feed(self, incident_id: str) -> PlatformWorkspaceActionListViewModel:
        if self._support_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Support Activity",
                subtitle="Support activity appears here once the platform support API is connected.",
                empty_state="Platform support API is not connected in this QML preview.",
            )
        result = self._support_api.list_activity(trace_id=incident_id or None, limit=12)
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load support activity."
            return PlatformWorkspaceActionListViewModel(
                title="Support Activity",
                subtitle=message,
                empty_state=message,
            )
        items = tuple(self._serialize_event_item(row) for row in result.data)
        return PlatformWorkspaceActionListViewModel(
            title="Support Activity",
            subtitle="Structured operational support events for the selected incident trace.",
            empty_state="No support activity has been recorded for this incident yet.",
            items=items,
        )

    def initial_update_status(self, settings_state: dict[str, object]) -> dict[str, object]:
        return {
            "statusLabel": "Ready" if self._support_api is not None else "Preview",
            "summary": (
                "Save settings or run a check to load the latest release manifest."
                if self._support_api is not None
                else "Support update status appears here once the platform support API is connected."
            ),
            "currentVersion": str(settings_state.get("appVersion") or ""),
            "latestVersion": "",
            "channel": str(settings_state.get("updateChannel") or "stable"),
            "updateAvailable": False,
            "canOpenDownload": False,
            "downloadUrl": "",
            "notes": "",
            "sha256": "",
        }

    def save_settings(
        self,
        payload: dict[str, Any],
        *,
        trace_id: str,
    ) -> DesktopApiResult[object]:
        if self._support_api is None:
            return preview_error_result("Platform support API is not connected in this QML preview.")
        return self._support_api.save_settings(self._build_settings_command(payload), trace_id=trace_id)

    def check_for_updates(
        self,
        payload: dict[str, Any],
        *,
        trace_id: str,
    ) -> DesktopApiResult[object]:
        if self._support_api is None:
            return preview_error_result("Platform support API is not connected in this QML preview.")
        return self._support_api.check_for_updates(self._build_settings_command(payload), trace_id=trace_id)

    def export_diagnostics(self, *, incident_id: str) -> DesktopApiResult[object]:
        if self._support_api is None:
            return preview_error_result("Platform support API is not connected in this QML preview.")
        return self._support_api.export_diagnostics(incident_id=incident_id)

    def export_diagnostics_to(
        self,
        *,
        incident_id: str,
        output_path: str,
    ) -> DesktopApiResult[object]:
        if self._support_api is None:
            return preview_error_result("Platform support API is not connected in this QML preview.")
        return self._support_api.export_diagnostics_to(
            incident_id=incident_id,
            output_path=output_path,
        )

    def create_incident_report(self, *, incident_id: str) -> DesktopApiResult[object]:
        if self._support_api is None:
            return preview_error_result("Platform support API is not connected in this QML preview.")
        return self._support_api.create_incident_report(incident_id=incident_id)

    def install_available_update(
        self,
        payload: dict[str, Any],
        *,
        trace_id: str,
    ) -> DesktopApiResult[object]:
        if self._support_api is None:
            return preview_error_result("Platform support API is not connected in this QML preview.")
        return self._support_api.install_available_update(
            self._build_settings_command(payload),
            trace_id=trace_id,
        )

    @staticmethod
    def serialize_update_status(dto) -> dict[str, object]:
        return {
            "statusLabel": dto.status_label,
            "summary": dto.summary,
            "currentVersion": dto.current_version,
            "latestVersion": dto.latest_version,
            "channel": dto.channel,
            "updateAvailable": dto.update_available,
            "canOpenDownload": dto.can_open_download,
            "downloadUrl": dto.download_url,
            "notes": dto.notes,
            "sha256": dto.sha256,
        }

    @staticmethod
    def serialize_bundle_state(
        *,
        current_state: dict[str, object],
        diagnostics_bundle=None,
        incident_report_bundle=None,
    ) -> dict[str, object]:
        state = dict(current_state)
        if diagnostics_bundle is not None:
            state.update(
                {
                    "lastDiagnosticsPath": diagnostics_bundle.output_path,
                    "lastDiagnosticsUrl": diagnostics_bundle.output_url,
                    "lastDiagnosticsWarnings": list(diagnostics_bundle.warnings),
                }
            )
        if incident_report_bundle is not None:
            state.update(
                {
                    "lastIncidentReportPath": incident_report_bundle.output_path,
                    "lastIncidentReportUrl": incident_report_bundle.output_url,
                    "lastIncidentReportWarnings": list(incident_report_bundle.warnings),
                    "supportEmail": incident_report_bundle.support_email,
                }
            )
        return state

    @staticmethod
    def _build_settings_command(payload: dict[str, Any]) -> SupportSettingsUpdateCommand:
        return SupportSettingsUpdateCommand(
            update_channel=string_value(payload, "updateChannel", default="stable"),
            update_auto_check=bool_value(payload, "updateAutoCheck", default=False),
            update_manifest_source=string_value(payload, "updateManifestSource"),
        )

    @staticmethod
    def _preview_settings_state() -> dict[str, object]:
        return {
            "updateChannel": "stable",
            "updateAutoCheck": False,
            "updateManifestSource": "",
            "themeMode": "light",
            "governanceMode": "off",
            "appVersion": "",
            "supportEmail": "",
            "channelOptions": PlatformSupportWorkspacePresenter._channel_options(),
        }

    @staticmethod
    def _channel_options() -> list[dict[str, str]]:
        return [
            option_item(label="Stable", value="stable", supporting_text="Recommended production channel"),
            option_item(label="Beta", value="beta", supporting_text="Preview channel for pre-release builds"),
        ]

    @staticmethod
    def _serialize_event_item(row) -> PlatformWorkspaceActionItemViewModel:
        timestamp_label = PlatformSupportWorkspacePresenter._timestamp_label(row.timestamp_utc)
        return PlatformWorkspaceActionItemViewModel(
            id=f"{row.trace_id}:{row.timestamp_utc}:{row.event_type}",
            title=row.message or title_case_code(row.event_type),
            status_label=str(row.level or "INFO").title(),
            subtitle=f"{timestamp_label} | {PlatformSupportWorkspacePresenter._event_label(row.event_type)}",
            supporting_text=row.details_summary or f"Trace: {row.trace_id}",
            meta_text=f"Incident: {row.trace_id}",
        )

    @staticmethod
    def _timestamp_label(value: str) -> str:
        try:
            return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return value

    @staticmethod
    def _event_label(value: str) -> str:
        text = str(value or "").replace(".", " ").replace("_", " ").strip()
        return text.title() or "Support Event"


__all__ = ["PlatformSupportWorkspacePresenter"]
