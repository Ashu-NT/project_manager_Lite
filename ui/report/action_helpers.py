from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from ui.shared.async_job import JobUiConfig, start_async_job
from ui.shared.incident_support import emit_error_event, message_with_incident
from ui.shared.worker_services import worker_service_scope


class ReportActionHelpersMixin:
    def _require_project(self, action_label: str) -> tuple[str, str] | None:
        project_id, project_name = self._current_project_id_and_name()
        if not project_id:
            QMessageBox.information(self, action_label, "Please select a project.")
            return None
        return project_id, (project_name or "project")

    def _open_dialog(self, action_label: str, error_title: str, dialog_factory) -> None:
        selected = self._require_project(action_label)
        if not selected:
            return
        project_id, project_name = selected
        try:
            dialog_factory(project_id, project_name).exec()
        except Exception as exc:
            QMessageBox.warning(self, error_title, f"Failed to show {error_title.lower()}: {exc}")

    def _export_file(
        self,
        *,
        action_label: str,
        save_title: str,
        file_suffix: str,
        file_filter: str,
        success_title: str,
        error_prefix: str,
        error_event_type: str,
        exporter,
        empty_hint: str | None = None,
    ) -> None:
        selected = self._require_project(action_label)
        if not selected:
            return
        project_id, project_name = selected
        path = self._choose_export_path(save_title, f"{project_name}_{file_suffix}", file_filter)
        if not path:
            return

        def _work(token, progress):
            token.raise_if_cancelled()
            progress(None, f"{success_title}: preparing...")
            with worker_service_scope(getattr(self, "_user_session", None)) as services:
                token.raise_if_cancelled()
                progress(None, f"{success_title}: generating file...")
                out_path = exporter(services, project_id, Path(path))
                token.raise_if_cancelled()
                return Path(out_path)

        def _on_success(exported_path: Path) -> None:
            if empty_hint and (not exported_path.exists() or exported_path.stat().st_size == 0):
                QMessageBox.information(self, success_title, empty_hint)
                return
            QMessageBox.information(self, success_title, f"{success_title} saved to:\n{exported_path}")

        def _on_error(msg: str) -> None:
            incident_id = emit_error_event(
                event_type=error_event_type,
                message=f"{error_prefix}.",
                parent=self,
                data={"project_id": project_id, "path": path, "error": msg},
            )
            QMessageBox.warning(self, "Error", message_with_incident(f"{error_prefix}: {msg}", incident_id))

        start_async_job(
            parent=self,
            ui=JobUiConfig(title=success_title, label=f"{success_title} in progress...", allow_retry=True),
            work=_work,
            on_success=_on_success,
            on_error=_on_error,
            on_cancel=lambda: QMessageBox.information(self, success_title, f"{success_title} canceled."),
        )

    def _choose_export_path(self, title: str, suggested_name: str, file_filter: str) -> str | None:
        sanitized_name = self._sanitize_filename(suggested_name)
        path, _ = QFileDialog.getSaveFileName(self, title, sanitized_name, file_filter)
        return path or None

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        sanitized = "".join("_" if c in invalid_chars else c for c in filename).strip().strip(".")
        return sanitized or "report"


__all__ = ["ReportActionHelpersMixin"]

