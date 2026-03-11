from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from core.services.import_service import DataImportService


class ProjectImportActionsMixin:
    _data_import_service: DataImportService

    def import_csv_data(self) -> None:
        options = {
            "Projects": "projects",
            "Resources": "resources",
            "Tasks": "tasks",
            "Costs": "costs",
        }
        label, ok = QInputDialog.getItem(
            self,
            "Import CSV",
            "Import type:",
            list(options.keys()),
            0,
            editable=False,
        )
        if not ok or not label:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Import {label}",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        if not file_path:
            return

        try:
            summary = self._data_import_service.import_csv(options[label], Path(file_path))
        except Exception as exc:
            QMessageBox.critical(self, "Import CSV", str(exc))
            return

        details = [
            f"Created: {summary.created_count}",
            f"Updated: {summary.updated_count}",
            f"Errors: {summary.error_count}",
        ]
        if summary.error_rows:
            details.append("")
            details.append("First errors:")
            details.extend(summary.error_rows[:8])

        QMessageBox.information(
            self,
            "Import CSV",
            "\n".join(details),
        )


__all__ = ["ProjectImportActionsMixin"]
