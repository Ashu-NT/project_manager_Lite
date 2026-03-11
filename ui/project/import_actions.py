from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from core.services.import_service import DataImportService
from ui.project.import_wizard import ImportWizardDialog


class ProjectImportActionsMixin:
    _data_import_service: DataImportService

    def import_csv_data(self) -> None:
        try:
            dialog = ImportWizardDialog(self, data_import_service=self._data_import_service)
        except Exception as exc:
            QMessageBox.critical(self, "Import Wizard", str(exc))
            return
        dialog.exec()


__all__ = ["ProjectImportActionsMixin"]
