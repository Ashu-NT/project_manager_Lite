from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from infra.diagnostics import DiagnosticsBundleResult, build_diagnostics_bundle
from infra.operational_support import bind_trace_id
from infra.path import user_data_dir
from ui.shared.async_job import JobUiConfig, start_async_job


class SupportDiagnosticsExportMixin:
    def _set_diag_busy(self, busy: bool) -> None:
        self.btn_export_diagnostics.setEnabled(not busy)
        if hasattr(self, "btn_report_incident"):
            self.btn_report_incident.setEnabled(not busy)

    def _settings_snapshot(self) -> dict[str, object]:
        return {
            "theme_mode": self._settings_store.load_theme_mode(default_mode="light"),
            "governance_mode": self._settings_store.load_governance_mode(default_mode="off"),
            "update_channel": self._settings_store.load_update_channel(default_channel="stable"),
            "update_auto_check": self._settings_store.load_update_auto_check(default_enabled=False),
            "update_manifest_url": self._settings_store.load_update_manifest_url(default_url=""),
        }

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

        incident_id = self._current_incident_id()
        self._emit_support_event(
            event_type="support.diagnostics.export_started",
            message="Started diagnostics export.",
            trace_id=incident_id,
            data={"output_path": output_path},
        )

        def _work(token, progress):
            with bind_trace_id(incident_id):
                token.raise_if_cancelled()
                progress(None, "Collecting logs and metadata...")
                result = build_diagnostics_bundle(
                    output_path=Path(output_path),
                    settings_snapshot=self._settings_snapshot(),
                    include_db_copy=True,
                    incident_id=incident_id,
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
            on_success=lambda result: self._handle_diagnostics_result(result, incident_id=incident_id),
            on_error=lambda msg: self._handle_async_error(
                title="Diagnostics",
                context="Diagnostics export",
                event_type="support.diagnostics.export_failed",
                message=msg,
            ),
            on_cancel=lambda: self._on_diagnostics_export_canceled(incident_id),
            set_busy=self._set_diag_busy,
        )

    def _on_diagnostics_export_canceled(self, incident_id: str) -> None:
        self._append_result("Diagnostics export canceled.")
        self._emit_support_event(
            event_type="support.diagnostics.export_canceled",
            message="Diagnostics export canceled by user.",
            trace_id=incident_id,
        )

    def _handle_diagnostics_result(
        self,
        result: DiagnosticsBundleResult,
        *,
        incident_id: str,
    ) -> None:
        notes = "\n".join(result.warnings) if result.warnings else "No warnings."
        self._append_result(
            f"Diagnostics bundle created: {result.output_path} | files={result.files_added} | {notes}"
        )
        self._emit_support_event(
            event_type="support.diagnostics.exported",
            message="Diagnostics bundle exported.",
            trace_id=incident_id,
            data={
                "output_path": str(result.output_path),
                "files_added": result.files_added,
                "warnings": list(result.warnings),
            },
        )
        QMessageBox.information(
            self,
            "Diagnostics",
            f"Diagnostics bundle saved to:\n{result.output_path}",
        )


__all__ = ["SupportDiagnosticsExportMixin"]
