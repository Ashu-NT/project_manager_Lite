from __future__ import annotations

from PySide6.QtWidgets import QDialog, QMessageBox

from core.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from core.services.resource import ResourceService
from ui.resource.dialogs import ResourceEditDialog


class ResourceActionsMixin:
    _resource_service: ResourceService

    def create_resource(self) -> None:
        dlg = ResourceEditDialog(self, resource=None)
        if dlg.exec() != QDialog.Accepted:
            return

        try:
            self._resource_service.create_resource(
                name=dlg.name,
                role=dlg.role,
                hourly_rate=dlg.hourly_rate,
                is_active=dlg.is_active,
                cost_type=dlg.cost_type,
                currency_code=dlg.currency_code,
            )
        except ValidationError as e:
            QMessageBox.warning(self, "Validation error", str(e))
            return
        except (BusinessRuleError, NotFoundError, ConcurrencyError) as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.reload_resources()

    def edit_resource(self) -> None:
        resource = self._get_selected_resource()
        if not resource:
            QMessageBox.information(self, "Edit resource", "Please select a resource.")
            return

        dlg = ResourceEditDialog(self, resource=resource)
        if dlg.exec() != QDialog.Accepted:
            return

        try:
            self._resource_service.update_resource(
                resource_id=resource.id,
                name=dlg.name,
                role=dlg.role,
                hourly_rate=dlg.hourly_rate,
                is_active=dlg.is_active,
                cost_type=dlg.cost_type,
                currency_code=dlg.currency_code,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.reload_resources()

    def delete_resource(self) -> None:
        resource = self._get_selected_resource()
        if not resource:
            QMessageBox.information(self, "Delete resource", "Please select a resource.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete resource",
            f"Delete resource '{resource.name}'? (Assignments may fail if still referenced.)",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self._resource_service.delete_resource(resource.id)
        except (BusinessRuleError, NotFoundError) as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.reload_resources()

    def toggle_active(self) -> None:
        resource = self._get_selected_resource()
        if not resource:
            QMessageBox.information(self, "Toggle active", "Please select a resource.")
            return

        try:
            self._resource_service.update_resource(
                resource_id=resource.id,
                is_active=not getattr(resource, "is_active", True),
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.reload_resources()


__all__ = ["ResourceActionsMixin"]
