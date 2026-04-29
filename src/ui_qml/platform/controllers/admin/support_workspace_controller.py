from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication

from src.ui_qml.platform.presenters.support_workspace_presenter import (
    PlatformSupportWorkspacePresenter,
)

from ..common import (
    PlatformWorkspaceControllerBase,
    serialize_action_list,
    serialize_operation_result,
)


class PlatformSupportWorkspaceController(PlatformWorkspaceControllerBase):
    supportSettingsChanged = Signal()
    supportPathsChanged = Signal()
    updateStatusChanged = Signal()
    activityFeedChanged = Signal()
    incidentIdChanged = Signal()
    bundleStateChanged = Signal()

    def __init__(
        self,
        *,
        presenter: PlatformSupportWorkspacePresenter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenter = presenter
        self._support_settings: dict[str, object] = {}
        self._support_paths: dict[str, object] = {}
        self._update_status: dict[str, object] = {}
        self._activity_feed: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._incident_id = ""
        self._bundle_state: dict[str, object] = self._empty_bundle_state()
        self.refresh()

    @Property("QVariantMap", notify=supportSettingsChanged)
    def supportSettings(self) -> dict[str, object]:
        return self._support_settings

    @Property("QVariantMap", notify=supportPathsChanged)
    def supportPaths(self) -> dict[str, object]:
        return self._support_paths

    @Property("QVariantMap", notify=updateStatusChanged)
    def updateStatus(self) -> dict[str, object]:
        return self._update_status

    @Property("QVariantMap", notify=activityFeedChanged)
    def activityFeed(self) -> dict[str, object]:
        return self._activity_feed

    @Property(str, notify=incidentIdChanged)
    def incidentId(self) -> str:
        return self._incident_id

    @Property("QVariantMap", notify=bundleStateChanged)
    def bundleState(self) -> dict[str, object]:
        return self._bundle_state

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        self._set_error_message("")
        if not self._incident_id:
            self._set_incident_id(self._presenter.new_incident_id())
        self._set_support_settings(self._presenter.build_settings_state())
        self._set_support_paths(self._presenter.build_paths_state())
        self._set_bundle_state(self._empty_bundle_state())
        if not self._update_status:
            self._set_update_status(self._presenter.initial_update_status(self._support_settings))
        self._refresh_activity_feed()
        self._set_is_loading(False)

    @Slot(str)
    def setIncidentId(self, incident_id: str) -> None:
        normalized = incident_id.strip()
        if not normalized:
            return
        if normalized == self._incident_id:
            return
        self._set_incident_id(normalized)
        self._set_bundle_state(self._empty_bundle_state())
        self._refresh_activity_feed()
        self._set_feedback_message("")
        self._set_error_message("")

    @Slot()
    def newIncidentId(self) -> None:
        self._set_incident_id(self._presenter.new_incident_id())
        self._set_bundle_state(self._empty_bundle_state())
        self._refresh_activity_feed()
        self._set_feedback_message("Created a new support incident trace ID.")
        self._set_error_message("")

    @Slot()
    def copyIncidentId(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None and self._incident_id:
            clipboard.setText(self._incident_id)
        self._set_feedback_message("Copied support incident trace ID.")
        self._set_error_message("")

    @Slot("QVariantMap", result="QVariantMap")
    def saveSettings(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_support_action(
            action=lambda: self._presenter.save_settings(payload, trace_id=self._incident_id),
            success_message="Support settings saved.",
            on_success=self._refresh_activity_feed,
            success_result_handler=lambda result: self._set_support_settings(
                self._presenter.build_settings_state()
            ),
        )

    @Slot("QVariantMap", result="QVariantMap")
    def checkForUpdates(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_support_action(
            action=lambda: self._presenter.check_for_updates(payload, trace_id=self._incident_id),
            success_message="Update check completed.",
            on_success=self._refresh_activity_feed,
            success_result_handler=lambda result: self._set_update_status(
                self._presenter.serialize_update_status(result.data)
            ),
        )

    @Slot(result="QVariantMap")
    def exportDiagnostics(self) -> dict[str, object]:
        return self._run_support_action(
            action=lambda: self._presenter.export_diagnostics(incident_id=self._incident_id),
            success_message="Diagnostics bundle created.",
            on_success=self._refresh_activity_feed,
            success_result_handler=lambda result: self._set_bundle_state(
                self._presenter.serialize_bundle_state(
                    current_state=self._bundle_state,
                    diagnostics_bundle=result.data,
                )
            ),
        )

    @Slot(str, result="QVariantMap")
    def exportDiagnosticsTo(self, output_path: str) -> dict[str, object]:
        return self._run_support_action(
            action=lambda: self._presenter.export_diagnostics_to(
                incident_id=self._incident_id,
                output_path=output_path,
            ),
            success_message="Diagnostics bundle created.",
            on_success=self._refresh_activity_feed,
            success_result_handler=lambda result: self._set_bundle_state(
                self._presenter.serialize_bundle_state(
                    current_state=self._bundle_state,
                    diagnostics_bundle=result.data,
                )
            ),
        )

    @Slot(result="QVariantMap")
    def reportIncident(self) -> dict[str, object]:
        return self._run_support_action(
            action=lambda: self._presenter.create_incident_report(incident_id=self._incident_id),
            success_message="Incident report package created.",
            on_success=self._refresh_activity_feed,
            success_result_handler=lambda result: self._set_bundle_state(
                self._presenter.serialize_bundle_state(
                    current_state=self._bundle_state,
                    incident_report_bundle=result.data,
                )
            ),
        )

    @Slot("QVariantMap", result="QVariantMap")
    def installAvailableUpdate(self, payload: dict[str, object]) -> dict[str, object]:
        operation_result = self._run_support_action(
            action=lambda: self._presenter.install_available_update(
                payload,
                trace_id=self._incident_id,
            ),
            success_message="Update install handoff launched.",
            on_success=self._refresh_activity_feed,
        )
        if operation_result.get("ok"):
            app = QGuiApplication.instance()
            if app is not None:
                app.quit()
        return operation_result

    @Slot()
    def openLogsFolder(self) -> None:
        self._open_url(
            str(self._support_paths.get("logsDirectoryUrl") or ""),
            success_message="Opened logs folder.",
        )

    @Slot()
    def openDataFolder(self) -> None:
        self._open_url(
            str(self._support_paths.get("dataDirectoryUrl") or ""),
            success_message="Opened app data folder.",
        )

    @Slot()
    def openUpdateDownload(self) -> None:
        self._open_url(
            str(self._update_status.get("downloadUrl") or ""),
            success_message="Opened update download target.",
        )

    @Slot()
    def openLatestDiagnostics(self) -> None:
        self._open_url(
            str(self._bundle_state.get("lastDiagnosticsUrl") or ""),
            success_message="Opened diagnostics bundle.",
        )

    @Slot()
    def openLatestIncidentReport(self) -> None:
        self._open_url(
            str(self._bundle_state.get("lastIncidentReportUrl") or ""),
            success_message="Opened incident report package.",
        )

    def _run_support_action(
        self,
        *,
        action: Callable[[], object],
        success_message: str,
        on_success: Callable[[], None],
        success_result_handler: Callable[[object], None] | None = None,
    ) -> dict[str, object]:
        self._set_is_busy(True)
        self._set_error_message("")
        try:
            result = action()
            payload = serialize_operation_result(result, success_message=success_message)
            self._set_operation_result(payload)
            if payload["ok"] and getattr(result, "data", None) is not None:
                if success_result_handler is not None:
                    success_result_handler(result)
                self._set_feedback_message(str(payload["message"]))
                on_success()
            else:
                self._set_feedback_message("")
                self._set_error_message(str(payload["message"]))
            return dict(payload)
        finally:
            self._set_is_busy(False)

    def _refresh_activity_feed(self) -> None:
        activity_feed = serialize_action_list(self._presenter.build_activity_feed(self._incident_id))
        self._set_activity_feed(activity_feed)
        self._set_empty_state("" if activity_feed.get("items") else str(activity_feed.get("emptyState") or ""))

    def _open_url(self, target_url: str, *, success_message: str) -> None:
        normalized = target_url.strip()
        if not normalized:
            self._set_error_message("This support resource is not available yet.")
            self._set_feedback_message("")
            return
        opened = QDesktopServices.openUrl(QUrl(normalized))
        if opened:
            self._set_feedback_message(success_message)
            self._set_error_message("")
        else:
            self._set_feedback_message("")
            self._set_error_message("The requested support resource could not be opened.")

    def _set_support_settings(self, support_settings: dict[str, object]) -> None:
        if support_settings == self._support_settings:
            return
        self._support_settings = support_settings
        self.supportSettingsChanged.emit()

    def _set_support_paths(self, support_paths: dict[str, object]) -> None:
        if support_paths == self._support_paths:
            return
        self._support_paths = support_paths
        self.supportPathsChanged.emit()

    def _set_update_status(self, update_status: dict[str, object]) -> None:
        if update_status == self._update_status:
            return
        self._update_status = update_status
        self.updateStatusChanged.emit()

    def _set_activity_feed(self, activity_feed: dict[str, object]) -> None:
        if activity_feed == self._activity_feed:
            return
        self._activity_feed = activity_feed
        self.activityFeedChanged.emit()

    def _set_incident_id(self, value: str) -> None:
        if value == self._incident_id:
            return
        self._incident_id = value
        self.incidentIdChanged.emit()

    def _set_bundle_state(self, bundle_state: dict[str, object]) -> None:
        if bundle_state == self._bundle_state:
            return
        self._bundle_state = bundle_state
        self.bundleStateChanged.emit()

    def _empty_bundle_state(self) -> dict[str, object]:
        return {
            "lastDiagnosticsPath": "",
            "lastDiagnosticsUrl": "",
            "lastDiagnosticsWarnings": [],
            "lastIncidentReportPath": "",
            "lastIncidentReportUrl": "",
            "lastIncidentReportWarnings": [],
            "supportEmail": str(self._support_settings.get("supportEmail") or ""),
        }


__all__ = ["PlatformSupportWorkspaceController"]
