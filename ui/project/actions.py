from __future__ import annotations

from PySide6.QtWidgets import QDialog, QInputDialog, QMessageBox

from core.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from core.models import ProjectStatus
from ui.project.dialogs import ProjectEditDialog


class ProjectActionsMixin:
    def create_project(self):
        dlg = ProjectEditDialog(self)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._project_service.create_project(
                    name=dlg.name,
                    client_name=dlg.client_name,
                    client_contact=dlg.client_contact,
                    planned_budget=dlg.planned_budget,
                    currency=dlg.currency,
                    start_date=dlg.start_date,
                    end_date=dlg.end_date,
                    description=dlg.description,
                )
            except ValidationError as e:
                QMessageBox.warning(self, "Validation error", str(e))
                continue
            except (BusinessRuleError, NotFoundError, ConcurrencyError) as e:
                QMessageBox.warning(self, "Error", str(e))
                return
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                return
            self.reload_projects()
            return

    def edit_project(self):
        proj = self._get_selected_project()
        if not proj:
            QMessageBox.information(self, "Edit project", "Please select a project.")
            return

        dlg = ProjectEditDialog(self, project=proj)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._project_service.update_project(
                    project_id=proj.id,
                    name=dlg.name,
                    description=dlg.description,
                    client_name=dlg.client_name,
                    client_contact=dlg.client_contact,
                    planned_budget=dlg.planned_budget,
                    currency=dlg.currency,
                    status=dlg.status,
                    start_date=dlg.start_date,
                    end_date=dlg.end_date,
                )
            except ValidationError as e:
                QMessageBox.warning(self, "Error", str(e))
                continue
            except (BusinessRuleError, NotFoundError, ConcurrencyError) as e:
                QMessageBox.warning(self, "Error", str(e))
                return
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                return
            self.reload_projects()
            return

    def delete_project(self):
        proj = self._get_selected_project()
        if not proj:
            QMessageBox.information(self, "Delete project", "Please select a project.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm delete",
            f"Delete project '{proj.name}' and all its tasks, costs, etc.?",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self._project_service.delete_project(proj.id)
        except (BusinessRuleError, NotFoundError) as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.reload_projects()

    def update_project_status(self) -> None:
        proj = self._get_selected_project()
        if not proj:
            QMessageBox.information(self, "Project status", "Please select a project.")
            return

        statuses = [
            ProjectStatus.PLANNED,
            ProjectStatus.ACTIVE,
            ProjectStatus.ON_HOLD,
            ProjectStatus.COMPLETED,
        ]
        labels = [status.value.replace("_", " ").title() for status in statuses]
        current_status = getattr(proj.status, "value", str(proj.status))
        current_idx = 0
        for idx, status in enumerate(statuses):
            if status.value == current_status:
                current_idx = idx
                break

        selected_label, ok = QInputDialog.getItem(
            self,
            "Update Project Status",
            f"Status for '{proj.name}':",
            labels,
            current_idx,
            editable=False,
        )
        if not ok:
            return

        selected_status = statuses[labels.index(selected_label)]
        try:
            self._project_service.set_status(proj.id, selected_status)
        except (ValidationError, BusinessRuleError, NotFoundError, ConcurrencyError) as e:
            QMessageBox.warning(self, "Project status", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Project status", str(e))
            return
        self.reload_projects()


__all__ = ["ProjectActionsMixin"]
