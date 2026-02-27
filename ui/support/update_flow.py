from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox

from infra.operational_support import bind_trace_id
from infra.path import user_data_dir
from infra.update import UpdateCheckResult, check_for_updates, default_update_manifest_source
from infra.updater import (
    PreparedUpdateLaunch,
    download_update_installer,
    launch_windows_update_handoff,
    prepare_windows_update_handoff,
    verify_sha256,
)
from infra.version import get_app_version
from ui.shared.async_job import JobUiConfig, start_async_job


class SupportUpdateFlowMixin:
    def _load_settings(self) -> None:
        channel = self._settings_store.load_update_channel(default_channel="stable")
        idx = self.channel_combo.findData(channel)
        self.channel_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.auto_check.setChecked(self._settings_store.load_update_auto_check(default_enabled=False))
        self.manifest_url.setText(
            self._settings_store.load_update_manifest_url(
                default_url=default_update_manifest_source()
            )
        )
        self._append_result(
            f"Current app version: {get_app_version()} | channel={channel} | auto-check={self.auto_check.isChecked()}"
        )
        self._append_result(f"Incident trace ID: {self._current_incident_id()}")
        self._emit_support_event(
            event_type="support.tab.opened",
            message="Support tab opened.",
            data={"channel": channel, "auto_check": self.auto_check.isChecked()},
        )

    def _save_update_settings(self, *, show_feedback: bool = True) -> None:
        channel = str(self.channel_combo.currentData() or "stable")
        manifest = self.manifest_url.text().strip() or default_update_manifest_source()
        self.manifest_url.setText(manifest)
        self._settings_store.save_update_channel(channel)
        self._settings_store.save_update_auto_check(self.auto_check.isChecked())
        self._settings_store.save_update_manifest_url(manifest)
        self._append_result(
            f"Saved update settings: channel={channel}, auto-check={self.auto_check.isChecked()}, source='{manifest or '-'}'"
        )
        self._emit_support_event(
            event_type="support.update.settings_saved",
            message="Update settings saved.",
            data={
                "channel": channel,
                "auto_check": self.auto_check.isChecked(),
                "manifest_source": manifest,
            },
        )
        if show_feedback:
            QMessageBox.information(self, "Support", "Update settings saved.")

    def _set_update_busy(self, busy: bool) -> None:
        self.btn_check_updates.setEnabled(not busy)
        self.btn_save_update_settings.setEnabled(not busy)

    def _check_updates(self) -> None:
        self._save_update_settings(show_feedback=False)
        channel = self._settings_store.load_update_channel(default_channel="stable")
        manifest = self._settings_store.load_update_manifest_url(
            default_url=default_update_manifest_source()
        )
        if not manifest:
            QMessageBox.information(self, "Support", "Set a manifest source before checking for updates.")
            return

        incident_id = self._current_incident_id()
        self._emit_support_event(
            event_type="support.update.check_started",
            message="Started update check.",
            trace_id=incident_id,
            data={"channel": channel, "manifest_source": manifest},
        )

        def _work(token, progress):
            with bind_trace_id(incident_id):
                token.raise_if_cancelled()
                progress(None, "Checking release manifest...")
                result = check_for_updates(
                    current_version=get_app_version(),
                    channel=channel,
                    manifest_source=manifest,
                )
                token.raise_if_cancelled()
                return result

        start_async_job(
            parent=self,
            ui=JobUiConfig(
                title="Check Updates",
                label="Checking for updates...",
                allow_retry=True,
            ),
            work=_work,
            on_success=lambda result: self._handle_update_result(result, incident_id=incident_id),
            on_error=lambda msg: self._handle_async_error(
                title="Support",
                context="Update check",
                event_type="support.update.check_failed",
                message=msg,
            ),
            on_cancel=lambda: self._on_update_check_canceled(incident_id),
            set_busy=self._set_update_busy,
        )

    def _on_update_check_canceled(self, incident_id: str) -> None:
        self._append_result("Update check canceled.")
        self._emit_support_event(
            event_type="support.update.check_canceled",
            message="Update check canceled by user.",
            trace_id=incident_id,
        )

    def _handle_update_result(self, result: UpdateCheckResult, *, incident_id: str) -> None:
        self._append_result(result.message)
        if not result.update_available or result.latest is None:
            self._emit_support_event(
                event_type="support.update.no_change",
                message=result.message,
                trace_id=incident_id,
            )
            QMessageBox.information(self, "Check Updates", result.message)
            return

        details = (
            f"{result.message}\n"
            f"Channel: {result.channel}\n"
            f"Download: {result.latest.url or 'N/A'}\n"
            f"SHA256: {result.latest.sha256 or 'N/A'}\n"
            f"Notes: {result.latest.notes or 'N/A'}"
        )
        self._append_result(details)
        self._emit_support_event(
            event_type="support.update.available",
            message=result.message,
            trace_id=incident_id,
            data={
                "channel": result.channel,
                "version": result.latest.version,
                "download_url": result.latest.url or "",
                "sha256": result.latest.sha256 or "",
            },
        )

        if result.latest.url:
            box = QMessageBox(self)
            box.setWindowTitle("Update Available")
            box.setIcon(QMessageBox.Information)
            box.setText(result.message)
            box.setInformativeText(
                "Choose Install Now to close the app, run the installer, and relaunch automatically."
            )
            install_button = box.addButton("Install Now", QMessageBox.AcceptRole)
            open_button = box.addButton("Open Download Page", QMessageBox.ActionRole)
            box.addButton("Later", QMessageBox.RejectRole)
            box.setDefaultButton(install_button)
            box.exec()

            clicked = box.clickedButton()
            if clicked == install_button:
                self._download_and_install_update(result, incident_id=incident_id)
            elif clicked == open_button:
                self._emit_support_event(
                    event_type="support.update.download_page_opened",
                    message="Opened update download URL.",
                    trace_id=incident_id,
                    data={"download_url": result.latest.url},
                )
                QDesktopServices.openUrl(QUrl(result.latest.url))

    def _resolve_relaunch_command(self) -> tuple[str, list[str]]:
        if bool(getattr(sys, "frozen", False)):
            return str(sys.executable), []
        project_root = Path(__file__).resolve().parents[2]
        entry = project_root / "main_qt.py"
        return str(sys.executable), [str(entry)]

    def _download_and_install_update(self, result: UpdateCheckResult, *, incident_id: str) -> None:
        latest = result.latest
        if latest is None or not latest.url:
            QMessageBox.information(self, "Update", "No installer URL was provided in the manifest.")
            return
        if os.name != "nt":
            QMessageBox.information(
                self,
                "Update",
                "In-app install is currently supported on Windows only. Opening download URL.",
            )
            self._emit_support_event(
                event_type="support.update.non_windows_download",
                message="Installer handoff unavailable on this platform; opened URL.",
                trace_id=incident_id,
                data={"download_url": latest.url},
            )
            QDesktopServices.openUrl(QUrl(latest.url))
            return

        updates_dir = user_data_dir() / "updates"
        app_pid = os.getpid()
        self._emit_support_event(
            event_type="support.update.install_started",
            message="Started in-app update install flow.",
            trace_id=incident_id,
            data={"download_url": latest.url},
        )

        def _work(token, progress):
            with bind_trace_id(incident_id):
                token.raise_if_cancelled()
                installer_path = download_update_installer(
                    url=latest.url or "",
                    download_dir=updates_dir,
                    progress=progress,
                    is_cancelled=token.is_cancelled,
                )
                token.raise_if_cancelled()
                progress(None, "Verifying installer checksum...")
                expected_hash = latest.sha256 or ""
                if expected_hash and not verify_sha256(installer_path, expected_hash):
                    raise RuntimeError("Downloaded installer failed SHA256 verification.")
                progress(None, "Preparing update handoff...")
                relaunch_exe, relaunch_args = self._resolve_relaunch_command()
                prepared = prepare_windows_update_handoff(
                    installer_path=installer_path,
                    app_pid=app_pid,
                    relaunch_executable=relaunch_exe,
                    relaunch_args=relaunch_args,
                    output_dir=updates_dir,
                )
                token.raise_if_cancelled()
                return prepared

        start_async_job(
            parent=self,
            ui=JobUiConfig(
                title="Install Update",
                label="Preparing update installer...",
                allow_retry=True,
            ),
            work=_work,
            on_success=lambda prepared: self._run_prepared_update(prepared, incident_id=incident_id),
            on_error=lambda msg: self._handle_async_error(
                title="Update",
                context="Update install",
                event_type="support.update.install_failed",
                message=msg,
            ),
            on_cancel=lambda: self._on_update_install_canceled(incident_id),
            set_busy=self._set_update_busy,
        )

    def _on_update_install_canceled(self, incident_id: str) -> None:
        self._append_result("Update install canceled.")
        self._emit_support_event(
            event_type="support.update.install_canceled",
            message="Update install canceled by user.",
            trace_id=incident_id,
        )

    def _run_prepared_update(self, prepared: PreparedUpdateLaunch, *, incident_id: str) -> None:
        self._append_result(f"Update installer ready: {prepared.installer_path}")
        confirm = QMessageBox.question(
            self,
            "Install Update",
            (
                "The app will now close, run the installer, then relaunch automatically.\n\n"
                "Proceed?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm != QMessageBox.Yes:
            self._append_result("Update install aborted before app shutdown.")
            self._emit_support_event(
                event_type="support.update.install_aborted",
                message="Update install aborted before shutdown.",
                trace_id=incident_id,
            )
            return

        try:
            launch_windows_update_handoff(prepared)
        except Exception as exc:  # noqa: BLE001
            self._handle_async_error(
                title="Update",
                context="Launch installer",
                event_type="support.update.handoff_failed",
                message=f"Failed to launch update installer: {exc}",
            )
            return

        self._emit_support_event(
            event_type="support.update.handoff_started",
            message="Update handoff launched; app will close.",
            trace_id=incident_id,
            data={"installer_path": str(prepared.installer_path)},
        )
        self._append_result("Closing app to apply update...")
        app = QApplication.instance()
        if app is not None:
            app.quit()


__all__ = ["SupportUpdateFlowMixin"]
