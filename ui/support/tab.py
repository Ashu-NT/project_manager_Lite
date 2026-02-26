from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.services.auth import UserSessionContext
from infra.diagnostics import DiagnosticsBundleResult, build_diagnostics_bundle
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
from ui.settings import MainWindowSettingsStore
from ui.shared.async_job import JobUiConfig, start_async_job
from ui.shared.guards import make_guarded_slot
from ui.styles.ui_config import UIConfig as CFG


class SupportTab(QWidget):
    def __init__(
        self,
        *,
        settings_store: MainWindowSettingsStore,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._settings_store = settings_store
        self._user_session = user_session
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        root.setSpacing(CFG.SPACING_MD)

        title = QLabel("Support & Updates")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Admin tooling for release checks, diagnostics export, and runtime troubleshooting."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        update_group = QGroupBox("Release Channel")
        update_group.setFont(CFG.GROUPBOX_TITLE_FONT)
        update_form = QFormLayout(update_group)
        update_form.setSpacing(CFG.SPACING_SM)

        self.channel_combo = QComboBox()
        self.channel_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.channel_combo.addItem("Stable", userData="stable")
        self.channel_combo.addItem("Beta", userData="beta")

        self.auto_check = QCheckBox("Check for updates automatically at startup")
        self.manifest_url = QLineEdit()
        self.manifest_url.setPlaceholderText("Manifest URL or local file path")
        self.manifest_url.setMinimumHeight(CFG.INPUT_HEIGHT)

        update_form.addRow("Channel:", self.channel_combo)
        update_form.addRow("Manifest source:", self.manifest_url)
        update_form.addRow("", self.auto_check)

        update_buttons = QHBoxLayout()
        self.btn_save_update_settings = QPushButton("Save Update Settings")
        self.btn_check_updates = QPushButton("Check for Updates")
        for btn in (self.btn_save_update_settings, self.btn_check_updates):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            update_buttons.addWidget(btn)
        update_buttons.addStretch()
        update_form.addRow(update_buttons)
        root.addWidget(update_group)

        diag_group = QGroupBox("Diagnostics")
        diag_group.setFont(CFG.GROUPBOX_TITLE_FONT)
        diag_layout = QVBoxLayout(diag_group)
        diag_layout.setSpacing(CFG.SPACING_SM)

        diag_hint = QLabel(
            "Build a diagnostics zip with metadata, logs, and optional DB snapshot for support triage."
        )
        diag_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        diag_hint.setWordWrap(True)
        diag_layout.addWidget(diag_hint)

        diag_buttons = QHBoxLayout()
        self.btn_export_diagnostics = QPushButton("Export Diagnostics Bundle")
        self.btn_open_logs = QPushButton("Open Logs Folder")
        self.btn_open_data = QPushButton("Open Data Folder")
        for btn in (self.btn_export_diagnostics, self.btn_open_logs, self.btn_open_data):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            diag_buttons.addWidget(btn)
        diag_buttons.addStretch()
        diag_layout.addLayout(diag_buttons)
        root.addWidget(diag_group)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setMinimumHeight(220)
        self.result_box.setPlaceholderText("Support activity and update check results appear here.")
        root.addWidget(self.result_box, 1)

        self.btn_save_update_settings.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._save_update_settings)
        )
        self.btn_check_updates.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._check_updates)
        )
        self.btn_export_diagnostics.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._export_diagnostics)
        )
        self.btn_open_logs.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._open_logs_folder)
        )
        self.btn_open_data.clicked.connect(
            make_guarded_slot(self, title="Support", callback=self._open_data_folder)
        )

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
        if show_feedback:
            QMessageBox.information(self, "Support", "Update settings saved.")

    def _set_update_busy(self, busy: bool) -> None:
        self.btn_check_updates.setEnabled(not busy)
        self.btn_save_update_settings.setEnabled(not busy)

    def _set_diag_busy(self, busy: bool) -> None:
        self.btn_export_diagnostics.setEnabled(not busy)

    def _check_updates(self) -> None:
        self._save_update_settings(show_feedback=False)
        channel = self._settings_store.load_update_channel(default_channel="stable")
        manifest = self._settings_store.load_update_manifest_url(
            default_url=default_update_manifest_source()
        )
        if not manifest:
            QMessageBox.information(self, "Support", "Set a manifest source before checking for updates.")
            return

        def _work(token, progress):
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
            on_success=self._handle_update_result,
            on_error=lambda msg: QMessageBox.warning(self, "Support", msg),
            on_cancel=lambda: self._append_result("Update check canceled."),
            set_busy=self._set_update_busy,
        )

    def _handle_update_result(self, result: UpdateCheckResult) -> None:
        self._append_result(result.message)
        if not result.update_available or result.latest is None:
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
                self._download_and_install_update(result)
            elif clicked == open_button:
                QDesktopServices.openUrl(QUrl(result.latest.url))

    def _resolve_relaunch_command(self) -> tuple[str, list[str]]:
        if bool(getattr(sys, "frozen", False)):
            return str(sys.executable), []
        project_root = Path(__file__).resolve().parents[2]
        entry = project_root / "main_qt.py"
        return str(sys.executable), [str(entry)]

    def _download_and_install_update(self, result: UpdateCheckResult) -> None:
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
            QDesktopServices.openUrl(QUrl(latest.url))
            return

        updates_dir = user_data_dir() / "updates"
        app_pid = os.getpid()

        def _work(token, progress):
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
            on_success=self._run_prepared_update,
            on_error=lambda msg: QMessageBox.warning(self, "Update", msg),
            on_cancel=lambda: self._append_result("Update install canceled."),
            set_busy=self._set_update_busy,
        )

    def _run_prepared_update(self, prepared: PreparedUpdateLaunch) -> None:
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
            return

        try:
            launch_windows_update_handoff(prepared)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Update", f"Failed to launch update installer: {exc}")
            return

        self._append_result("Closing app to apply update...")
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _export_diagnostics(self) -> None:
        default_name = f"pm_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save diagnostics bundle",
            str(user_data_dir() / default_name),
            "Zip archive (*.zip)",
        )
        if not output_path:
            return

        settings_snapshot = {
            "theme_mode": self._settings_store.load_theme_mode(default_mode="light"),
            "governance_mode": self._settings_store.load_governance_mode(default_mode="off"),
            "update_channel": self._settings_store.load_update_channel(default_channel="stable"),
            "update_auto_check": self._settings_store.load_update_auto_check(default_enabled=False),
            "update_manifest_url": self._settings_store.load_update_manifest_url(default_url=""),
        }

        def _work(token, progress):
            token.raise_if_cancelled()
            progress(None, "Collecting logs and metadata...")
            result = build_diagnostics_bundle(
                output_path=Path(output_path),
                settings_snapshot=settings_snapshot,
                include_db_copy=True,
            )
            token.raise_if_cancelled()
            return result

        start_async_job(
            parent=self,
            ui=JobUiConfig(
                title="Diagnostics",
                label="Building diagnostics bundle...",
                allow_retry=True,
            ),
            work=_work,
            on_success=self._handle_diagnostics_result,
            on_error=lambda msg: QMessageBox.warning(self, "Diagnostics", msg),
            on_cancel=lambda: self._append_result("Diagnostics export canceled."),
            set_busy=self._set_diag_busy,
        )

    def _handle_diagnostics_result(self, result: DiagnosticsBundleResult) -> None:
        notes = "\n".join(result.warnings) if result.warnings else "No warnings."
        self._append_result(
            f"Diagnostics bundle created: {result.output_path} | files={result.files_added} | {notes}"
        )
        QMessageBox.information(
            self,
            "Diagnostics",
            f"Diagnostics bundle saved to:\n{result.output_path}",
        )

    def _open_logs_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(user_data_dir() / "logs")))

    def _open_data_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(user_data_dir())))

    def _append_result(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.result_box.append(f"[{stamp}] {text}")


__all__ = ["SupportTab"]
