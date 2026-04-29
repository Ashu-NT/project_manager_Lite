from __future__ import annotations

import tempfile
import time
from contextlib import suppress
from pathlib import Path

from PySide6.QtGui import QPixmap

from src.core.modules.project_management.infrastructure.reporting.api import generate_gantt_png
from src.ui.shared.dialogs.async_job import JobUiConfig, start_async_job
from src.ui.shared.models.worker_services import service_uses_in_memory_sqlite, worker_service_scope


def load_gantt_image(dialog) -> None:
    if dialog._load_inflight:
        dialog._load_pending = True
        return

    def _set_busy(busy: bool) -> None:
        dialog._load_inflight = busy
        dialog.btn_refresh.setEnabled(not busy)
        dialog.btn_open_interactive.setEnabled(not busy and dialog._can_open_interactive)
        if busy and dialog._raw_pixmap.isNull():
            dialog.image_label.setText("Generating Gantt preview...")
            dialog.meta_label.setText("Loading schedule data...")
        if not busy and dialog._load_pending:
            dialog._load_pending = False
            dialog._load_image()

    def _work(token, progress):
        token.raise_if_cancelled()
        progress(None, "Generating Gantt preview...")
        with worker_service_scope(getattr(dialog._reporting_service, "_user_session", None)) as services:
            return load_preview_payload(dialog, services["reporting_service"])

    def _on_success(result) -> None:
        out_path = Path(result["path"])
        pixmap = QPixmap()
        pixmap.load(str(out_path))
        with suppress(FileNotFoundError, PermissionError, OSError):
            out_path.unlink()
        if pixmap.isNull():
            _apply_preview_error(dialog, "Unable to load Gantt image.", timeline_error="Unable to load Gantt image.")
            return
        dialog._raw_pixmap = pixmap
        dialog._gantt_bars = list(result.get("bars") or [])
        update_gantt_meta(dialog, dialog._gantt_bars)
        dialog._render_preview()
        dialog._build_interactive_timeline()

    def _on_error(message: str) -> None:
        _apply_preview_error(dialog, f"Error generating Gantt: {message}", timeline_error=message)

    if service_uses_in_memory_sqlite(dialog._reporting_service):
        _set_busy(True)
        try:
            _on_success(load_preview_payload(dialog, dialog._reporting_service))
        except Exception as exc:
            _on_error(str(exc))
        finally:
            _set_busy(False)
        return

    start_async_job(
        parent=dialog,
        ui=JobUiConfig(
            title="Gantt Preview",
            label="Generating Gantt preview...",
            allow_retry=True,
            show_progress=False,
        ),
        work=_work,
        on_success=_on_success,
        on_error=_on_error,
        on_cancel=lambda: None,
        set_busy=_set_busy,
    )


def update_gantt_meta(dialog, bars) -> None:
    dated = [bar for bar in bars if bar.start and bar.end]
    critical_count = sum(1 for bar in dated if bar.is_critical)
    if dated:
        timeline_start = min(bar.start for bar in dated if bar.start)
        timeline_end = max(bar.end for bar in dated if bar.end)
        dialog.meta_label.setText(
            f"Tasks: {len(dated)} scheduled | Critical: {critical_count} | "
            f"Timeline: {timeline_start.isoformat()} to {timeline_end.isoformat()}"
        )
        return
    dialog.meta_label.setText("No scheduled tasks with valid dates.")


def load_preview_payload(dialog, reporting_service):
    tmpdir = Path(tempfile.gettempdir()) / "pm_gantt_preview"
    tmpdir.mkdir(parents=True, exist_ok=True)
    out_path = tmpdir / f"gantt_{dialog._project_id}_{int(time.time() * 1000)}.png"
    bars = reporting_service.get_gantt_data(dialog._project_id)
    generate_gantt_png(reporting_service, dialog._project_id, out_path, bars=bars)
    return {"path": out_path, "bars": bars}


def _apply_preview_error(dialog, label_text: str, *, timeline_error: str) -> None:
    dialog._raw_pixmap = QPixmap()
    dialog._gantt_bars = []
    dialog.meta_label.setText("")
    dialog.image_label.setText(label_text)
    dialog._build_interactive_timeline(error_text=timeline_error)


__all__ = ["load_gantt_image"]

