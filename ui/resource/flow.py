from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QTableView

from core.models import Resource
from core.services.resource import ResourceService
from ui.resource.models import ResourceTableModel


class ResourceFlowMixin:
    _resource_service: ResourceService
    model: ResourceTableModel
    table: QTableView

    def reload_resources(self) -> None:
        resources = self._resource_service.list_resources()
        self.model.set_resources(resources)

    def _get_selected_resource(self) -> Optional[Resource]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model.get_resource(row)


__all__ = ["ResourceFlowMixin"]
