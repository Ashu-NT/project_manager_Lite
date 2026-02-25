from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QDialog, QMessageBox

from core.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from core.models import CostItem, Project, Task
from core.services.cost import CostService
from ui.cost.cost_dialogs import CostEditDialog
from ui.cost.error_handling import show_cost_business_rule
from ui.cost.models import CostTableModel


class CostActionsMixin:
    _cost_service: CostService
    model: CostTableModel
    _current_project: Project | None
    _project_tasks: list[Task]

    def _get_selected_cost(self) -> Optional[CostItem]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        return self.model.get_cost(indexes[0].row())

    def create_cost_item(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "New cost item", "Please select a project.")
            return

        dlg = CostEditDialog(
            self,
            project=self._current_project,
            tasks=self._project_tasks,
            cost_item=None,
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._cost_service.add_cost_item(
                    project_id=pid,
                    description=dlg.description,
                    task_id=dlg.task_id,
                    planned_amount=dlg.planned_amount,
                    committed_amount=dlg.committed_amount,
                    actual_amount=dlg.actual_amount,
                    cost_type=dlg.cost_type,
                    incurred_date=dlg.incurred_date_value,
                    currency_code=dlg.currency_code,
                )
            except ValidationError as e:
                QMessageBox.warning(self, "Validation error", str(e))
                continue
            except NotFoundError as e:
                QMessageBox.warning(self, "Error", str(e))
                continue
            except BusinessRuleError as e:
                show_cost_business_rule(self, e)
                self.reload_costs()
                return
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                return

            self.reload_costs()
            return

    def edit_cost_item(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "Edit cost item", "Please select a project.")
            return
        item = self._get_selected_cost()
        if not item:
            QMessageBox.information(self, "Edit cost item", "Please select a cost item.")
            return

        dlg = CostEditDialog(
            self,
            project=self._current_project,
            tasks=self._project_tasks,
            cost_item=item,
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._cost_service.update_cost_item(
                    cost_id=item.id,
                    actual_amount=dlg.actual_amount,
                    description=dlg.description,
                    planned_amount=dlg.planned_amount,
                    committed_amount=dlg.committed_amount,
                    cost_type=dlg.cost_type,
                    incurred_date=dlg.incurred_date_value,
                    currency_code=dlg.currency_code,
                )
            except (ValidationError, NotFoundError, ConcurrencyError) as e:
                QMessageBox.warning(self, "Error", str(e))
                continue
            except BusinessRuleError as e:
                show_cost_business_rule(self, e)
                self.reload_costs()
                return
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                return

            self.reload_costs()
            return

    def delete_cost_item(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "Delete cost item", "Please select a project.")
            return
        item = self._get_selected_cost()
        if not item:
            QMessageBox.information(self, "Delete cost item", "Please select a cost item.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm delete",
            f"Delete cost item '{item.description}'?",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self._cost_service.delete_cost_item(item.id)
        except NotFoundError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        except BusinessRuleError as e:
            show_cost_business_rule(self, e)
            self.reload_costs()
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.reload_costs()
