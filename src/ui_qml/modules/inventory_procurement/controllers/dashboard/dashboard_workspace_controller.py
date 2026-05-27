from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    InventoryProcurementWorkspaceControllerBase,
    serialize_dashboard_overview_view_model,
    serialize_dashboard_section_view_models,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryDashboardWorkspacePresenter,
    InventoryProcurementWorkspacePresenter,
)

QML_IMPORT_NAME = "InventoryProcurement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Inventory workspace controllers are provided by the shell runtime.")
class InventoryProcurementDashboardWorkspaceController(
    InventoryProcurementWorkspaceControllerBase
):
    overviewChanged = Signal()
    contextLabelChanged = Signal()
    sectionsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: InventoryProcurementWorkspacePresenter | None = None,
        dashboard_workspace_presenter: InventoryDashboardWorkspacePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or InventoryProcurementWorkspacePresenter(
            "inventory_procurement.dashboard"
        )
        self._dashboard_workspace_presenter = (
            dashboard_workspace_presenter or InventoryDashboardWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._context_label = ""
        self._sections: list[dict[str, object]] = []
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property(str, notify=contextLabelChanged)
    def contextLabel(self) -> str:
        return self._context_label

    @Property("QVariantList", notify=sectionsChanged)
    def sections(self) -> list[dict[str, object]]:
        return self._sections

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
            snapshot = self._dashboard_workspace_presenter.build_workspace_state()
            self._set_overview(
                serialize_dashboard_overview_view_model(snapshot.overview)
            )
            self._set_context_label(snapshot.context_label)
            self._set_sections(
                serialize_dashboard_section_view_models(snapshot.sections)
            )
            self._set_empty_state(snapshot.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="inventory_procurement")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_context_label(self, context_label: str) -> None:
        if context_label == self._context_label:
            return
        self._context_label = context_label
        self.contextLabelChanged.emit()

    def _set_sections(self, sections: list[dict[str, object]]) -> None:
        if sections == self._sections:
            return
        self._sections = sections
        self.sectionsChanged.emit()


__all__ = ["InventoryProcurementDashboardWorkspaceController"]
