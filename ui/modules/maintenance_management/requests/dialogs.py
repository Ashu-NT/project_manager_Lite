from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QTableWidgetItem, QVBoxLayout, QWidget

from core.modules.maintenance_management import MaintenanceWorkOrderService, MaintenanceWorkRequestService
from ui.modules.maintenance_management.shared import MaintenanceWorkbenchNavigator, MaintenanceWorkbenchSection, format_timestamp
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class MaintenanceRequestDetailDialog(QDialog):
    def __init__(
        self,
        *,
        work_request_service: MaintenanceWorkRequestService,
        work_order_service: MaintenanceWorkOrderService,
        site_labels: dict[str, str],
        asset_labels: dict[str, str],
        location_labels: dict[str, str],
        system_labels: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._work_request_service = work_request_service
        self._work_order_service = work_order_service
        self._site_labels = site_labels
        self._asset_labels = asset_labels
        self._location_labels = location_labels
        self._system_labels = system_labels

        self.setWindowTitle("Request Detail")
        self.resize(980, 680)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        root.setSpacing(CFG.SPACING_MD)

        self.title_label = QLabel("No request selected")
        self.title_label.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        root.addWidget(self.title_label)

        self.workbench = MaintenanceWorkbenchNavigator(object_name="maintenanceRequestDetailWorkbench", parent=self)
        self.overview_widget, self.overview_summary = self._build_overview_widget()
        self.orders_widget, self.linked_orders_table = self._build_orders_widget()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(key="overview", label="Overview", widget=self.overview_widget),
                MaintenanceWorkbenchSection(key="linked_orders", label="Linked Work Orders", widget=self.orders_widget),
            ],
            initial_key="overview",
        )
        root.addWidget(self.workbench, 1)

    def load_request(self, request_id: str) -> None:
        request = self._work_request_service.get_work_request(request_id)
        related_orders = [
            row
            for row in self._work_order_service.list_work_orders(site_id=request.site_id)
            if row.source_type == "WORK_REQUEST" and row.source_id == request.id
        ]
        self.title_label.setText(f"{request.work_request_code} - {request.title or request.request_type.title()}")
        self.overview_summary.setText(
            "\n".join(
                [
                    f"Type: {request.request_type.title()} | Status: {request.status.value.title()} | Priority: {request.priority.value.title()}",
                    f"Site: {self._site_labels.get(request.site_id, request.site_id)}",
                    f"Asset: {self._label_for(self._asset_labels, request.asset_id)} | System: {self._label_for(self._system_labels, request.system_id)}",
                    f"Location: {self._label_for(self._location_labels, request.location_id)} | Component: {request.component_id or '-'}",
                    f"Failure symptom: {request.failure_symptom_code or '-'}",
                    f"Safety risk: {request.safety_risk_level or '-'} | Production impact: {request.production_impact_level or '-'}",
                    f"Requested by: {request.requested_by_name_snapshot or '-'} | Triaged: {format_timestamp(request.triaged_at)}",
                    f"Description: {request.description or '-'}",
                    f"Notes: {request.notes or '-'}",
                ]
            )
        )
        self.linked_orders_table.setRowCount(len(related_orders))
        for row_index, order in enumerate(related_orders):
            values = (
                f"{order.work_order_code} - {order.title or order.work_order_type.value.title()}",
                order.status.value.title(),
                order.priority.value.title(),
                order.work_order_type.value.title(),
            )
            for column, value in enumerate(values):
                self.linked_orders_table.setItem(row_index, column, QTableWidgetItem(value))
        self.workbench.set_current_section("overview")

    def _build_overview_widget(self) -> tuple[QWidget, QLabel]:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceRequestDialogOverviewSurface",
            alt=False,
        )
        title = QLabel("Request Overview")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        summary = QLabel("Select a request to inspect intake, impact, and conversion context.")
        summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        summary.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(summary)
        return widget, summary

    def _build_orders_widget(self) -> tuple[QWidget, object]:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceRequestDialogOrdersSurface",
            alt=False,
        )
        title = QLabel("Linked Work Orders")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Work orders created from the selected request.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        table = build_admin_table(
            headers=("Work Order", "Status", "Priority", "Type"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(table)
        return widget, table

    @staticmethod
    def _label_for(labels: dict[str, str], value: str | None) -> str:
        if not value:
            return "-"
        return labels.get(value, value)

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceRequestDetailDialog"]
