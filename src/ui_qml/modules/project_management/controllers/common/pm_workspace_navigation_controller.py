from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.navigation import (
    PM_CANONICAL_ROUTE_ID,
    PM_WORKSPACE_KEYS,
    compatibility_route_intent,
    workspace_intent,
)

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("PM workspace navigation is provided by the PM catalog.")
class PMWorkspaceNavigationController(QObject):
    selectionChanged = Signal()
    routeStateChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workspace_key = "dashboard"
        self._entity_id = ""
        self._section_id = ""

    @Property(str, notify=selectionChanged)
    def workspaceKey(self) -> str:
        return self._workspace_key

    @Property(str, notify=selectionChanged)
    def destinationId(self) -> str:
        intent = workspace_intent(self._workspace_key)
        return intent.destination_id if intent is not None else "overview"

    @Property(str, notify=selectionChanged)
    def secondaryId(self) -> str:
        intent = workspace_intent(self._workspace_key)
        return intent.secondary_id if intent is not None else ""

    @Property("QVariantMap", notify=routeStateChanged)
    def routeState(self) -> dict[str, str]:
        return {
            "routeId": PM_CANONICAL_ROUTE_ID,
            "destination": self.destinationId,
            "workspaceKey": self._workspace_key,
            "secondary": self.secondaryId,
            "entityId": self._entity_id,
            "section": self._section_id,
        }

    @Property("QVariantList", constant=True)
    def navigationItems(self) -> list[dict[str, str]]:
        return [
            {"id": "dashboard", "label": "Dashboard", "group": "Overview", "icon": "dashboard"},
            {"id": "portfolio", "label": "Portfolio", "group": "Portfolio", "icon": "portfolio"},
            {"id": "projects", "label": "Projects", "group": "Work", "icon": "project"},
            {"id": "tasks", "label": "Tasks", "group": "Work", "icon": "task"},
            {"id": "scheduling", "label": "Planning", "group": "Work", "icon": "calendar"},
            {"id": "resources", "label": "Resources", "group": "People & Time", "icon": "resource"},
            {"id": "timesheets", "label": "Review Queue", "group": "People & Time", "icon": "time"},
            {"id": "financials", "label": "Finance", "group": "Finance", "icon": "finance"},
            {"id": "register", "label": "Register", "group": "Governance", "icon": "register"},
            {"id": "collaboration", "label": "Collaboration", "group": "Governance", "icon": "collaboration"},
        ]

    @Slot(str, result=bool)
    def applyRoute(self, route_id: str) -> bool:
        normalized = str(route_id or "").strip()
        if normalized == PM_CANONICAL_ROUTE_ID:
            return True
        intent = compatibility_route_intent(normalized)
        if intent is None:
            return False
        return self.selectWorkspace(intent.workspace_key)

    @Slot(str, result=bool)
    def selectWorkspace(self, workspace_key: str) -> bool:
        normalized = str(workspace_key or "").strip()
        if normalized not in PM_WORKSPACE_KEYS:
            return False
        selection_changed = normalized != self._workspace_key
        route_state_changed = bool(self._entity_id or self._section_id)
        self._workspace_key = normalized
        self._entity_id = ""
        self._section_id = ""
        if selection_changed:
            self.selectionChanged.emit()
        if selection_changed or route_state_changed:
            self.routeStateChanged.emit()
        return True

    @Slot(str, str, str, result=bool)
    def openEntity(
        self,
        workspace_key: str,
        entity_id: str,
        section_id: str = "",
    ) -> bool:
        if not self.selectWorkspace(workspace_key):
            return False
        normalized_entity_id = str(entity_id or "").strip()
        normalized_section_id = str(section_id or "").strip()
        if (
            normalized_entity_id == self._entity_id
            and normalized_section_id == self._section_id
        ):
            return True
        self._entity_id = normalized_entity_id
        self._section_id = normalized_section_id
        self.routeStateChanged.emit()
        return True


__all__ = ["PMWorkspaceNavigationController"]
