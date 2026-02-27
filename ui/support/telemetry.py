from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox

from infra.operational_support import bind_trace_id
from infra.path import user_data_dir


class SupportTelemetryMixin:
    def _current_incident_id(self) -> str:
        value = self.incident_id_input.text().strip()
        if value:
            return value
        value = self._ops_support.new_incident_id()
        self.incident_id_input.setText(value)
        return value

    def _new_incident_id(self) -> None:
        incident = self._ops_support.new_incident_id()
        self.incident_id_input.setText(incident)
        self._append_result(f"New incident trace ID: {incident}")
        self._emit_support_event(
            event_type="support.incident.renewed",
            message="Created new incident trace ID.",
            trace_id=incident,
        )

    def _copy_incident_id(self) -> None:
        incident = self._current_incident_id()
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(incident)
        self._append_result(f"Copied incident ID: {incident}")

    def _emit_support_event(
        self,
        *,
        event_type: str,
        message: str,
        level: str = "INFO",
        data: Mapping[str, object] | None = None,
        trace_id: str | None = None,
    ) -> str:
        resolved_trace = (trace_id or self._current_incident_id()).strip()
        try:
            with bind_trace_id(resolved_trace):
                return self._ops_support.emit_event(
                    event_type=event_type,
                    level=level,
                    message=message,
                    trace_id=resolved_trace,
                    data=data,
                )
        except Exception:
            return resolved_trace

    def _handle_async_error(
        self,
        *,
        title: str,
        context: str,
        event_type: str,
        message: str,
    ) -> None:
        text = (message or "Operation failed.").strip()
        self._append_result(f"{context} failed: {text}")
        self._emit_support_event(
            event_type=event_type,
            level="ERROR",
            message=f"{context} failed.",
            data={"error": text},
        )
        QMessageBox.warning(self, title, text)

    def _open_logs_folder(self) -> None:
        target = user_data_dir() / "logs"
        self._emit_support_event(
            event_type="support.logs.opened",
            message="Opened logs folder.",
            data={"path": str(target)},
        )
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _open_data_folder(self) -> None:
        target = user_data_dir()
        self._emit_support_event(
            event_type="support.data.opened",
            message="Opened app data folder.",
            data={"path": str(target)},
        )
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _append_result(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.result_box.append(f"[{stamp}] {text}")


__all__ = ["SupportTelemetryMixin"]
