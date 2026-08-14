from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.core.shared.events.domain_events import DomainChangeEvent, domain_events

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("PM project context is provided by the PM catalog.")
class PMProjectContextController(QObject):
    activeProjectChanged = Signal()
    projectOptionsChanged = Signal()
    validationStateChanged = Signal()
    projectOpenRequested = Signal(str, str)

    def __init__(
        self,
        *,
        projects_api: Any | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._projects_api = projects_api
        self._active_project_id = ""
        self._active_project_label = ""
        self._project_options: list[dict[str, str]] = []
        self._validation_status = "unavailable" if projects_api is None else "ready"
        self._error_message = ""
   
        domain_events.domain_changed.connect(self._on_domain_changed)
        if projects_api is not None:
            self.refreshProjects()

    def _on_domain_changed(self, event: DomainChangeEvent) -> None:
        if event.scope_code == "project_management" and event.entity_type == "project":
            self.refreshProjects()

    @Property(str, notify=activeProjectChanged)
    def activeProjectId(self) -> str:
        return self._active_project_id

    @Property(str, notify=activeProjectChanged)
    def activeProjectLabel(self) -> str:
        return self._active_project_label

    @Property(bool, notify=activeProjectChanged)
    def hasActiveProject(self) -> bool:
        return bool(self._active_project_id)

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> list[dict[str, str]]:
        return self._project_options

    @Property(str, notify=validationStateChanged)
    def validationStatus(self) -> str:
        return self._validation_status

    @Property(str, notify=validationStateChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Slot()
    def refreshProjects(self) -> None:
        self._load_project_options("")
        self.revalidate()

    @Slot(str)
    def searchProjects(self, search_text: str) -> None:
        self._load_project_options(str(search_text or "").strip())

    @Slot(str, result=bool)
    def selectProject(self, project_id: str) -> bool:
        project = self._read_project(project_id)
        if project is None:
            self._set_validation_state(
                "stale",
                "The selected project is unavailable in the active organization.",
            )
            return False
        self._set_active_project(project)
        self._set_validation_state("ready", "")
        return True

    @Slot()
    def clearProject(self) -> None:
        self._clear_active_project()
        self._set_validation_state(
            "unavailable" if self._projects_api is None else "ready",
            "",
        )

    @Slot(str, str, result=bool)
    def openProject(self, project_id: str, source_route: str) -> bool:
        project = self._read_project(project_id)
        if project is None:
            self._set_validation_state(
                "stale",
                "The requested project is unavailable in the active organization.",
            )
            return False
        self.projectOpenRequested.emit(
            str(getattr(project, "id", "") or ""),
            str(source_route or "").strip(),
        )
        self._set_validation_state("ready", "")
        return True

    @Slot()
    def resetContext(self) -> None:
        self._clear_active_project()
        self._project_options = []
        self.projectOptionsChanged.emit()
        self.refreshProjects()

    @Slot(result=bool)
    def revalidate(self) -> bool:
        if not self._active_project_id:
            return True
        project = self._read_project(self._active_project_id)
        if project is None:
            self._clear_active_project()
            self._set_validation_state(
                "stale",
                "The active project is no longer available in this scope.",
            )
            return False
        self._set_active_project(project)
        self._set_validation_state("ready", "")
        return True

    def _load_project_options(self, search_text: str) -> None:
        if self._projects_api is None:
            self._set_project_options([])
            self._set_validation_state("unavailable", "")
            return
        try:
            page = self._projects_api.list_project_page(
                search_text=search_text,
                status="all",
                page=1,
                page_size=100,
                sort_key="title",
                sort_direction="asc",
            )
            options = [self._serialize_project_option(project) for project in page.items]
            self._set_project_options(options)
            self._set_validation_state("ready", "")
        except Exception:
            self._set_project_options([])
            self._set_validation_state(
                "error",
                "Project context could not be refreshed.",
            )

    def _read_project(self, project_id: str):
        normalized = str(project_id or "").strip()
        if not normalized or self._projects_api is None:
            return None
        try:
            return self._projects_api.get_project(normalized)
        except Exception:
            self._set_validation_state(
                "error",
                "Project context could not be validated.",
            )
            return None

    def _set_active_project(self, project: Any) -> None:
        project_id = str(getattr(project, "id", "") or "").strip()
        project_label = str(getattr(project, "name", "") or "").strip()
        if (
            project_id == self._active_project_id
            and project_label == self._active_project_label
        ):
            return
        self._active_project_id = project_id
        self._active_project_label = project_label
        self.activeProjectChanged.emit()

    def _clear_active_project(self) -> None:
        if not self._active_project_id and not self._active_project_label:
            return
        self._active_project_id = ""
        self._active_project_label = ""
        self.activeProjectChanged.emit()

    def _set_project_options(self, options: list[dict[str, str]]) -> None:
        if options == self._project_options:
            return
        self._project_options = options
        self.projectOptionsChanged.emit()

    def _set_validation_state(self, status: str, error_message: str) -> None:
        if status == self._validation_status and error_message == self._error_message:
            return
        self._validation_status = status
        self._error_message = error_message
        self.validationStateChanged.emit()

    @staticmethod
    def _serialize_project_option(project: Any) -> dict[str, str]:
        return {
            "id": str(getattr(project, "id", "") or ""),
            "label": str(getattr(project, "name", "") or ""),
            "code": str(getattr(project, "code", "") or ""),
            "statusLabel": str(getattr(project, "status_label", "") or ""),
        }


__all__ = ["PMProjectContextController"]
