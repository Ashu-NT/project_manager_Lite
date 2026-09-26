from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.context_navigation import (
    build_pm_context_navigation,
)
from src.ui_qml.modules.project_management.navigation import (
    PM_CANONICAL_ROUTE_ID,
    PM_WORKSPACE_KEYS,
    compatibility_route_intent,
    workspace_intent,
)
from src.ui_qml.shell.context_navigation import (
    filter_context_navigation,
    resolve_breadcrumb,
    resolve_safe_context_destination,
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
    def contextNavigation(self) -> list[dict[str, object]]:
        return build_pm_context_navigation().to_qml_groups()

    @Property("QVariantList", notify=selectionChanged)
    def breadcrumb(self) -> list[str]:
        return resolve_breadcrumb(
            workspace_title="Project Management",
            tree=build_pm_context_navigation(),
            current_id=self._workspace_key,
        )

    @Slot("QVariantList")
    def refreshContextAvailability(self, accessible_workspace_keys) -> None:
        """Re-validate the current workspace selection against a filtered
        set of accessible workspace keys, redirecting to a safe destination
        when the current one is no longer present. PM's context navigation
        is not filtered by permissions today, so nothing calls this yet --
        it exists so a future Level-2 PM accessibility source can plug in
        through the same redirect contract Platform already uses."""
        accessible_ids = frozenset(str(key) for key in (accessible_workspace_keys or []))
        if not accessible_ids:
            return
        filtered = filter_context_navigation(build_pm_context_navigation(), accessible_ids)
        safe_key = resolve_safe_context_destination(
            self._workspace_key, filtered, preferred_id="dashboard"
        )
        if safe_key != self._workspace_key:
            self.selectWorkspace(safe_key)

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
